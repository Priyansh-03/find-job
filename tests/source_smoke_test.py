#!/usr/bin/env python3
"""
Smoke-test every orchestrator source: one subprocess each with the same keyword/locale
setup as fetch_for_users (via _build_args + _run_fetcher).

Examples:
  python tests/source_smoke_test.py --jobspy-only
  python tests/source_smoke_test.py --max-sources 10
  python tests/source_smoke_test.py --include-linkedin-risk
  python tests/source_smoke_test.py --json-out logs/source_smoke_report.json

Exit code 1 if any source had a hard failure (non-zero exit, timeout, exception).
Exit code 0 otherwise (empty results are still "ok" for fragile APIs).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fetch_for_users import (  # noqa: E402
    FetchOpts,
    SCRIPT_DIR,
    VENV_PY,
    _build_args,
    _run_fetcher,
    build_configs,
    jobspy_sites_full_pipeline,
    parse_keywords,
    _resolve_user_location_hint,
    adapt_keywords_for_source,
)
from paths import LOG_DIR, OUTPUT_DIR, USER_CSV  # noqa: E402


def _default_keywords_and_location() -> tuple[tuple, str]:
    if USER_CSV.is_file():
        with open(USER_CSV, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            row = next(iter(reader), None)
        if row:
            roles = (row.get("Roles") or "").strip() or "software engineer"
            skills = (row.get("Skills") or "").strip() or "python"
            loc_col = (row.get("Location") or "").strip()
            return parse_keywords(roles, skills), _resolve_user_location_hint("", loc_col)
    return parse_keywords("software engineer", "python"), _resolve_user_location_hint("", "")


def _csv_nonempty_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    n = 0
    for row in rows:
        if row is None:
            continue
        parts = [
            (row.get(k) or "").strip()
            for k in ("title", "link", "url", "job_url", "company", "position")
            if row.get(k) is not None
        ]
        if any(parts):
            n += 1
    return n


def _effective_cap(name: str, opts: FetchOpts) -> int:
    base = max(1, opts.jobs_per_source)
    if name == "jobspy-linkedin":
        return max(1, min(opts.risk_jobspy_per_site, 50))
    return base


def _timeout_for(name: str, workday_sec: int, default_sec: int) -> int:
    if name.startswith("workday-") or name.endswith("-ats"):
        return workday_sec
    return default_sec


def _make_opts(
    *,
    include_linkedin_risk: bool,
    jobs_per_source: int,
    jobspy_results: int,
) -> FetchOpts:
    sites = jobspy_sites_full_pipeline(include_risky_jobspy=include_linkedin_risk)
    return FetchOpts(
        ignore_title_words=[],
        user_lat=None,
        user_lng=None,
        radius_miles=None,
        page_size=0,
        jobspy_sites=sites,
        jobspy_results=max(1, jobspy_results),
        risk_jobspy_per_site=max(1, min(jobspy_results, 10)),
        ashby_compensation=False,
        custom_ats=True,
        workday=True,
        jobvite=True,
        smartrecruiters=True,
        greenhouse_lever_india_only=False,
        jobs_per_source=max(1, jobs_per_source),
        location_preference="",
        location_fallback=True,
        netflix_location="",
        netflix_sort_by="",
        netflix_teams=[],
        netflix_work_types=[],
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Smoke-test all orchestrator sources")
    ap.add_argument(
        "--jobspy-only",
        action="store_true",
        help="Only sources whose names start with jobspy-",
    )
    ap.add_argument(
        "--include-linkedin-risk",
        action="store_true",
        help="Include JobSpy LinkedIn in site list (higher block risk)",
    )
    ap.add_argument("--jobs-per-source", type=int, default=1, metavar="N")
    ap.add_argument("--jobspy-results", type=int, default=5, metavar="N")
    ap.add_argument("--timeout-default", type=int, default=75)
    ap.add_argument("--timeout-workday-ats", type=int, default=120)
    ap.add_argument("--max-sources", type=int, default=0, metavar="N", help="Stop after N sources (0 = no limit)")
    ap.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write machine-readable report (default: logs/source_smoke_<utc>.json)",
    )
    ap.add_argument("--quiet", action="store_true", help="Less console output during runs")
    args = ap.parse_args()

    if not VENV_PY.is_file():
        print(f"Missing venv Python: {VENV_PY}", file=sys.stderr)
        return 2

    kw_tuple, loc_hint = _default_keywords_and_location()
    if not (loc_hint or "").strip():
        loc_hint = _resolve_user_location_hint("", "")
    primary = kw_tuple[0]
    opts = _make_opts(
        include_linkedin_risk=args.include_linkedin_risk,
        jobs_per_source=args.jobs_per_source,
        jobspy_results=args.jobspy_results,
    )
    configs = build_configs(opts)
    if args.jobspy_only:
        configs = [(n, s) for n, s in configs if n.startswith("jobspy-")]

    scratch = OUTPUT_DIR / "_source_smoke_scratch.csv"
    results: list[dict] = []
    hard_failures = 0

    def emit(msg: str = "") -> None:
        if not args.quiet and msg:
            print(msg)

    print(
        f"Keywords: {primary!r} | location hint: {loc_hint!r} | sources: {len(configs)}",
        flush=True,
    )

    for i, (name, script) in enumerate(configs):
        if args.max_sources and i >= args.max_sources:
            break
        rel = SCRIPT_DIR / script
        if not rel.is_file():
            results.append(
                {
                    "source": name,
                    "script": script,
                    "status": "skipped",
                    "reason": "script_missing",
                    "jobs_with_link": 0,
                    "csv_nonempty_rows": 0,
                }
            )
            if not args.quiet:
                print(f"[SKIP] {name}: script not found", flush=True)
            continue

        cap = _effective_cap(name, opts)
        adap = adapt_keywords_for_source(name, primary)
        try:
            argv = _build_args(
                name,
                adap,
                cap,
                opts,
                user_location_hint=loc_hint,
                arg_variant="prefer",
            )
        except Exception as e:
            hard_failures += 1
            results.append(
                {
                    "source": name,
                    "script": script,
                    "status": "error",
                    "reason": "build_args_exception",
                    "detail": str(e),
                    "jobs_with_link": 0,
                    "csv_nonempty_rows": 0,
                }
            )
            if not args.quiet:
                print(f"[ERR] {name}: _build_args: {e}", flush=True)
            continue

        to = _timeout_for(name, args.timeout_workday_ats, args.timeout_default)
        count, jobs, diag = _run_fetcher(
            name,
            script,
            argv,
            timeout=to,
            out_csv=scratch,
            emit=emit,
        )
        rows = _csv_nonempty_rows(scratch)
        linked = len(jobs) if jobs else int(count)

        if diag:
            kind = diag.get("kind", "unknown")
            if kind in ("exit_error", "timeout", "exception"):
                hard_failures += 1
            status = "fail" if kind in ("exit_error", "timeout", "exception") else "degraded"
            results.append(
                {
                    "source": name,
                    "script": script,
                    "status": status,
                    "diag_kind": kind,
                    "hint": diag.get("hint"),
                    "stderr_tail": (diag.get("stderr") or "")[:400],
                    "jobs_with_link": linked,
                    "csv_nonempty_rows": rows,
                    "timeout_sec": to,
                }
            )
            if not args.quiet:
                print(
                    f"[{status.upper()}] {name}: {kind} | rows(csv)={rows} linked={linked}",
                    flush=True,
                )
        else:
            status = "ok" if (linked > 0 or rows > 0) else "empty"
            results.append(
                {
                    "source": name,
                    "script": script,
                    "status": status,
                    "jobs_with_link": linked,
                    "csv_nonempty_rows": rows,
                    "timeout_sec": to,
                }
            )
            if not args.quiet:
                print(
                    f"[{status.upper()}] {name}: linked={linked} csv_nonempty_rows={rows}",
                    flush=True,
                )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "venv_py": str(VENV_PY),
        "location_hint": loc_hint,
        "primary_keywords": primary,
        "opts": {
            "jobspy_sites": opts.jobspy_sites,
            "jobs_per_source": opts.jobs_per_source,
            "jobspy_results": opts.jobspy_results,
            "include_linkedin_risk": args.include_linkedin_risk,
        },
        "counts": {
            "sources": len(results),
            "hard_failures": hard_failures,
            "empty": sum(1 for r in results if r.get("status") == "empty"),
            "ok": sum(1 for r in results if r.get("status") == "ok"),
            "fail": sum(1 for r in results if r.get("status") == "fail"),
            "skipped": sum(1 for r in results if r.get("status") == "skipped"),
        },
        "results": results,
    }

    if args.json_out is None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = (LOG_DIR / f"source_smoke_{stamp}.json").resolve()
    else:
        out_path = Path(args.json_out)
        out_path = out_path.resolve() if out_path.is_absolute() else (ROOT / out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    try:
        rel = out_path.relative_to(ROOT)
    except ValueError:
        rel = out_path
    print(f"\nWrote {rel}", flush=True)
    print(
        f"Summary: ok={summary['counts']['ok']} empty={summary['counts']['empty']} "
        f"fail={summary['counts']['fail']} skipped={summary['counts']['skipped']} "
        f"hard_failures={hard_failures}",
        flush=True,
    )
    return 1 if hard_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
