#!/usr/bin/env python3
"""Netflix careers API (explore.jobs.netflix.net).

Unfiltered list:
  GET .../api/apply/v2/jobs?domain=netflix.com&start=0

Filtered search (same filters as the careers UI), e.g.:
  https://explore.jobs.netflix.net/careers?query=...&location=Mumbai%2CIndia&Teams=...&Work%20Type=onsite&sort_by=relevance

Pass the same dimensions via --query, --location, --team (repeat), --work-type (repeat), --sort-by.

If the strict combination returns no rows, the fetcher relaxes filters in order (unless --no-fallback):
drop work type → drop teams → drop location → browse without query. Each step uses the same sort_by.
"""
import argparse
import csv
import sys
from typing import Any, Callable

import requests

API = "https://explore.jobs.netflix.net/api/apply/v2/jobs"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; job-fetch/1.0)"}


def _build_params(
    start: int,
    *,
    query: str | None,
    location: str | None,
    teams: list[str] | None,
    work_types: list[str] | None,
    sort_by: str | None,
) -> list[tuple[str, Any]]:
    """Use a list of tuples so repeated keys (Teams, Work Type) encode correctly."""
    params: list[tuple[str, Any]] = [
        ("domain", "netflix.com"),
        ("start", start),
    ]
    if query:
        params.append(("query", query))
    if location:
        params.append(("location", location))
    for t in teams or []:
        if t.strip():
            params.append(("Teams", t.strip()))
    for wt in work_types or []:
        if wt.strip():
            params.append(("Work Type", wt.strip()))
    if sort_by:
        params.append(("sort_by", sort_by))
    return params


def _norm_str(s: str | None) -> str | None:
    if not s:
        return None
    t = s.strip()
    return t or None


def _norm_list(xs: list[str] | None) -> list[str] | None:
    if not xs:
        return None
    out = [x.strip() for x in xs if x and str(x).strip()]
    return out or None


def _netflix_relaxation_variants(
    query: str | None,
    location: str | None,
    teams: list[str] | None,
    work_types: list[str] | None,
) -> list[tuple[str, str | None, str | None, list[str] | None, list[str] | None]]:
    """Ordered attempts: strict, then progressively broader. Deduplicates identical API shapes."""
    q = _norm_str(query)
    loc = _norm_str(location)
    t = _norm_list(teams)
    wt = _norm_list(work_types)

    steps: list[tuple[str, str | None, str | None, list[str] | None, list[str] | None]] = [
        ("strict", q, loc, t, wt),
        ("no work-type filter", q, loc, t, None),
        ("no team filter", q, loc, None, None),
        ("no location filter", q, None, None, None),
        ("catalog (no search query)", None, None, None, None),
    ]

    seen: set[tuple[Any, ...]] = set()
    out: list[tuple[str, str | None, str | None, list[str] | None, list[str] | None]] = []
    for label, qv, lv, tv, wtv in steps:
        # Skip steps that change nothing vs previous effective API call
        eff_wt = wtv if wtv else None
        eff_t = tv if tv else None
        if label == "no work-type filter" and not wt:
            continue
        if label == "no team filter" and not t:
            continue
        if label == "no location filter" and not loc:
            continue
        if label == "catalog (no search query)" and not q:
            continue
        key = (qv, lv, tuple(eff_t or ()), tuple(eff_wt or ()))
        if key in seen:
            continue
        seen.add(key)
        out.append((label, qv, lv, eff_t, eff_wt))
    return out


def fetch_netflix(
    page_size: int = 10,
    max_pages: int = 100,
    max_jobs: int = 0,
    *,
    query: str | None = None,
    location: str | None = None,
    teams: list[str] | None = None,
    work_types: list[str] | None = None,
    sort_by: str | None = None,
) -> list[dict]:
    jobs: list[dict] = []
    start = 0
    for _ in range(max_pages):
        params = _build_params(
            start,
            query=query,
            location=location,
            teams=teams,
            work_types=work_types,
            sort_by=sort_by,
        )
        r = requests.get(API, params=params, headers=HEADERS, timeout=(15, 45))
        r.raise_for_status()
        data = r.json()
        positions = data.get("positions") or []
        if not positions:
            break
        for p in positions:
            title = p.get("posting_name") or p.get("name") or ""
            link = p.get("canonicalPositionUrl") or ""
            loc = p.get("location") or ""
            if isinstance(loc, dict):
                loc = loc.get("name") or str(loc)
            jobs.append({
                "title": title,
                "link": link,
                "company": "Netflix",
                "category": p.get("department") or "",
                "job_type": p.get("work_location_option") or p.get("type") or "",
                "published": str(p.get("t_update") or p.get("t_create") or ""),
            })
            if max_jobs > 0 and len(jobs) >= max_jobs:
                return jobs
        start += len(positions)
    return jobs


