#!/usr/bin/env python3
"""Fetch jobs from Himalayas. https://himalayas.app/jobs/api - verified working."""
import argparse
import csv
import re
import requests

API_URL = "https://himalayas.app/jobs/api"


def _keyword_matches_blob(kw: str, blob: str) -> bool:
    """Avoid false positives (e.g. ``ai`` matching inside unrelated words)."""
    k = (kw or "").strip().lower()
    if not k:
        return False
    if " " in k:
        return k in blob
    return re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", blob) is not None


def fetch_jobs(q: str = "engineer", limit: int = 100) -> list[dict]:
    jobs_raw = []
    offset = 0
    page_size = 20  # API returns max 20 per request
    while len(jobs_raw) < limit:
        r = requests.get(API_URL, params={"q": q, "limit": page_size, "offset": offset}, timeout=30)
        r.raise_for_status()
        data = r.json()
        batch = data.get("jobs") or []
        if not batch:
            break
        jobs_raw.extend(batch)
        offset += len(batch)
        if len(batch) < page_size:
            break
    jobs_raw = jobs_raw[:limit]  # cap at requested limit
    jobs = []
    for j in jobs_raw:
        locs = j.get("locationRestrictions", []) or []
        loc_str = ",".join(locs) if isinstance(locs, list) else str(locs)
        pub = j.get("pubDate", "")
        jobs.append({
            "title": j.get("title", ""),
            "link": j.get("guid", "") or j.get("applicationLink", ""),
            "company": j.get("companyName", ""),
            "category": ",".join(j.get("categories", []) or j.get("parentCategories", [])),
            "job_type": j.get("employmentType", ""),
            "published": str(pub) if pub else "",
            "_location": loc_str,
            "_salary_min": j.get("minSalary"),
            "_salary_max": j.get("maxSalary"),
            "_epoch": pub,
        })
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", "-q", default="engineer", help="Search query")
    ap.add_argument("--location", help="Filter by location (e.g. india, worldwide)")
    ap.add_argument("--company", help="Post-filter: company name (partial match)")
    ap.add_argument("--job-type", help="Post-filter: Full Time, Part Time, Contract, etc.")
    ap.add_argument("--salary-min", type=int, help="Post-filter: min salary")
    ap.add_argument("--salary-max", type=int, help="Post-filter: max salary")
    ap.add_argument("--since", type=int, default=0, help="Only jobs from last N days (0=all)")
    ap.add_argument("--limit", type=int, default=0, help="Max jobs to save (0=all)")
    ap.add_argument("--size", type=int, default=100, help="Max jobs to fetch from API")
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    jobs = fetch_jobs(q=args.query, limit=args.size)
    if args.location:
        kw = args.location.lower()
        jobs = [j for j in jobs if kw in (j.get("_location", "") or "").lower()]
    if args.company:
        jobs = [j for j in jobs if args.company.lower() in (j.get("company", "") or "").lower()]
    if args.job_type:
        jobs = [j for j in jobs if args.job_type.lower() in (j.get("job_type", "") or "").lower()]
    if args.salary_min is not None:
        def has_min_salary(j):
            smin, smax = j.get("_salary_min"), j.get("_salary_max")
            if smin is None and smax is None:
                return True  # unknown salary, include
            return (smax or smin or 0) >= args.salary_min
        jobs = [j for j in jobs if has_min_salary(j)]
    if args.salary_max is not None:
        def within_max(j):
            smin = j.get("_salary_min")
            if smin is None:
                return True  # unknown, include
            return smin <= args.salary_max
        jobs = [j for j in jobs if within_max(j)]
    if args.since:
        import time
        cutoff = int(time.time()) - args.since * 86400
        jobs = [j for j in jobs if (j.get("_epoch") or 0) >= cutoff]
    for j in jobs:
        j.pop("_location", None)
        j.pop("_salary_min", None)
        j.pop("_salary_max", None)
        j.pop("_epoch", None)
    print(f"Himalayas: {len(jobs)} jobs")
    if args.keywords:
        def job_matches_keywords(j: dict) -> bool:
            blob = (
                (j.get("title") or "")
                + " "
                + (j.get("company") or "")
                + " "
                + (j.get("category") or "")
            ).lower()
            return any(_keyword_matches_blob(kw, blob) for kw in args.keywords)

        jobs = [j for j in jobs if job_matches_keywords(j)]
    if args.limit > 0:
        jobs = jobs[: args.limit]
    for i, j in enumerate(jobs[:20], 1):
        print(f"  {i}. {j['title']} @ {j.get('company','')}\n     {j['link']}")
    if jobs:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["title", "link", "company", "category", "job_type", "published"])
            w.writeheader()
            w.writerows(jobs)
        print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
