#!/usr/bin/env python3
"""Fetch jobs from Arbeitnow API. https://arbeitnow.com/api/job-board-api - no auth."""
import argparse
import csv
import requests

API_URL = "https://arbeitnow.com/api/job-board-api"


def fetch_jobs(page: int = 1, per_page: int = 50) -> list[dict]:
    r = requests.get(API_URL, params={"page": page, "per_page": per_page}, timeout=30)
    r.raise_for_status()
    data = r.json()
    jobs_raw = data.get("data", [])
    jobs = []
    for j in jobs_raw:
        job_types = j.get("job_types", [])
        jt = ", ".join(job_types) if isinstance(job_types, list) else str(job_types or "")
        tags = j.get("tags", [])
        cat = ", ".join(tags[:3]) if isinstance(tags, list) else ""
        loc = j.get("location", "") or ""
        jobs.append({
            "title": j.get("title", ""),
            "link": j.get("url", ""),
            "company": j.get("company_name", ""),
            "category": cat,
            "job_type": jt,
            "published": str(j.get("created_at", "")),
            "_location": loc,
            "_epoch": j.get("created_at"),
        })
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--per-page", type=int, default=50)
    ap.add_argument("--location", help="Filter by location (e.g. india, remote)")
    ap.add_argument("--company", help="Post-filter: company name (partial match)")
    ap.add_argument("--job-type", help="Post-filter: full-time, part-time, contract, etc.")
    ap.add_argument("--since", type=int, default=0, help="Only jobs from last N days (0=all)")
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    jobs = fetch_jobs(page=args.page, per_page=args.per_page)
    if args.location:
        kw = args.location.lower()
        jobs = [j for j in jobs if kw in (j.get("_location", "") or "").lower()]
    if args.company:
        jobs = [j for j in jobs if args.company.lower() in (j.get("company", "") or "").lower()]
    if args.job_type:
        jobs = [j for j in jobs if args.job_type.lower() in (j.get("job_type", "") or "").lower()]
    if args.since:
        import time
        cutoff = int(time.time()) - args.since * 86400
        jobs = [j for j in jobs if (j.get("_epoch") or 0) >= cutoff]
    for j in jobs:
        j.pop("_location", None)
        j.pop("_epoch", None)
    print(f"Arbeitnow: {len(jobs)} jobs")
    if args.keywords:
        jobs = [j for j in jobs if any(kw.lower() in (j["title"] + j.get("company", "") + j.get("category", "")).lower() for kw in args.keywords)]
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
