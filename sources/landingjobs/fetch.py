#!/usr/bin/env python3
"""Fetch jobs from Landing Jobs RSS feed. https://landing.jobs/feed"""
import argparse
import csv
import feedparser

RSS_URL = "https://landing.jobs/feed"

def fetch_jobs() -> list[dict]:
    feed = feedparser.parse(RSS_URL)
    jobs = []
    for e in feed.entries:
        jobs.append({
            "title": (getattr(e, "title", "") or "")[:200],
            "link": getattr(e, "link", "") or "",
            "company": "",
            "category": "",
            "job_type": "",
            "published": getattr(e, "published", "") or "",
        })
    return jobs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    jobs = fetch_jobs()
    print(f"Landing Jobs: {len(jobs)} jobs")
    if args.limit:
        jobs = jobs[:args.limit]
    for i, j in enumerate(jobs, 1):
        print(f"  {i}. {j['title']}\n     {j['link']}")
    if jobs:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["title", "link", "company", "category", "job_type", "published"])
            w.writeheader()
            w.writerows(jobs)
        print(f"\nSaved to {args.out}")

if __name__ == "__main__":
    main()
