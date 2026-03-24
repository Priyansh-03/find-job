#!/usr/bin/env python3
"""Spotify jobs (lifeatspotify Animal API)."""
import argparse
import csv
import sys

import requests

API = "https://api-dot-new-spotifyjobs-com.nw.r.appspot.com/wp-json/animal/v1/job/search"
JOB_URL = "https://www.lifeatspotify.com/jobs/{id}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; job-fetch/1.0)"}


def fetch_spotify() -> list[dict]:
    r = requests.get(API, headers=HEADERS, timeout=45)
    r.raise_for_status()
    data = r.json()
    rows = data.get("result") or []
    jobs = []
    for p in rows:
        jid = p.get("id")
        title = p.get("text") or ""
        link = JOB_URL.format(id=jid) if jid is not None else ""
        locs = p.get("locations") or []
        loc_str = ", ".join(str(x) for x in locs) if isinstance(locs, list) else str(locs)
        jobs.append({
            "title": title,
            "link": link,
            "company": "Spotify",
            "category": p.get("main_category") or p.get("sub_category") or "",
            "job_type": p.get("job_type") or "",
            "published": "",
            "location": loc_str.strip(),
        })
    return jobs


def main() -> int:
    ap = argparse.ArgumentParser(description="Spotify jobs (public API)")
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    try:
        jobs = fetch_spotify()
    except requests.RequestException as e:
        print(f"spotify: {e}", file=sys.stderr)
        return 1
    if args.keywords:
        def _haystack(job: dict) -> str:
            t = job.get("title") or ""
            c = job.get("category", "")
            if not isinstance(c, str):
                c = str(c) if c is not None else ""
            loc = job.get("location", "") or ""
            return (t + c + loc).lower()

        jobs = [j for j in jobs if any(kw.lower() in _haystack(j) for kw in args.keywords)]
    if args.limit > 0:
        jobs = jobs[: args.limit]
    print(f"spotify: {len(jobs)} jobs")
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
