#!/usr/bin/env python3
"""Fetch jobs from 4 Day Week. https://4dayweek.io/api - verified working."""
import argparse
import csv
import requests

API_URL = "https://4dayweek.io/api"


def fetch_jobs() -> list[dict]:
    r = requests.get(API_URL, timeout=30)
    r.raise_for_status()
    data = r.json()
    jobs_raw = data.get("jobs") or []
    jobs = []
    for j in jobs_raw:
        loc = " ".join(
            str(x) for x in [
                j.get("location_country", ""),
                j.get("location_continent", ""),
                j.get("location_original", ""),
            ] if x
        )
        jobs.append({
            "title": j.get("title", ""),
            "link": j.get("url", ""),
            "company": j.get("company_name", ""),
            "category": j.get("role", "") or j.get("category", ""),
            "job_type": "",
            "published": str(j.get("posted", "")),
            "_location": loc,
            "_epoch": j.get("posted"),
        })
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--location", help="Filter by location (e.g. india, worldwide)")
    ap.add_argument("--company", help="Post-filter: company name (partial match)")
    ap.add_argument("--since", type=int, default=0, help="Only jobs from last N days (0=all)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    jobs = fetch_jobs()
    if args.location:
        kw = args.location.lower()
        jobs = [j for j in jobs if kw in (j.get("_location", "") or "").lower()]
    if args.company:
        jobs = [j for j in jobs if args.company.lower() in (j.get("company", "") or "").lower()]
    if args.since:
        import time
        cutoff = int(time.time()) - args.since * 86400
        jobs = [j for j in jobs if (j.get("_epoch") or 0) >= cutoff]
    for j in jobs:
        j.pop("_location", None)
        j.pop("_epoch", None)
    print(f"4 Day Week: {len(jobs)} jobs")
    if args.keywords:
        jobs = [j for j in jobs if any(kw.lower() in (j["title"] + j.get("company", "") + j.get("category", "")).lower() for kw in args.keywords)]
    if args.limit:
        jobs = jobs[: args.limit]
    for i, j in enumerate(jobs, 1):
        print(f"  {i}. {j['title']} @ {j.get('company','')}\n     {j['link']}")
    if jobs:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["title", "link", "company", "category", "job_type", "published"])
            w.writeheader()
            w.writerows(jobs)
        print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
