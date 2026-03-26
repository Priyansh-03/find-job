#!/usr/bin/env python3
"""Fetch jobs for each user in input/user.csv using their roles, skills, and location."""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from urllib.parse import unquote, urlparse
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal

from paths import (
    ASHBY_BOARDS,
    DATA_DIR,
    FETCHER_SCRATCH_CSV,
    GREENHOUSE_BOARDS,
    JOBVITE_BOARDS,
    LEVER_BOARDS,
    LOG_DIR,
    OUTPUT_DIR,
    PROJECT_ROOT,
    SMARTRECRUITERS_BOARDS,
    SOURCE_TIMING_EMA_JSON,
    USER_CSV,
    WORKDAY_BOARDS_JSON,
)
from source_keyword_policy import KeywordAdapt, adapt_keywords_for_source

from location_filter import (
    authentic_jobs_search_location_slug,
    filter_jobs_by_location_substrings,
    jobicy_geo_from_hint,
    location_suggests_india as _location_suggests_india,
    location_substrings_for_hint,
    merge_location_cells,
)

SCRIPT_DIR = PROJECT_ROOT
VENV_PY = Path(sys.executable)
LOC_JSON = DATA_DIR / "latitude_longitude.json"

JOBSPY_SITE_CHOICES = frozenset(
    {"indeed", "linkedin", "google"}
)
# LinkedIn via JobSpy is higher block-risk; dashboard “all job boards” omits it unless “risk ip” is on.
JOBSPY_SITES_RISKY = frozenset({"linkedin"})


def jobspy_sites_full_pipeline(*, include_risky_jobspy: bool) -> list[str]:
    """JobSpy site list for the full multi-board run (CLI default or dashboard “all job boards”)."""
    ordered = sorted(JOBSPY_SITE_CHOICES)
    if include_risky_jobspy:
        return list(ordered)
    return [s for s in ordered if s not in JOBSPY_SITES_RISKY]

# Default seconds per source when we have no timing history yet (JobSpy / slow APIs skew high)
_DEFAULT_SOURCE_SEC_ESTIMATE = 14.0
_TIMING_EMA_ALPHA = 0.25


def _s(rel: str) -> str:
    """Fetcher script path relative to project root (all implementations live under ``sources/``)."""
    return f"sources/{rel}"


