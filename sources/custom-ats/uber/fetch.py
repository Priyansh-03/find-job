#!/usr/bin/env python3
"""Uber careers search API (public POST)."""
import argparse
import csv
import json
import sys

import requests

API = "https://www.uber.com/api/loadSearchJobsResults"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-fetch/1.0)",
    "Content-Type": "application/json",
    "x-csrf-token": "x",
}


def fetch_uber(limit: int = 50, max_pages: int = 20, max_jobs: int = 0) -> list[dict]:
    jobs: list[dict] = []
    for page in range(max_pages):
        body = {"params": {}, "page": page, "limit": limit}
        r = requests.post(API, headers=HEADERS, data=json.dumps(body), timeout=(15, 45))
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "success":
            break
        results = (data.get("data") or {}).get("results") or []
        if not results:
            break
        for p in results:
            jid = p.get("id")
            link = f"https://www.uber.com/careers/list/{jid}/" if jid else ""
            loc = p.get("location") or ""
            if isinstance(loc, dict):
                loc = loc.get("name") or str(loc)
            loc_s = loc if isinstance(loc, str) else str(loc or "")
            jobs.append({
                "title": p.get("title") or "",
                "link": link,
                "company": "Uber",
                "category": p.get("department") or p.get("team") or "",
                "job_type": p.get("type") or "",
                "published": str(p.get("creationDate") or ""),
                "location": loc_s.strip(),
            })
            if max_jobs > 0 and len(jobs) >= max_jobs:
                return jobs
        if len(results) < limit:
            break
    return jobs


def main() -> int:
    ap = argparse.ArgumentParser(description="Uber jobs (public API)")
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--limit", type=int, default=0, help="Max jobs to keep after keyword filter")
    ap.add_argument(
        "--page-size",
        type=int,
        default=50,
        help="Jobs per API page (POST body limit)",
    )
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    try:
        cap = args.limit if args.limit > 0 else 0
        jobs = fetch_uber(
            limit=max(1, min(args.page_size, 100)),
            max_jobs=cap or 0,
        )
    except requests.RequestException as e:
        print(f"uber: {e}", file=sys.stderr)
        return 1
    if args.keywords:
        jobs = [
            j
            for j in jobs
            if any(
                kw.lower() in (j["title"] + j.get("category", "") + j.get("location", "")).lower()
                for kw in args.keywords
            )
        ]
    if args.limit > 0:
        jobs = jobs[: args.limit]
    print(f"uber: {len(jobs)} jobs")
    if jobs:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["title", "link", "company", "category", "job_type", "published", "location"],
            )
            w.writeheader()
            w.writerows(jobs)
        print(f"Saved to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