def fetch_netflix_with_fallback(
    page_size: int = 10,
    max_pages: int = 100,
    max_jobs: int = 0,
    *,
    query: str | None = None,
    location: str | None = None,
    teams: list[str] | None = None,
    work_types: list[str] | None = None,
    sort_by: str | None = None,
    fallback: bool = True,
    on_fallback: Callable[[str], None] | None = None,
) -> tuple[list[dict], str | None]:
    """Fetch jobs; if empty and fallback is True, retry with relaxed filters.

    on_fallback: optional callable(label: str) called when switching away from strict.
    Returns (jobs, label_used) where label_used is the variant name (None if unused).
    """
    variants: list[tuple[str, str | None, str | None, list[str] | None, list[str] | None]]
    if fallback:
        variants = _netflix_relaxation_variants(query, location, teams, work_types)
    else:
        variants = [
            (
                "strict",
                _norm_str(query),
                _norm_str(location),
                _norm_list(teams),
                _norm_list(work_types),
            )
        ]

    used_label: str | None = None
    for i, (label, qv, lv, tv, wtv) in enumerate(variants):
        jobs = fetch_netflix(
            page_size=page_size,
            max_pages=max_pages,
            max_jobs=max_jobs,
            query=qv,
            location=lv,
            teams=tv,
            work_types=wtv,
            sort_by=sort_by,
        )
        if jobs:
            used_label = label
            if i > 0 and on_fallback:
                on_fallback(label)
            return jobs, used_label
    return [], used_label


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Netflix jobs (public API) — supports careers-style filters",
        epilog="Example (matches careers URL facets):\n"
        '  %(prog)s --query "Artificial Intelligence" --location "Mumbai,India" \\\n'
        '    --team "Data & Insights" --team Engineering --work-type onsite --sort-by relevance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--keywords", nargs="+", help="Post-filter downloaded rows by keyword in title/category")
    ap.add_argument("--limit", type=int, default=0, help="Max jobs to collect (stops pagination early)")
    ap.add_argument(
        "--page-size",
        type=int,
        default=10,
        help="Batch size hint (API often returns 10 per page)",
    )
    ap.add_argument(
        "--query",
        default="",
        help="Search text (careers ?query=), e.g. 'Artificial Intelligence'",
    )
    ap.add_argument(
        "--location",
        default="",
        help="Location string (careers ?location=), e.g. 'Mumbai,India'",
    )
    ap.add_argument(
        "--team",
        action="append",
        dest="teams",
        default=None,
        metavar="NAME",
        help="Team facet; repeat for multiple (e.g. --team 'Data & Insights' --team Engineering)",
    )
    ap.add_argument(
        "--work-type",
        action="append",
        dest="work_types",
        default=None,
        metavar="TYPE",
        help="Work type facet; repeat (e.g. --work-type onsite --work-type remote)",
    )
    ap.add_argument(
        "--sort-by",
        choices=["relevance", "new", "old"],
        default=None,
        help="Sort order (careers sort_by)",
    )
    ap.add_argument(
        "--no-fallback",
        action="store_true",
        help="Do not relax filters when strict search returns zero jobs",
    )
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()

    q = args.query.strip() or None
    loc = args.location.strip() or None
    teams = args.teams
    work_types = args.work_types
    sort_by = args.sort_by

    def _warn_fallback(lbl: str) -> None:
        print(f"netflix: strict filters returned 0 jobs; using fallback: {lbl}", file=sys.stderr)

    jobs: list[dict] = []
    used_variant: str | None = None
    try:
        cap = args.limit if args.limit > 0 else 0
        jobs, used_variant = fetch_netflix_with_fallback(
            page_size=max(1, args.page_size),
            max_jobs=cap or 0,
            query=q,
            location=loc,
            teams=teams,
            work_types=work_types,
            sort_by=sort_by,
            fallback=not args.no_fallback,
            on_fallback=_warn_fallback,
        )
    except requests.RequestException as e:
        print(f"netflix: {e}", file=sys.stderr)
        return 1
    if args.keywords:
        jobs = [
            j
            for j in jobs
            if any(kw.lower() in (j["title"] + j.get("category", "")).lower() for kw in args.keywords)
        ]
    if args.limit > 0:
        jobs = jobs[: args.limit]
    filt = []
    if q:
        filt.append(f"query={q!r}")
    if loc:
        filt.append(f"location={loc!r}")
    if teams:
        filt.append(f"teams={teams}")
    if work_types:
        filt.append(f"work_types={work_types}")
    if sort_by:
        filt.append(f"sort_by={sort_by}")
    if used_variant and used_variant != "strict":
        filt.append(f"api_variant={used_variant}")
    extra = f" ({'; '.join(filt)})" if filt else ""
    print(f"netflix: {len(jobs)} jobs{extra}")
    if jobs:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["title", "link", "company", "category", "job_type", "published"])
            w.writeheader()
            w.writerows(jobs)
        print(f"Saved to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