def _fmt_dur(sec: float) -> str:
    sec = max(0.0, float(sec))
    if sec < 90:
        return f"{sec:.0f}s"
    m, s = divmod(int(sec + 0.5), 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s"


def _load_timing_ema() -> dict[str, float]:
    if not SOURCE_TIMING_EMA_JSON.is_file():
        return {}
    try:
        raw = json.loads(SOURCE_TIMING_EMA_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    out: dict[str, float] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            try:
                out[str(k)] = float(v)
            except (TypeError, ValueError):
                continue
    return out


def _save_timing_ema(data: dict[str, float]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_TIMING_EMA_JSON.write_text(json.dumps(dict(sorted(data.items())), indent=2), encoding="utf-8")


def _ema_blend(prev: float | None, sample: float, alpha: float = _TIMING_EMA_ALPHA) -> float:
    if prev is None:
        return float(sample)
    return alpha * float(sample) + (1.0 - alpha) * float(prev)


def _estimate_run_seconds(configs: list[tuple[str, str]], timing: dict[str, float], n_users: int) -> float:
    per_user = sum(float(timing.get(name, _DEFAULT_SOURCE_SEC_ESTIMATE)) for name, _ in configs)
    return per_user * max(1, n_users)


class RunTee:
    """Write the same lines to stdout and a per-run log file under ``logs/``."""

    def __init__(self, path: Path):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._fp = open(path, "w", encoding="utf-8")

    def emit(self, msg: str = "") -> None:
        print(msg)
        self._fp.write(msg + "\n")
        self._fp.flush()

    def close(self) -> None:
        self._fp.close()


def _parse_jobspy_sites(s: str) -> list[str]:
    out = []
    for p in (s or "").split(","):
        x = p.strip().lower()
        if x in JOBSPY_SITE_CHOICES:
            out.append(x)
    return out or ["indeed"]


# When `Location` is empty and `--location-preference` is unset (CLI + dashboard).
# Project default geography: India and Indian cities only unless the user overrides.
DEFAULT_USER_LOCATION_HINT = "india"


@dataclass
class FetchOpts:
    ignore_title_words: list[str]
    user_lat: float | None
    user_lng: float | None
    radius_miles: float | None
    page_size: int
    jobspy_sites: list[str]
    jobspy_results: int
    # Max jobs for JobSpy LinkedIn only (dashboard “risk ip” count; full run when LinkedIn is on).
    risk_jobspy_per_site: int
    ashby_compensation: bool
    custom_ats: bool
    workday: bool
    jobvite: bool
    smartrecruiters: bool
    greenhouse_lever_india_only: bool
    jobs_per_source: int
    location_preference: str
    location_fallback: bool
    # Netflix API mirrors careers URL query params (see sources/custom-ats/netflix/fetch.py)
    netflix_location: str
    netflix_sort_by: str
    netflix_teams: list[str]
    netflix_work_types: list[str]


def _first_location_token(csv_location: str) -> str:
    for chunk in (csv_location or "").replace(",", " ").split():
        w = chunk.strip()
        if len(w) >= 2:
            return w
    return ""


def _resolve_user_location_hint(cli_preference: str, csv_location: str) -> str:
    if cli_preference.strip():
        return cli_preference.strip()
    token = _first_location_token(csv_location)
    return token if token else DEFAULT_USER_LOCATION_HINT


def _skip_orch_location_text_filter(name: str) -> bool:
    """Sources already biased by API/feed params — avoid stripping rows with title-only heuristics."""
    if name in (
        "remoteok",
        "himalayas",
        "jobicy",
        "arbeitnow",
        "dayweek4",
        "themuse",
        "workingnomads",
        "authenticjobs",
        "netflix-ats",
    ):
        return True
    if name.startswith("jobspy-") or name.startswith("greenhouse-") or name.startswith("lever-"):
        return True
    return False


def _apply_orch_location_text_filter(
    name: str,
    rows: list[dict],
    user_location_hint: str,
    *,
    apply_filter: bool,
) -> list[dict]:
    """Narrow rows using location hint on structured fields only (not global RSS title spam)."""
    if not apply_filter or not rows or _skip_orch_location_text_filter(name):
        return rows
    subs = location_substrings_for_hint(user_location_hint)
    if not subs:
        return rows
    if name.startswith("ashby-") or name in ("spotify-ats", "uber-ats"):
        return filter_jobs_by_location_substrings(rows, subs, fields=("location", "title"))
    if name.startswith("workday-") or name.startswith("jobvite-") or name.startswith("smartrecruiters-"):
        return filter_jobs_by_location_substrings(rows, subs, fields=("title", "link"))
    return rows


def _failure_hint(kind: str, stderr: str, code: int | None) -> str:
    s = (stderr or "").lower()
    if kind == "timeout":
        return "Subprocess timed out; fewer boards or higher timeout may help."
    if "importerror" in s or "no module named" in s:
        return "Install missing dependency in .venv (e.g. pip install python-jobspy)."
    if "404" in s or "not found" in s or "not found (404)" in s:
        return "Board or API URL returned 404; verify slug/token or site still uses this ATS."
    if "401" in s or "403" in s:
        return "HTTP 401/403; endpoint may block automated access."
    if "recaptcha" in s or "406" in s:
        return (
            "Some job APIs return HTTP 406 or reCAPTCHA; automated fetchers cannot bypass that."
        )
    if kind == "no_csv":
        return "No jobs.csv written; fetcher may have matched zero jobs or crashed before write."
    if kind == "exception":
        return "Python error running subprocess; see stderr for traceback."
    return "Inspect stderr; check network, API changes, and fetcher CLI."


def _tokenize(s: str, max_items: int = 6) -> list[str]:
    parts = []
    for chunk in s.split(","):
        for word in chunk.split():
            w = word.strip()
            if w and len(w) >= 2 and w not in parts:
                parts.append(w)
                if len(parts) >= max_items:
                    return parts
    return parts


def parse_keywords(roles: str, skills: str, max_kw: int = 8) -> tuple[list[str], list[str], list[str], list[str]]:
    role_kw = _tokenize(roles, 5)
    skill_kw = _tokenize(skills, 5)
    primary = list(dict.fromkeys(role_kw + skill_kw))[:max_kw]
    if not primary:
        primary = ["manager", "remote"]
    role_only = role_kw[:4] if role_kw else ["manager"]
    skill_only = skill_kw[:4] if skill_kw else ["remote"]
    fallback = (role_kw[:1] or skill_kw[:1] or ["manager"]) + ["remote"]
    return primary, role_only, skill_only, fallback


def _slug_to_display_name(slug: str) -> str:
    """Turn a URL path segment (often hyphenated) into a short display name."""
    if not slug:
        return ""
    slug = unquote(slug.strip().strip("/")).replace("_", "-")
    parts = [p for p in slug.split("-") if p]
    if not parts:
        return ""
    out: list[str] = []
    for p in parts:
        if p.isupper() or (len(p) > 1 and p[0].isupper() and not p[1:].islower()):
            out.append(p)
        else:
            out.append(p.capitalize())
    return " ".join(out)


def _strip_trailing_numeric_slug(slug: str) -> str:
    return re.sub(r"-\d{3,}$", "", slug)


def _company_from_title(title: str) -> str:
    if not title or not str(title).strip():
        return ""
    t = html.unescape(str(title)).strip()
    for pat in (r"\s+at\s+([^,|/]+?)\s*$", r"\s+@\s+([^,|/]+?)\s*$"):
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            name = re.sub(r"\s*\([^)]{0,120}\)\s*$", "", name).strip()
            name = re.sub(r"\s*~\s*£[^)]+\)\s*$", "", name).strip()  # trim (~£...) tail noise
            if 2 <= len(name) <= 120:
                return name
    return ""


def _infer_company_from_url(link: str) -> str:
    """Best-effort company from known ATS / board URL shapes when scrapers omit ``company``."""
    link = (link or "").strip()
    if not link:
        return ""
    try:
        u = urlparse(link)
    except ValueError:
        return ""
    host = (u.netloc or "").lower()
    segs = [s for s in (u.path or "").strip("/").split("/") if s]
    if not segs:
        return ""

    if "greenhouse.io" in host and len(segs) >= 2 and segs[1] == "jobs":
        return _slug_to_display_name(segs[0])

    if "lever.co" in host and "jobs" not in segs[0].lower():
        # e.g. jobs.lever.co/acme/uuid
        return _slug_to_display_name(segs[0])

    if "ashbyhq.com" in host and len(segs) >= 1:
        # e.g. jobs.ashbyhq.com/company/...
        if segs[0] == "company" and len(segs) >= 2:
            return _slug_to_display_name(segs[1])
        return _slug_to_display_name(segs[0])

    if "smartr.me" in host and "company" in segs:
        i = segs.index("company")
        if i + 1 < len(segs):
            return _slug_to_display_name(segs[i + 1])

    if "remotefirstjobs.com" in host and "companies" in segs:
        i = segs.index("companies")
        if i + 1 < len(segs):
            return _slug_to_display_name(segs[i + 1])

    if "landing.jobs" in host and len(segs) >= 2 and segs[0] == "at":
        return _slug_to_display_name(segs[1])

    if "remoteok.com" in host or "remoteok.io" in host:
        last = segs[-1]
        parts = last.split("-")
        while parts and parts[-1].isdigit():
            parts.pop()
        if parts:
            cand = parts[-1]
            if len(cand) >= 2 and re.match(r"^[A-Za-z][A-Za-z0-9]*$", cand):
                return cand.capitalize() if cand.islower() else _slug_to_display_name(cand)

    if "weworkremotely.com" in host and "remote-jobs" in segs:
        i = segs.index("remote-jobs")
        if i + 1 < len(segs):
            job_slug = segs[i + 1]
            first = job_slug.split("-")[0]
            if len(first) >= 2:
                return first.capitalize() if first.islower() else _slug_to_display_name(first)

    if "realworkfromanywhere.com" in host and segs[0] == "jobs" and len(segs) >= 2:
        slug = _strip_trailing_numeric_slug(segs[1])
        parts = slug.split("-")
        suffixes = frozenset({"ltd", "inc", "llc", "limited", "plc", "gmbh"})
        if len(parts) >= 2 and parts[-1].lower() in suffixes:
            return _slug_to_display_name("-".join(parts[-2:]))
        if parts:
            tail = parts[-1]
            if len(tail) >= 3:
                return _slug_to_display_name(tail)

    if "jobspresso.co" in host and segs[0] == "job" and len(segs) >= 2:
        slug = segs[1]
        for sep in ("-worldwide-", "-remote-", "-us-", "-uk-", "-eu-", "-hybrid-"):
            if sep in slug:
                return _slug_to_display_name(slug.split(sep)[0])
        m = re.match(
            r"^([a-z0-9]+(?:-[a-z0-9]+){0,5})-(?:developer|engineer|designer|manager|specialist|analyst|lead)",
            slug,
            re.I,
        )
        if m:
            return _slug_to_display_name(m.group(1))

    if "vuejobs.com" in host and segs[0] == "jobs" and len(segs) >= 2:
        slug = segs[1]
        m = re.search(r"-at-([a-z0-9-]+?)(?:\?|$)", slug, re.I)
        if m:
            return _slug_to_display_name(m.group(1))

    return ""


def _is_blank_company(val: object) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    s = str(val).strip()
    return not s or s.lower() == "nan"


def _listing_host_tag(link: str) -> str:
    """Tag when the job URL points at a known board (aggregators often deep-link to LinkedIn, Indeed, etc.)."""
    if not (link or "").strip():
        return ""
    try:
        host = (urlparse(link).netloc or "").lower()
    except ValueError:
        return ""
    if "linkedin.com" in host:
        return "linkedin-listing"
    if "indeed." in host or host.endswith("indeed.com"):
        return "indeed-listing"
    if "glassdoor." in host or host.endswith("glassdoor.com"):
        return "glassdoor-listing"
    if "naukri.com" in host:
        return "naukri-listing"
    if "ashbyhq.com" in host:
        return "ashby-listing"
    if "greenhouse.io" in host:
        return "greenhouse-listing"
    if "lever.co" in host:
        return "lever-listing"
    return ""


# Values some APIs put in a "location" field that are site names, not geography.
_NON_GEO_LOCATION_TOKENS: frozenset[str] = frozenset(
    {
        "remoteok",
        "remote ok",
        "remoteok.com",
        "himalayas",
        "jobicy",
        "indeed",
        "linkedin",
        "glassdoor",
        "ziprecruiter",
        "zip recruiter",
    }
)


def _clean_job_location_field(raw: str) -> str:
    """Drop board/aggregator labels mistaken for place names."""
    s = (raw or "").strip()
    if not s:
        return ""
    if s.lower() in _NON_GEO_LOCATION_TOKENS:
        return ""
    compact = s.lower().replace(" ", "")
    if compact in {x.replace(" ", "") for x in _NON_GEO_LOCATION_TOKENS}:
        return ""
    return s


def _merge_source_with_listing_url(source: str, link: str) -> str:
    """Append listing-host tag when URL is on a different board than the fetcher name suggests."""
    tag = _listing_host_tag(link)
    if not tag:
        return source
    src_l = source.lower()
    if tag == "linkedin-listing" and "linkedin" in src_l:
        return source
    if tag == "indeed-listing" and "indeed" in src_l:
        return source
    if tag == "naukri-listing" and "naukri" in src_l:
        return source
    if tag == "glassdoor-listing" and "glassdoor" in src_l:
        return source
    if tag == "ashby-listing" and "ashby" in src_l:
        return source
    if tag == "greenhouse-listing" and "greenhouse" in src_l:
        return source
    if tag == "lever-listing" and "lever" in src_l:
        return source
    return f"{source}+{tag}" if source else tag


def normalize_job(row: dict, source: str) -> dict:
    title = row.get("title") or row.get("position") or row.get("job_title") or ""
    link = (row.get("link") or row.get("url") or row.get("job_url") or "").strip()
    company = row.get("company", "")
    if _is_blank_company(company):
        company = ""
    else:
        company = str(company).strip()
    if not company:
        company = _infer_company_from_url(link)
    if not company:
        company = _company_from_title(title)
    loc_raw = (row.get("location") or "").strip()
    loc = _clean_job_location_field(loc_raw)
    out = {
        "title": title,
        "link": link,
        "company": company,
        "source": _merge_source_with_listing_url(source, link),
        # Always set so dashboard column order matches (avoid shifting source into location).
        "location": loc,
    }
    return out


def _load_slug_file(path: Path) -> list[str]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def _workday_board_count() -> int:
    p = WORKDAY_BOARDS_JSON
    if not p.is_file():
        return 0
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    boards = raw if isinstance(raw, list) else raw.get("boards", [])
    return len(boards) if isinstance(boards, list) else 0


def _read_board_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [s.strip() for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


def build_configs(opts: FetchOpts) -> list[tuple[str, str]]:
    """Ordered by IP-block risk: JobSpy last (tier C)."""
    configs: list[tuple[str, str]] = [
        ("remoteok", _s("remoteok-scraper/fetch_jobs.py")),
        ("himalayas", _s("himalayas/fetch.py")),
        ("jobicy", _s("jobicy/fetch.py")),
        ("arbeitnow", _s("arbeitnow/fetch.py")),
        ("dayweek4", _s("dayweek4/fetch.py")),
        ("themuse", _s("themuse/fetch.py")),
        ("workingnomads", _s("workingnomads/fetch.py")),
        ("authenticjobs", _s("authenticjobs/fetch.py")),
        ("contentwritingjobs", _s("contentwritingjobs/fetch.py")),
        ("jobscollider", _s("jobscollider/fetch.py")),
        ("jobspresso", _s("jobspresso/fetch.py")),
        ("larajobs", _s("larajobs/fetch.py")),
        ("remotepython", _s("remotepython/fetch.py")),
        ("vuejobs", _s("vuejobs/fetch.py")),
        ("landingjobs", _s("landingjobs/fetch.py")),
        ("realworkfromanywhere", _s("realworkfromanywhere/fetch.py")),
        ("weworkremotely", _s("weworkremotely/fetch.py")),
    ]

    gh_companies = _read_board_lines(GREENHOUSE_BOARDS) if GREENHOUSE_BOARDS.exists() else ["stripe", "figma", "airtable"]
    for company in gh_companies:
        configs.append((f"greenhouse-{company}", _s("greenhouse-lever/fetch.py")))

    for company in _read_board_lines(LEVER_BOARDS):
        configs.append((f"lever-{company}", _s("greenhouse-lever/fetch.py")))

    for board in _read_board_lines(ASHBY_BOARDS):
        configs.append((f"ashby-{board}", _s("ashby/fetch.py")))

    if opts.custom_ats:
        configs.append(("netflix-ats", _s("custom-ats/netflix/fetch.py")))
        configs.append(("spotify-ats", _s("custom-ats/spotify/fetch.py")))
        configs.append(("uber-ats", _s("custom-ats/uber/fetch.py")))

    if opts.workday and _workday_board_count() > 0:
        for i in range(_workday_board_count()):
            configs.append((f"workday-{i}", _s("workday/fetch.py")))

    if opts.jobvite:
        for slug in _load_slug_file(JOBVITE_BOARDS):
            configs.append((f"jobvite-{slug}", _s("jobvite/fetch.py")))

    if opts.smartrecruiters:
        for slug in _load_slug_file(SMARTRECRUITERS_BOARDS):
            configs.append((f"smartrecruiters-{slug}", _s("smartrecruiters/fetch.py")))

    for site in opts.jobspy_sites:
        s = site.strip().lower()
        if s in JOBSPY_SITE_CHOICES:
            configs.append((f"jobspy-{s}", _s("jobspy/fetch.py")))
    return configs


def build_dashboard_configs(*, risk_ip: bool) -> list[tuple[str, str]]:
    """Small JobSpy-only pipeline for the web dashboard.

    When ``risk_ip`` is True: LinkedIn only (limits come from ``FetchOpts``).
    When False: LinkedIn off; Indeed only for a quick, lower-risk smoke test.
    """
    js = _s("jobspy/fetch.py")
    if risk_ip:
        return [("jobspy-linkedin", js)]
    return [("jobspy-indeed", js)]


def _progress_delta_after_filters(
    all_jobs: list[dict],
    opts: FetchOpts,
    state: dict[str, Any],
) -> tuple[list[dict], list[dict]]:
    """Apply title/geo/dedupe like the final pass; return (new rows since last call, full list)."""
    tmp = _apply_title_ignore(list(all_jobs), opts.ignore_title_words)
    tmp = _apply_geo_filter(tmp, opts.user_lat, opts.user_lng, opts.radius_miles, LOC_JSON)
    tmp = _dedupe_jobs_by_link(tmp)
    sent: set[str] = state.setdefault("sent_keys", set())
    delta: list[dict] = []
    for r in tmp:
        k = _normalize_url_for_dedupe((r.get("link") or "").strip())
        if not k:
            continue
        if k not in sent:
            sent.add(k)
            delta.append(r)
    return delta, tmp


def fetch_all_for_user(
    keywords_tuple: tuple,
    opts: FetchOpts,
    user_location_hint: str,
    *,
    timing_ema: dict[str, float],
    emit: Callable[[str], None] = print,
    eta_every: int = 10,
    configs_override: list[tuple[str, str]] | None = None,
    progress_emit: Callable[[list[dict], list[dict]], None] | None = None,
    progress_state: dict[str, Any] | None = None,
) -> tuple[list[dict], list[dict[str, Any]], dict[str, Any]]:
    primary, role_only, skill_only, fallback = keywords_tuple
    all_jobs: list[dict] = []
    failures: list[dict[str, Any]] = []
    configs = configs_override if configs_override is not None else build_configs(opts)
    prog_state: dict[str, Any] = progress_state if progress_state is not None else {}

    sources_configured = len(configs)
    sources_runnable = 0
    sources_missing_script = 0
    sources_delivered_pre_filters = 0

    keyword_sets = [
        ("primary (roles+skills)", primary),
        ("roles only", role_only),
        ("skills only", skill_only),
        ("fallback (broad)", fallback),
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    user_wall0 = time.perf_counter()

    for idx, (name, script) in enumerate(configs):
        spath = SCRIPT_DIR / script
        if not spath.exists():
            emit(f"    [SKIP] {name}: script not found ({script})")
            sources_missing_script += 1
            continue
        sources_runnable += 1
        source_wall0 = time.perf_counter()
        per_source_cap = max(1, opts.jobs_per_source)
        if name == "jobspy-linkedin":
            per_source_cap = max(1, min(max(1, opts.risk_jobspy_per_site), 50))
        added = 0
        seen_this_source: set[str] = set()
        for label, kw_set in keyword_sets:
            if added >= per_source_cap:
                break
            adap = adapt_keywords_for_source(name, kw_set)
            if adap.log_line and label == "primary (roles+skills)":
                emit(f"    [kw] {name}: {adap.log_line}")
            args = _build_args(
                name,
                adap,
                per_source_cap,
                opts,
                user_location_hint=user_location_hint,
                arg_variant="prefer",
            )
            to = 90 if name.startswith("workday-") or name.endswith("-ats") else 55
            n, jobs, diag = _run_fetcher(name, script, args, timeout=to, emit=emit)
            if diag:
                failures.append(diag)
                if diag.get("kind") in ("exit_error", "no_csv", "timeout", "exception"):
                    break
            jobs = _apply_orch_location_text_filter(
                name, jobs, user_location_hint, apply_filter=True
            )
            added_before = added
            for j in jobs:
                link = (j.get("link") or "").strip()
                if link and link not in seen_this_source:
                    seen_this_source.add(link)
                    all_jobs.append(j)
                    added += 1
                    if added >= per_source_cap:
                        break
            if added > added_before:
                gained = added - added_before
                if label != "primary (roles+skills)":
                    emit(f"    [OK] {name}: {gained} job(s) (via {label})")
                else:
                    emit(f"    [OK] {name}: {gained} job(s)")
            if added >= per_source_cap:
                break

        if added == 0 and opts.location_fallback:
            fb_adap = adapt_keywords_for_source(name, primary)
            if fb_adap.log_line:
                emit(f"    [kw] {name} (fallback): {fb_adap.log_line}")
            args = _build_args(
                name,
                fb_adap,
                per_source_cap,
                opts,
                user_location_hint=user_location_hint,
                arg_variant="fallback",
            )
            to = 90 if name.startswith("workday-") or name.endswith("-ats") else 55
            n, jobs, diag = _run_fetcher(name, script, args, timeout=to, emit=emit)
            if diag:
                failures.append(diag)
            jobs = _apply_orch_location_text_filter(
                name, jobs, user_location_hint, apply_filter=False
            )
            for j in jobs:
                link = (j.get("link") or "").strip()
                if link and link not in seen_this_source:
                    seen_this_source.add(link)
                    all_jobs.append(j)
                    added += 1
                    if added >= per_source_cap:
                        break
            if added > 0:
                emit(f"    [OK] {name}: fallback pass, {min(added, per_source_cap)} job(s)")

        if added == 0:
            emit(
                f"    [0] {name}: no jobs (tried all keyword sets"
                + (", fallback" if opts.location_fallback else "")
                + ")"
            )
        else:
            sources_delivered_pre_filters += 1

        if progress_emit is not None:
            delta, full = _progress_delta_after_filters(all_jobs, opts, prog_state)
            if delta:
                progress_emit(delta, full)

        dt_source = time.perf_counter() - source_wall0
        timing_ema[name] = _ema_blend(timing_ema.get(name), dt_source)

        done = idx + 1
        if eta_every > 0 and done % eta_every == 0 and done < len(configs):
            elapsed_u = time.perf_counter() - user_wall0
            avg = elapsed_u / done
            eta = avg * (len(configs) - done)
            emit(
                f"    [ETA] ~{_fmt_dur(eta)} left this user "
                f"(progress {done}/{len(configs)}, avg {avg:.1f}s/source)"
            )

    rows_after_collection = len(all_jobs)
    all_jobs = _apply_title_ignore(all_jobs, opts.ignore_title_words)
    rows_after_title = len(all_jobs)
    all_jobs = _apply_geo_filter(all_jobs, opts.user_lat, opts.user_lng, opts.radius_miles, LOC_JSON)
    rows_after_geo = len(all_jobs)
    pre_dedupe = len(all_jobs)
    all_jobs = _dedupe_jobs_by_link(all_jobs)
    duplicate_urls_merged = pre_dedupe - len(all_jobs)
    if duplicate_urls_merged > 0:
        emit(
            f"    [dedupe] merged {duplicate_urls_merged} duplicate row(s) (same URL); "
            "see combined `source` column"
        )

    stats: dict[str, Any] = {
        "sources_configured": sources_configured,
        "sources_runnable": sources_runnable,
        "sources_missing_script": sources_missing_script,
        "sources_delivered_pre_filters": sources_delivered_pre_filters,
        "sources_no_job_after_fetch": max(0, sources_runnable - sources_delivered_pre_filters),
        "failure_events": len(failures),
        "failure_sources_unique": len({f.get("source") for f in failures if f.get("source")}),
        "rows_after_collection": rows_after_collection,
        "dropped_title_filter": rows_after_collection - rows_after_title,
        "dropped_geo_filter": rows_after_title - rows_after_geo,
        "duplicate_urls_merged": duplicate_urls_merged,
        "final_rows": len(all_jobs),
        "wall_seconds": time.perf_counter() - user_wall0,
    }
    return all_jobs, failures, stats


def _build_args(
    name: str,
    adap: KeywordAdapt,
    limit_per: int,
    opts: FetchOpts,
    *,
    user_location_hint: str,
    arg_variant: Literal["prefer", "fallback"],
) -> list[str]:
    kw = list(adap.keywords)
    if not kw and name != "landingjobs":
        kw = ["manager", "remote"]
    k1 = kw[0] if kw else "manager"
    search_one = (adap.search_phrase or (" ".join(kw) if kw else k1)).strip() or k1
    base = ["--limit", str(max(1, limit_per))]
    kw_args = ["--keywords"] + kw if kw else []

    prefer_loc = (user_location_hint or "").strip().lower() or DEFAULT_USER_LOCATION_HINT
    # Use resolved geography (blank CSV → india) for all board args, not raw whitespace.
    india_focus = _location_suggests_india(prefer_loc)

    if arg_variant == "fallback":
        if india_focus:
            # Second keyword pass stays India-scoped by default (no US/worldwide widening).
            himalayas_loc = "india"
            remoteok_locs = location_substrings_for_hint(prefer_loc)
            jobicy_geo = jobicy_geo_from_hint(prefer_loc) or None
            arbeitnow_loc = "india"
            dayweek_loc = "india"
            themuse_loc = "india"
            workingnomads_loc = "india"
            jobspy_country = "india"
            jobspy_location = prefer_loc if prefer_loc != "worldwide" else "india"
        else:
            himalayas_loc = "worldwide"
            # Match https://remoteok.com/remote-jobs-in-india — broad OR only when not India-focused.
            remoteok_locs = ["remote", "worldwide"]
            jobicy_geo: str | None = None
            arbeitnow_loc = ""
            dayweek_loc = ""
            themuse_loc = ""
            workingnomads_loc = ""
            jobspy_country = "usa"
            jobspy_location = "remote"
    else:
        himalayas_loc = prefer_loc
        if india_focus:
            remoteok_locs = location_substrings_for_hint(prefer_loc)
        elif prefer_loc != "worldwide":
            remoteok_locs = [prefer_loc, "remote", "asia"]
        else:
            remoteok_locs = ["remote", "asia", "worldwide"]
        jobicy_geo = jobicy_geo_from_hint(prefer_loc)
        arbeitnow_loc = prefer_loc if prefer_loc != "worldwide" else ""
        dayweek_loc = arbeitnow_loc
        themuse_loc = arbeitnow_loc
        workingnomads_loc = arbeitnow_loc
        if india_focus:
            jobspy_country = "india"
            jobspy_location = prefer_loc if prefer_loc != "worldwide" else "india"
        elif (user_location_hint or "").strip():
            jobspy_country = "usa"
            jobspy_location = prefer_loc
        else:
            jobspy_country = "india"
            jobspy_location = "india"

    if name == "remoteok":
        cmd = kw_args + ["--location"] + remoteok_locs + base
        if india_focus:
            cmd = kw_args + ["--api-location", "india", "--location"] + remoteok_locs + base
        return cmd
    if name == "himalayas":
        return ["--query", search_one, "--location", himalayas_loc] + base + kw_args
    if name == "jobicy":
        jc = str(max(30, min(opts.page_size, 100))) if opts.page_size > 0 else "50"
        cmd = (["--geo", jobicy_geo] if jobicy_geo else []) + ["--keywords"] + kw + ["--count", jc] + base
        return cmd
    if name == "arbeitnow":
        cmd = base + kw_args
        if arbeitnow_loc:
            cmd = ["--location", arbeitnow_loc] + cmd
        return cmd
    if name == "dayweek4":
        cmd = base + kw_args
        if dayweek_loc:
            cmd = ["--location", dayweek_loc] + cmd
        return cmd
    if name == "themuse":
        cmd = base + kw_args
        if themuse_loc:
            cmd = ["--location", themuse_loc] + cmd
        return cmd
    if name == "workingnomads":
        cmd = base + kw_args
        if workingnomads_loc:
            cmd = ["--location", workingnomads_loc] + cmd
        return cmd
    if name == "authenticjobs":
        cmd = list(base + kw_args)
        slug = ""
        if arg_variant == "prefer":
            slug = authentic_jobs_search_location_slug(prefer_loc)
        elif arg_variant == "fallback" and india_focus:
            slug = authentic_jobs_search_location_slug(prefer_loc) or "india"
        if slug:
            cmd = ["--search-location", slug] + cmd
        return cmd
    if name in (
        "contentwritingjobs",
        "jobscollider",
        "jobspresso",
        "larajobs",
        "remotepython",
        "vuejobs",
    ):
        return base + kw_args
    if name == "landingjobs":
        return base
    if name == "realworkfromanywhere":
        return ["--category", "all"] + base + kw_args
    if name == "weworkremotely":
        return ["--category", "all"] + base + kw_args
    if name.startswith("jobspy-"):
        site = name.split("-", 1)[1]
        if name == "jobspy-linkedin":
            res = max(1, opts.risk_jobspy_per_site)
        else:
            res = opts.jobspy_results if opts.jobspy_results > 0 else 8
        if opts.page_size > 0:
            res = min(res, opts.page_size)
        res = max(1, min(res, limit_per))
        jkw = kw_args if kw_args else ["--keywords", search_one]
        return [
            "--site",
            site,
            "--country",
            jobspy_country,
            "--location",
            jobspy_location,
            "--search",
            search_one,
            "--results",
            str(res),
        ] + base + jkw
    if name.startswith("greenhouse-"):
        company = name.replace("greenhouse-", "")
        extra = []
        if opts.page_size > 0:
            extra = ["--page-size", str(opts.page_size)]
        # India hint (CSV / default) or --greenhouse-india-only: drop US-only rows (no API-side filter).
        if opts.greenhouse_lever_india_only or india_focus:
            extra.append("--india-only")
        return ["--source", "greenhouse", "--company", company] + extra + base + kw_args
    if name.startswith("lever-"):
        company = name.replace("lever-", "")
        extra = []
        if opts.page_size > 0:
            extra = ["--page-size", str(opts.page_size)]
        if opts.greenhouse_lever_india_only or india_focus:
            extra.append("--india-only")
        return ["--source", "lever", "--company", company] + extra + base + kw_args
    if name.startswith("ashby-"):
        board = name.replace("ashby-", "")
        extra = ["--compensation"] if opts.ashby_compensation else []
        return ["--board", board] + extra + base + kw_args
    if name == "netflix-ats":
        ps = max(1, opts.page_size) if opts.page_size > 0 else 10
        cmd = ["--page-size", str(ps), "--query", search_one]
        netflix_loc = opts.netflix_location.strip()
        if not netflix_loc:
            if india_focus:
                netflix_loc = "India"
            else:
                netflix_loc = (user_location_hint or "").strip() or prefer_loc
        if netflix_loc:
            cmd += ["--location", netflix_loc]
        for t in opts.netflix_teams:
            if t.strip():
                cmd += ["--team", t.strip()]
        for wt in opts.netflix_work_types:
            if wt.strip():
                cmd += ["--work-type", wt.strip()]
        if opts.netflix_sort_by.strip():
            cmd += ["--sort-by", opts.netflix_sort_by.strip()]
        return cmd + base + kw_args
    if name == "spotify-ats":
        return base + kw_args
    if name == "uber-ats":
        ps = max(1, min(opts.page_size, 100)) if opts.page_size > 0 else 50
        return ["--page-size", str(ps)] + base + kw_args
    if name.startswith("workday-"):
        idx = int(name.split("-", 1)[1])
        ps = max(1, min(opts.page_size, 50)) if opts.page_size > 0 else 20
        return ["--board-index", str(idx), "--page-size", str(ps)] + base + kw_args
    if name.startswith("jobvite-"):
        slug = name.replace("jobvite-", "")
        return ["--slug", slug] + base + kw_args
    if name.startswith("smartrecruiters-"):
        slug = name.replace("smartrecruiters-", "")
        return ["--slug", slug] + base + kw_args
    return base + kw_args


def _run_fetcher(
    name: str,
    script: str,
    args: list[str],
    timeout: int = 55,
    *,
    out_csv: Path = FETCHER_SCRATCH_CSV,
    emit: Callable[[str], None] = print,
) -> tuple[int, list[dict], dict[str, Any] | None]:
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    run_args = [str(x) for x in args]
    if "--out" not in run_args:
        run_args = run_args + ["--out", str(out_csv)]
    argv = [str(VENV_PY), str(SCRIPT_DIR / script)] + run_args
    try:
        result = subprocess.run(argv, cwd=SCRIPT_DIR, capture_output=True, text=True, timeout=timeout)
        err_full = (result.stderr or "").strip()
        out_full = (result.stdout or "").strip()
        if result.returncode != 0:
            err = err_full[:200] or out_full[:200]
            emit(f"    [FAIL] {name}: exit {result.returncode} - {err or 'no output'}")
            diag = {
                "source": name,
                "script": script,
                "code": result.returncode,
                "stderr": err_full[:800],
                "stdout": out_full[:400],
                "kind": "exit_error",
                "hint": _failure_hint("exit_error", err_full, result.returncode),
            }
            return 0, [], diag
        if not out_csv.exists():
            emit(f"    [WARN] {name}: no output file")
            diag = {
                "source": name,
                "script": script,
                "code": 0,
                "stderr": err_full[:800],
                "stdout": out_full[:400],
                "kind": "no_csv",
                "hint": _failure_hint("no_csv", err_full, 0),
            }
            return 0, [], diag
        jobs = []
        with open(out_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                link = (row.get("link") or row.get("url") or row.get("job_url") or "").strip()
                if link:
                    jobs.append(normalize_job(row, name))
        if not jobs:
            return 0, [], None
        return len(jobs), jobs, None
    except subprocess.TimeoutExpired:
        emit(f"    [FAIL] {name}: timeout ({timeout}s)")
        diag = {
            "source": name,
            "script": script,
            "code": None,
            "stderr": "",
            "stdout": "",
            "kind": "timeout",
            "hint": _failure_hint("timeout", "", None),
        }
        return 0, [], diag
    except Exception as e:
        emit(f"    [FAIL] {name}: {e}")
        diag = {
            "source": name,
            "script": script,
            "code": None,
            "stderr": str(e),
            "stdout": "",
            "kind": "exception",
            "hint": _failure_hint("exception", str(e), None),
        }
        return 0, [], diag


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3959.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1, math.sqrt(a)))


def _coords_for_text(text: str, loc_map: dict) -> tuple[float, float] | None:
    t = text.lower()
    best = None
    best_len = 0
    for place, pair in loc_map.items():
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        pl = place.lower()
        if pl in t and len(pl) > best_len:
            try:
                best = (float(pair[0]), float(pair[1]))
                best_len = len(pl)
            except (TypeError, ValueError):
                continue
    return best


def _apply_geo_filter(
    jobs: list[dict],
    user_lat: float | None,
    user_lng: float | None,
    radius: float | None,
    loc_map_path: Path,
) -> list[dict]:
    if user_lat is None or user_lng is None or radius is None:
        return jobs
    if not loc_map_path.is_file():
        return jobs
    try:
        loc_map = json.loads(loc_map_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return jobs
    out = []
    for j in jobs:
        blob = f"{j.get('title','')} {j.get('link','')} {j.get('company','')}"
        c = _coords_for_text(blob, loc_map)
        if c is None:
            continue
        if _haversine_miles(user_lat, user_lng, c[0], c[1]) <= radius:
            out.append(j)
    return out


def _normalize_url_for_dedupe(url: str) -> str:
    u = (url or "").strip().lower()
    if not u:
        return ""
    u = u.split("?", 1)[0].rstrip("/")
    return u


def _dedupe_jobs_by_link(jobs: list[dict]) -> list[dict]:
    """One row per canonical URL; merge extra board names into ``source`` (e.g. a+b+c)."""
    by_key: dict[str, dict] = {}
    order: list[str] = []
    for j in jobs:
        raw = (j.get("link") or "").strip()
        key = _normalize_url_for_dedupe(raw)
        if not key:
            continue
        if key not in by_key:
            by_key[key] = dict(j)
            order.append(key)
        else:
            prev = by_key[key]
            a = str(prev.get("source", "") or "")
            b = str(j.get("source", "") or "")
            if b and b not in a.split("+"):
                prev["source"] = f"{a}+{b}" if a else b
            la = str(prev.get("location", "") or "").strip()
            lb = str(j.get("location", "") or "").strip()
            merged = merge_location_cells(la, lb)
            if merged:
                prev["location"] = merged
    return [by_key[k] for k in order]


def _apply_title_ignore(jobs: list[dict], words: list[str]) -> list[dict]:
    if not words:
        return jobs
    wl = [w.lower() for w in words if w.strip()]
    if not wl:
        return jobs
    out = []
    for j in jobs:
        title = (j.get("title") or "").lower()
        if any(w in title for w in wl):
            continue
        out.append(j)
    return out


def _print_failure_report(failures: list[dict[str, Any]], emit: Callable[[str], None] = print) -> None:
    if not failures:
        return
    emit("\n--- Sources with errors (see hints) ---")
    seen: set[tuple[Any, ...]] = set()
    for f in failures:
        key = (f.get("source"), f.get("kind"), f.get("code"), f.get("stderr", "")[:120])
        if key in seen:
            continue
        seen.add(key)
        emit(f"  {f.get('source')}: kind={f.get('kind')} code={f.get('code')}")
        emit(f"    hint: {f.get('hint', '')}")
        err = (f.get("stderr") or "").strip()
        if err:
            emit(f"    stderr: {err[:320]}{'...' if len(err) > 320 else ''}")


def _print_run_stats_block(title: str, s: dict[str, Any], emit: Callable[[str], None] = print) -> None:
    emit(title)
    emit(f"  Job sources configured: {s['sources_configured']}")
    emit(f"  Runnable sources (script exists): {s['sources_runnable']}")
    emit(f"  Missing fetcher script (skipped): {s['sources_missing_script']}")
    emit(f"  Sources that returned ≥1 job (before title/geo): {s['sources_delivered_pre_filters']}")
    emit(f"  Sources with no job after fetch tries: {s['sources_no_job_after_fetch']}")
    emit(f"  Failure diagnostics (events): {s['failure_events']}")
    emit(f"  Failure diagnostics (unique source names): {s['failure_sources_unique']}")
    emit(f"  Rows collected (all sources, before filters): {s['rows_after_collection']}")
    emit(f"  Dropped by title filter: {s['dropped_title_filter']}")
    emit(f"  Dropped by geo filter: {s['dropped_geo_filter']}")
    emit(f"  Duplicate URLs merged (same link): {s['duplicate_urls_merged']}")
    emit(f"  Final unique jobs in CSV: {s['final_rows']}")
    emit(f"  Wall time this user: {_fmt_dur(s.get('wall_seconds', 0))}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch jobs for users in input/user.csv")
    ap.add_argument("--ignore-title", default="", help="Comma-separated words; drop jobs whose title contains any")
    ap.add_argument("--location-lat", type=float, default=None, help="Optional: your latitude for distance filter")
    ap.add_argument("--location-lng", type=float, default=None, help="Optional: your longitude for distance filter")
    ap.add_argument(
        "--location-radius-miles",
        type=float,
        default=None,
        help="Optional: keep jobs whose inferred location is within this many miles",
    )
    ap.add_argument(
        "--page-size",
        type=int,
        default=0,
        help="Optional page/batch size for APIs that support it (0 = fetcher defaults)",
    )
    ap.add_argument(
        "--jobspy-sites",
        default=None,
        metavar="LIST",
        help=(
            "Comma-separated JobSpy sites. If omitted: all except linkedin "
            "(same as dashboard “all job boards” without risk ip). "
            "Use --jobspy-risk-sites to include LinkedIn."
        ),
    )
    ap.add_argument(
        "--jobspy-risk-sites",
        action="store_true",
        help=(
            "When --jobspy-sites is not passed: run JobSpy for LinkedIn too "
            "(aligned with dashboard “risk ip”). Ignored if --jobspy-site or --jobspy-sites is set."
        ),
    )
    ap.add_argument(
        "--jobspy-site",
        default=None,
        choices=["indeed", "linkedin", "google"],
        help="Single JobSpy site (overrides --jobspy-sites and --jobspy-risk-sites)",
    )
    ap.add_argument("--jobspy-results", type=int, default=8, help="Max JobSpy scrape results per query (except LinkedIn; capped by --jobs-per-source)")
    ap.add_argument(
        "--risk-jobspy-per-site",
        type=int,
        default=3,
        metavar="N",
        help="Max jobs for JobSpy LinkedIn only (default: 3)",
    )
    ap.add_argument(
        "--jobs-per-source",
        type=int,
        default=1,
        help="Max jobs to keep per board/source (passed as child --limit)",
    )
    ap.add_argument(
        "--location-preference",
        default="",
        help="Override location hint for all users; if empty, use each row's Location column (first token), else default india (India + Indian cities across boards)",
    )
    ap.add_argument(
        "--no-location-fallback",
        action="store_true",
        help="Disable second pass with broader location/geo when prefer pass returns no jobs",
    )
    ap.add_argument(
        "--all-sources",
        action="store_true",
        help="Same as defaults: Workday, Jobvite, SmartRecruiters, custom ATS (on by default)",
    )
    ap.add_argument("--ashby-compensation", action="store_true", help="Pass includeCompensation to Ashby API")
    ap.add_argument(
        "--custom-ats",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include Netflix, Spotify, Uber fetchers (default: on; use --no-custom-ats to skip)",
    )
    ap.add_argument(
        "--workday",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include boards from job_boards/workday_boards.json (default: on; use --no-workday to skip)",
    )
    ap.add_argument(
        "--jobvite",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include slugs from job_boards/jobvite_boards.txt (default: on; use --no-jobvite to skip)",
    )
    ap.add_argument(
        "--smartrecruiters",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include slugs from job_boards/smartrecruiters_boards.txt (default: on; use --no-smartrecruiters to skip)",
    )
    ap.add_argument(
        "--greenhouse-india-only",
        action="store_true",
        help="Greenhouse & Lever: force India location filter (also on automatically when user location hint looks India-specific, e.g. CSV city or default india)",
    )
    ap.add_argument(
        "--netflix-location",
        default="",
        help='Netflix API location= (e.g. "Mumbai,India") — same as careers URL',
    )
    ap.add_argument(
        "--netflix-team",
        action="append",
        dest="netflix_teams",
        default=None,
        metavar="NAME",
        help="Netflix Team facet; repeat (e.g. --netflix-team 'Data & Insights' --netflix-team Engineering)",
    )
    ap.add_argument(
        "--netflix-work-type",
        action="append",
        dest="netflix_work_types",
        default=None,
        metavar="TYPE",
        help="Netflix work type (onsite / remote); repeat for multiple",
    )
    ap.add_argument(
        "--netflix-sort-by",
        choices=["relevance", "new", "old"],
        default=None,
        help="Netflix sort_by (careers URL sort_by=relevance)",
    )
    ap.add_argument(
        "--eta-interval",
        type=int,
        default=10,
        metavar="N",
        help="While fetching each user, print ETA every N sources (0 = disable)",
    )
    args = ap.parse_args()

    if args.all_sources:
        args.custom_ats = True
        args.workday = True
        args.jobvite = True
        args.smartrecruiters = True

    if args.jobspy_site:
        jss = [args.jobspy_site.strip().lower()]
    elif args.jobspy_sites is not None:
        jss = _parse_jobspy_sites(args.jobspy_sites)
    elif args.jobspy_risk_sites:
        jss = sorted(JOBSPY_SITE_CHOICES)
    else:
        jss = jobspy_sites_full_pipeline(include_risky_jobspy=False)

    ignore_words = [x.strip() for x in args.ignore_title.split(",") if x.strip()]
    opts = FetchOpts(
        ignore_title_words=ignore_words,
        user_lat=args.location_lat,
        user_lng=args.location_lng,
        radius_miles=args.location_radius_miles,
        page_size=args.page_size,
        jobspy_sites=jss,
        jobspy_results=args.jobspy_results,
        risk_jobspy_per_site=max(1, min(int(args.risk_jobspy_per_site), 50)),
        ashby_compensation=args.ashby_compensation,
        custom_ats=args.custom_ats,
        workday=args.workday,
        jobvite=args.jobvite,
        smartrecruiters=args.smartrecruiters,
        greenhouse_lever_india_only=args.greenhouse_india_only,
        jobs_per_source=max(1, args.jobs_per_source),
        location_preference=args.location_preference or "",
        location_fallback=not args.no_location_fallback,
        netflix_location=args.netflix_location,
        netflix_sort_by=args.netflix_sort_by or "",
        netflix_teams=list(args.netflix_teams or []),
        netflix_work_types=list(args.netflix_work_types or []),
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    users_path = USER_CSV
    if not users_path.exists():
        print(f"Missing {USER_CSV.relative_to(PROJECT_ROOT)} — create it under input/")
        sys.exit(1)

    with open(users_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        users = list(reader)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"fetch_{stamp}.log"
    tee = RunTee(log_path)
    timing_ema = _load_timing_ema()
    configs_preview = build_configs(opts)
    est_all_sec = _estimate_run_seconds(configs_preview, timing_ema, len(users))

    all_failures: list[dict[str, Any]] = []
    per_user_stats: list[tuple[str, dict[str, Any]]] = []

    n_gh = len(_read_board_lines(GREENHOUSE_BOARDS)) if GREENHOUSE_BOARDS.exists() else 0
    tee.emit(f"Log file: {log_path.relative_to(PROJECT_ROOT)}")
    tee.emit(
        f"Estimated duration for this run: ~{_fmt_dur(est_all_sec)} "
        f"({len(users)} user(s) × {len(configs_preview)} sources; "
        f"based on {SOURCE_TIMING_EMA_JSON.name} or {_DEFAULT_SOURCE_SEC_ESTIMATE:.0f}s per new source)"
    )
    tee.emit(
        f"Boards: {n_gh} Greenhouse slug(s) in job_boards/greenhouse_boards.txt; "
        "fetcher code under sources/. JobSpy default skips LinkedIn unless --jobspy-risk-sites or explicit --jobspy-sites."
    )

    run_wall0 = time.perf_counter()
    try:
        for user in users:
            name = user.get("Name", "").strip()
            roles = user.get("Roles", "") or ""
            skills = user.get("Skills", "") or ""
            csv_loc = user.get("Location", "") or ""

            keywords_tuple = parse_keywords(roles, skills)
            primary = keywords_tuple[0]
            loc_hint = _resolve_user_location_hint(opts.location_preference, csv_loc)
            loc_display = loc_hint

            tee.emit(f"\nFetching jobs for: {name}")
            tee.emit(f"  Roles (search priority): {primary[:4]}")
            tee.emit(f"  Keywords (roles+skills): {primary}")
            tee.emit(f"  Location hint: {loc_display}")

            jobs, fails, stats = fetch_all_for_user(
                keywords_tuple,
                opts,
                loc_hint,
                timing_ema=timing_ema,
                emit=tee.emit,
                eta_every=max(0, args.eta_interval),
            )
            all_failures.extend(fails)
            per_user_stats.append((name or "(unnamed)", stats))
            _save_timing_ema(timing_ema)
            _print_run_stats_block(f"\n  --- Stats for {name or '(unnamed)'} ---", stats, emit=tee.emit)

            safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in name).replace(" ", "_").strip("_")
            out_path = OUTPUT_DIR / f"jobs_{safe_name}.csv"

            fieldnames = [
                "title",
                "link",
                "company",
                "location",
                "category",
                "job_type",
                "published",
                "source",
            ]
            if jobs and jobs[0].keys() - set(fieldnames):
                fieldnames = list(jobs[0].keys())

            def _quote(v: str) -> str:
                v = str(v)
                if "," in v or '"' in v or "\n" in v:
                    return '"' + v.replace('"', '""') + '"'
                return v

            def _row_line(row: dict) -> str:
                return ", ".join(_quote(row.get(k, "")) for k in fieldnames)

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(_row_line({k: k for k in fieldnames}) + "\n")
                for row in jobs:
                    f.write(_row_line(row) + "\n")
            rel_out = out_path.relative_to(PROJECT_ROOT)
            if jobs:
                tee.emit(f"  Saved {len(jobs)} jobs to {rel_out}")
            else:
                tee.emit(f"  Wrote {rel_out} (header only, 0 jobs — check filters, keywords, or failure report below)")

        _print_failure_report(all_failures, emit=tee.emit)

        total_wall = time.perf_counter() - run_wall0
        tee.emit("\n=== Final run summary (all users) ===")
        tee.emit(f"  Users processed: {len(users)}")
        if per_user_stats:
            s0 = per_user_stats[0][1]
            tee.emit(f"  Job sources configured (per user): {s0['sources_configured']}")
            tee.emit(f"  Runnable sources (per user): {s0['sources_runnable']}")
        tot_jobs = sum(s[1]["final_rows"] for s in per_user_stats)
        tot_merged = sum(s[1]["duplicate_urls_merged"] for s in per_user_stats)
        tot_fail_ev = sum(s[1]["failure_events"] for s in per_user_stats)
        tot_no_job = sum(s[1]["sources_no_job_after_fetch"] for s in per_user_stats)
        tot_delivered = sum(s[1]["sources_delivered_pre_filters"] for s in per_user_stats)
        tee.emit(f"  Sum of final unique jobs (all CSVs): {tot_jobs}")
        tee.emit(f"  Sum of duplicate URLs merged (all users): {tot_merged}")
        tee.emit(f"  Sum of failure diagnostic events (all users): {tot_fail_ev}")
        tee.emit(f"  Sum of sources with no job after fetch (all users): {tot_no_job}")
        tee.emit(f"  Sum of sources that delivered ≥1 job (all users): {tot_delivered}")
        tee.emit(f"  Output directory: {OUTPUT_DIR.relative_to(PROJECT_ROOT)}/")
        tee.emit(f"  Total run wall time: {_fmt_dur(total_wall)} (pre-run estimate was ~{_fmt_dur(est_all_sec)})")
        tee.emit("\n### MACHINE_READABLE_SUMMARY_JSON")
        tee.emit(
            json.dumps(
                {
                    "total_wall_seconds": round(total_wall, 3),
                    "estimated_seconds_before_run": round(est_all_sec, 3),
                    "users_processed": len(users),
                    "final_jobs_rows_sum": tot_jobs,
                    "failure_events_sum": tot_fail_ev,
                    "timing_ema_file": str(SOURCE_TIMING_EMA_JSON.relative_to(PROJECT_ROOT)),
                },
                indent=2,
            )
        )
        tee.emit("\nDone.")
    finally:
        tee.close()


if __name__ == "__main__":
    main()
