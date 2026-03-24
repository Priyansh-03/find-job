#!/usr/bin/env python3
"""Fetch jobs from Jobicy API. https://jobicy.com/api/v2/remote-jobs"""
import argparse
import csv
import requests

API_URL = "https://jobicy.com/api/v2/remote-jobs"


def fetch_jobs(count: int = 50, keywords: str = "", geo: str = "") -> list[dict]:
    params = {"count": min(count, 100)}
    if keywords:
        params["keywords"] = keywords
    if geo:
        params["geo"] = geo  # apac, emea, latam, usa, canada, uk, etc.
    r = requests.get(API_URL, params=params, timeout=30)
    if r.status_code == 400 and keywords:
        params.pop("keywords", None)
        r = requests.get(API_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    jobs_raw = data.get("jobs", [])
    jobs = []
    for j in jobs_raw:
        jt = j.get("jobType", "")
        if isinstance(jt, list):
            jt = ", ".join(str(x) for x in jt)
        geo = j.get("jobGeo") or ""
        if isinstance(geo, list):
            geo = ", ".join(str(x) for x in geo)
        jobs.append({
            "title": j.get("jobTitle", ""),
            "link": j.get("url", ""),
            "company": j.get("companyName", ""),
            "category": ", ".join(j.get("jobIndustry", [])) if isinstance(j.get("jobIndustry"), list) else (j.get("jobIndustry") or ""),
            "job_type": jt,
            "published": j.get("pubDate", ""),
            "location": str(geo).strip(),
            "_pub_dt": j.get("pubDate"),
        })
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=20, help="Max jobs (1-100)")
    ap.add_argument(
        "--keywords",
        nargs="*",
        default=[],
        help="Search keywords (repeat or space-separated via orchestrator)",
    )
    ap.add_argument("--geo", help="Region: apac, emea, latam, usa, canada, uk (India→apac)")
    ap.add_argument("--company", help="Post-filter: company name (partial match)")
    ap.add_argument("--job-type", help="Post-filter: Full-Time, Part-Time, Contract")
    ap.add_argument("--since", type=int, default=0, help="Only jobs from last N days (0=all)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    kw_joined = " ".join(args.keywords).strip() if args.keywords else ""
    jobs = fetch_jobs(count=args.count, keywords=kw_joined, geo=args.geo or "")
    if kw_joined and jobs:
        kw_lower = kw_joined.lower().split()
        def match(j):
            cat = j.get("category", "") or ""
            if isinstance(cat, list):
                cat = " ".join(str(x) for x in cat)
            text = (j.get("title", "") + " " + j.get("company", "") + " " + str(cat)).lower()
            return any(k in text for k in kw_lower)
        jobs = [j for j in jobs if match(j)]
    if args.company:
        jobs = [j for j in jobs if args.company.lower() in (j.get("company", "") or "").lower()]
    if args.job_type:
        jobs = [j for j in jobs if args.job_type.lower() in (j.get("job_type", "") or "").lower()]
    if args.since:
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.since)
        def ok(j):
            d = j.get("_pub_dt", "")
            if not d:
                return True
            try:
                dt = datetime.fromisoformat(str(d).replace("Z", "+00:00"))
                return dt.replace(tzinfo=timezone.utc) >= cutoff
            except (ValueError, TypeError):
                return True
        jobs = [j for j in jobs if ok(j)]
    for j in jobs:
        j.pop("_pub_dt", None)
    print(f"Jobicy: {len(jobs)} jobs")
    if args.limit > 0:
        jobs = jobs[: args.limit]
    for i, j in enumerate(jobs[:15], 1):
        print(f"  {i}. {j['title']} @ {j.get('company','')}\n     {j['link']}")
    if jobs:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["title", "link", "company", "category", "job_type", "published", "location"],
            )
            w.writeheader()
            w.writerows(jobs)
        print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
