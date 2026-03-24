#!/usr/bin/env python3
"""Fetch jobs from JobsCollider RSS. https://jobscollider.com/remote-jobs.rss"""
import argparse
import csv
import feedparser

RSS_URL = "https://jobscollider.com/remote-jobs.rss"


def fetch_jobs() -> list[dict]:
    feed = feedparser.parse(RSS_URL)
    jobs = []
    for e in feed.entries:
        jobs.append({
            "title": e.get("title", ""),
            "link": e.get("link", ""),
            "company": "",
            "category": "",
            "job_type": "",
            "published": e.get("published", "") or e.get("updated", ""),
        })
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    jobs = fetch_jobs()
    print(f"JobsCollider: {len(jobs)} jobs")
    if args.keywords:
        jobs = [
            j
            for j in jobs
            if any(kw.lower() in (j.get("title") or "").lower() for kw in args.keywords)
        ]
    if args.limit > 0:
        jobs = jobs[: args.limit]
    for i, j in enumerate(jobs[:15], 1):
        print(f"  {i}. {j['title']}\n     {j['link']}")
    if jobs:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["title", "link", "company", "category", "job_type", "published"])
            w.writeheader()
            w.writerows(jobs)
        print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
