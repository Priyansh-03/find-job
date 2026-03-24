#!/usr/bin/env python3
"""Fetch jobs from The Muse. https://www.themuse.com/api/public/jobs - verified working."""
import argparse
import csv
import requests

API_URL = "https://www.themuse.com/api/public/jobs"


def fetch_jobs(pages: int = 5) -> list[dict]:
    jobs = []
    for page in range(1, pages + 1):
        r = requests.get(API_URL, params={"page": page}, timeout=30)
        r.raise_for_status()
        data = r.json()
        results = data.get("results") or []
        for j in results:
            refs = j.get("refs") or {}
            if isinstance(refs, str):
                try:
                    import ast
                    refs = ast.literal_eval(refs)
                except Exception:
                    refs = {}
            company = j.get("company") or {}
            if isinstance(company, str):
                try:
                    import ast
                    company = ast.literal_eval(company)
                except Exception:
                    company = {}
            company_name = company.get("name", "") if isinstance(company, dict) else str(company)
            loc_raw = j.get("locations", "") or ""
            loc_str = str(loc_raw) if loc_raw else ""
            jobs.append({
                "title": j.get("name", ""),
                "link": refs.get("landing_page", ""),
                "company": company_name,
                "category": "",
                "job_type": "",
                "published": j.get("publication_date", ""),
                "_location": loc_str,
                "_pub_date": j.get("publication_date"),
            })
        if not results:
            break
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=5, help="Number of pages to fetch (20 jobs/page)")
    ap.add_argument("--location", help="Filter by location (e.g. india)")
    ap.add_argument("--company", help="Post-filter: company name (partial match)")
    ap.add_argument("--since", type=int, default=0, help="Only jobs from last N days (0=all)")
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    jobs = fetch_jobs(pages=args.pages)
    if args.location:
        kw = args.location.lower()
        jobs = [j for j in jobs if kw in (j.get("_location", "") or "").lower()]
    if args.company:
        jobs = [j for j in jobs if args.company.lower() in (j.get("company", "") or "").lower()]
    if args.since:
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.since)
        def ok(j):
            d = j.get("_pub_date", "")
            if not d:
                return True
            try:
                dt = datetime.fromisoformat(str(d).replace("Z", "+00:00"))
                return dt.replace(tzinfo=timezone.utc) >= cutoff
            except (ValueError, TypeError):
                return True
        jobs = [j for j in jobs if ok(j)]
    for j in jobs:
        j.pop("_location", None)
        j.pop("_pub_date", None)
    print(f"The Muse: {len(jobs)} jobs")
    if args.keywords:
        jobs = [j for j in jobs if any(kw.lower() in (j["title"] + j.get("company", "") + j.get("category", "")).lower() for kw in args.keywords)]
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
