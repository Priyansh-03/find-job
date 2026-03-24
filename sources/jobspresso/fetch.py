#!/usr/bin/env python3
"""Fetch jobs from Jobspresso RSS feed. Job listings only, no articles."""
import argparse
import csv
import feedparser

# remote-work-jobs/feed/ has no items; use WP job_listing post type
RSS_URL = "https://jobspresso.co/feed/?post_type=job_listing"
ARTICLE_PATTERNS = ("how to", "guide", "article", "top 10", "5 free", "tips", "blog:")

def is_article(title: str) -> bool:
    t = title.lower()
    return any(p in t for p in ARTICLE_PATTERNS)

def fetch_jobs() -> list[dict]:
    feed = feedparser.parse(RSS_URL)
    jobs = []
    for e in feed.entries:
        title = getattr(e, "title", "") or ""
        if is_article(title):
            continue
        jobs.append({
            "title": title,
            "link": getattr(e, "link", "") or "",
            "summary": getattr(e, "summary", "")[:200] if getattr(e, "summary", None) else "",
            "published": getattr(e, "published", "") or "",
        })
    return jobs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", nargs="+", help="Filter by keywords")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    jobs = fetch_jobs()
    print(f"Jobspresso: {len(jobs)} jobs")
    if args.keywords:
        jobs = [j for j in jobs if any(kw.lower() in (j["title"] + j["summary"]).lower() for kw in args.keywords)]
        print(f"  Filtered: {len(jobs)}")
    if args.limit:
        jobs = jobs[:args.limit]
    for i, j in enumerate(jobs, 1):
        print(f"  {i}. {j['title']}\n     {j['link']}")
    if jobs:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["title", "link", "summary", "published"])
            w.writeheader()
            w.writerows(jobs)
        print(f"\nSaved to {args.out}")

if __name__ == "__main__":
    main()
