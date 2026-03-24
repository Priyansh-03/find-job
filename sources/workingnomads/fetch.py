#!/usr/bin/env python3
"""Fetch jobs from Working Nomads.

URL patterns:
  - Job page: /jobs?job={slug}  or  /job/go/{id}/
  - Search:   /jobs?tag=X&location=india&category=development&positionType=full-time&experienceLevel=entry-level&salary=N&postedDate=N
  - Companies: /remote-companies  or  /remote-companies?hiring=on

APIs:
  - exposed_jobs: https://www.workingnomads.com/api/exposed_jobs/  (JSON, ~29 recent jobs)
  - elasticsearch: jobsapi/_search  (POST, ~5K jobs, undocumented)
"""
import argparse
import csv
import requests

EXPOSED_JOBS_URL = "https://www.workingnomads.com/api/exposed_jobs/"
ES_URL = "https://www.workingnomads.com/jobsapi/_search"
JOB_URL_TEMPLATE = "https://www.workingnomads.com/jobs?job={slug}"


def fetch_via_exposed_jobs() -> list[dict]:
    """Public API – returns ~29 recent jobs with full metadata."""
    r = requests.get(EXPOSED_JOBS_URL, timeout=30)
    r.raise_for_status()
    data = r.json()
    jobs = []
    for j in data:
        locs = j.get("locations", []) or []
        loc_str = ",".join(locs) if isinstance(locs, list) else str(locs)
        jobs.append({
            "title": j.get("title", ""),
            "link": j.get("url", ""),
            "company": j.get("company_name", ""),
            "category": j.get("category_name", ""),
            "job_type": "",
            "published": j.get("pub_date", ""),
            "_location": loc_str,
            "_pub": j.get("pub_date"),
        })
    return jobs


def fetch_via_elasticsearch(size: int = 100) -> list[dict]:
    """Internal ES API – returns up to 5K jobs (undocumented)."""
    payload = {
        "size": min(size, 1000),
        "query": {"match_all": {}},
        "sort": [{"pub_date": "desc"}],
        "_source": ["id", "title", "slug", "company", "category_name", "position_type", "pub_date", "locations"],
    }
    r = requests.post(ES_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
    r.raise_for_status()
    data = r.json()
    hits = data.get("hits", {}).get("hits", [])
    jobs = []
    for h in hits:
        s = h.get("_source", {})
        slug = s.get("slug") or ""
        if not slug:
            continue
        locs = s.get("locations", []) or []
        loc_str = ",".join(locs) if isinstance(locs, list) else str(locs)
        jobs.append({
            "title": s.get("title", ""),
            "link": JOB_URL_TEMPLATE.format(slug=slug),
            "company": s.get("company", ""),
            "category": s.get("category_name", ""),
            "job_type": s.get("position_type", ""),
            "published": s.get("pub_date", ""),
            "_location": loc_str,
        })
    return jobs


def fetch_jobs(api: str = "elasticsearch", size: int = 100) -> list[dict]:
    if api == "exposed_jobs":
        return fetch_via_exposed_jobs()
    return fetch_via_elasticsearch(size=size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", choices=["exposed_jobs", "elasticsearch"], default="elasticsearch",
        help="exposed_jobs=~29 recent, elasticsearch=~5K (default)")
    ap.add_argument("--location", help="Filter by location (e.g. india)")
    ap.add_argument("--company", help="Post-filter: company name (partial match)")
    ap.add_argument("--job-type", help="Post-filter: full-time, part-time, etc.")
    ap.add_argument("--since", type=int, default=0, help="Only jobs from last N days (0=all)")
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--size", type=int, default=100, help="Max jobs (elasticsearch only)")
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    jobs = fetch_jobs(api=args.api, size=args.size)
    if args.location:
        kw = args.location.lower()
        jobs = [j for j in jobs if kw in (j.get("_location", "") or "").lower()]
    if args.company:
        jobs = [j for j in jobs if args.company.lower() in (j.get("company", "") or "").lower()]
    if args.job_type:
        jobs = [j for j in jobs if args.job_type.lower() in (j.get("job_type", "") or "").lower()]
    if args.since:
        from datetime import datetime
        cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=args.since)
        def ok(j):
            d = j.get("_pub", "")
            if not d:
                return True
            try:
                dt = datetime.fromisoformat(str(d).replace("Z", "+00:00"))
                return dt >= cutoff
            except (ValueError, TypeError):
                return True
        jobs = [j for j in jobs if ok(j)]
    for j in jobs:
        j.pop("_location", None)
        j.pop("_pub", None)
    print(f"Working Nomads: {len(jobs)} jobs")
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
