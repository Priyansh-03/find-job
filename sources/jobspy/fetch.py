#!/usr/bin/env python3
"""Fetch jobs via JobSpy. Covers Indeed, LinkedIn, Google.
pip install python-jobspy
Date filter: listings from the last JOBSPY_HOURS_OLD hours (24) only.
Keep results_wanted low to avoid rate limits.
"""
import argparse
import csv
import sys

try:
    from jobspy import scrape_jobs
    import pandas as pd
except ImportError:
    print("Run: pip install python-jobspy")
    sys.exit(1)

# JobSpy date filter: only listings from the last N hours (passed to scrape_jobs as hours_old).
JOBSPY_HOURS_OLD = 24


def _rows_to_jobs(df, *, category: str = "") -> list[dict]:
    jobs: list[dict] = []
    if df is None or df.empty:
        return jobs
    for _, row in df.iterrows():
        company = row.get("company")
        if pd.isna(company):
            company = ""
        jobs.append({
            "title": str(row.get("title", "")),
            "link": str(row.get("job_url", "") or row.get("job_url_direct", "")) or "",
            "company": str(company) if company else "",
            "category": category,
            "job_type": "" if pd.isna(row.get("job_type")) else str(row.get("job_type", "")),
            "published": "" if pd.isna(row.get("date_posted")) else str(row.get("date_posted", "")),
        })
    return jobs


def fetch_jobs(
    search_term: str = "software engineer",
    location: str = "remote",
    site_name: str = "indeed",
    results_wanted: int = 10,
    country: str = "usa",
    is_remote: bool | None = None,
) -> list[dict]:
    sites = [site_name]
    # Auto-detect remote when location contains "remote"
    if is_remote is None:
        is_remote = "remote" in (location or "").lower()

    df = scrape_jobs(
        site_name=sites,
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=JOBSPY_HOURS_OLD,
        country_indeed=country,
        is_remote=is_remote,
        verbose=0,
    )

    return _rows_to_jobs(df)


def main():
    ap = argparse.ArgumentParser(description="JobSpy fetcher - keep results low to avoid rate limits")
    ap.add_argument("--search", default="software engineer", help="Search term")
    ap.add_argument("--location", default="remote", help="Location filter")
    ap.add_argument("--site", default="indeed",
        choices=["indeed", "linkedin", "google"],
        help="Platform (indeed is least restricted)")
    ap.add_argument("--country", default="usa",
        help="Country for Indeed (usa, india, uk, canada, etc.)")
    ap.add_argument("--results", type=int, default=10, help="Max results (keep low: 10-20)")
    ap.add_argument("--no-remote", action="store_true", help="Don't filter by remote")
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    jobs = fetch_jobs(
        search_term=args.search,
        location=args.location,
        site_name=args.site,
        results_wanted=args.results,
        country=args.country,
        is_remote=False if args.no_remote else None,
    )
    print(f"JobSpy ({args.site}): {len(jobs)} jobs")
    if args.keywords:
        jobs = [j for j in jobs if any(kw.lower() in (j["title"] + j.get("company", "")).lower() for kw in args.keywords)]
    if args.limit > 0:
        jobs = jobs[: args.limit]
    for i, j in enumerate(jobs[:15], 1):
        print(f"  {i}. {j['title']} @ {j.get('company','')}\n     {j['link']}")
    if jobs:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["title", "link", "company", "category", "job_type", "published"])
            w.writeheader()
            w.writerows(jobs)
        print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
