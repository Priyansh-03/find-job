#!/usr/bin/env python3
"""
RSS Job Feed Fetcher

Fetches remote job listings from multiple RSS feeds using feedparser.
"""

import argparse
import csv
import feedparser

FEEDS = {
    "WeWorkRemotely": "https://weworkremotely.com/jobs.rss",
    "Jobspresso": "https://jobspresso.co/remote-work-jobs/feed/",
    "DynamiteJobs": "https://dynamitejobs.com/feed",
    "EuropeRemotely": "https://europeremotely.com/feed",
    "Craigslist_LA": "https://losangeles.craigslist.org/search/jjj?format=rss",
    "ProBlogger": "https://problogger.com/jobs/feed/",
    "AuthenticJobs": "https://authenticjobs.com/feed/",
    "Larajobs": "https://larajobs.com/feed",
    "PyJobs": "https://www.pyjobs.com/api/jobs/rss",
    "SwissDevJobs": "https://swissdevjobs.ch/feed",
    "RemotePython": "https://www.remotepython.com/jobs/rss/",
    "WorkInTech": "https://www.workintech.io/jobs/rss",
}


def fetch_all_rss_jobs(feeds: dict[str, str] | None = None) -> list[dict]:
    """Fetch jobs from all RSS feeds."""
    feeds = feeds or FEEDS
    all_jobs = []

    for name, url in feeds.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                all_jobs.append({
                    "source": name,
                    "title": getattr(entry, "title", "") or "",
                    "link": getattr(entry, "link", "") or "",
                    "summary": getattr(entry, "summary", "") or "",
                    "published": getattr(entry, "published", "") or "",
                })
        except Exception as e:
            print(f"  ⚠ {name}: {e}")

    return all_jobs


def filter_jobs(jobs: list[dict], keywords: list[str] | None = None) -> list[dict]:
    """Filter jobs by keywords in title/summary."""
    if not keywords:
        return jobs
    filtered = []
    for job in jobs:
        text = f"{job.get('title', '')} {job.get('summary', '')}".lower()
        if any(kw.lower() in text for kw in keywords):
            filtered.append(job)
    return filtered


def main():
    ap = argparse.ArgumentParser(description="Fetch remote jobs from RSS feeds")
    ap.add_argument("--keywords", nargs="+", help="Filter by keywords (e.g. frontend python)")
    ap.add_argument("--limit", type=int, default=0, help="Max jobs to show (0=all)")
    ap.add_argument("--out", default="", help="Output CSV file (empty=no CSV)")
    ap.add_argument("--sources", nargs="+", help="Only fetch from these sources (default: all)")
    args = ap.parse_args()

    feeds = {k: v for k, v in FEEDS.items() if not args.sources or k in args.sources}

    print(f"Fetching from {len(feeds)} RSS feeds...")
    jobs = fetch_all_rss_jobs(feeds)
    print(f"  Fetched {len(jobs)} total jobs")

    if args.keywords:
        jobs = filter_jobs(jobs, args.keywords)
        print(f"  Filtered to {len(jobs)} matching jobs")

    if args.limit:
        jobs = jobs[: args.limit]

    for i, job in enumerate(jobs, 1):
        print(f"{i}. [{job['source']}] {job['title']}")
        print(f"   {job['link']}")

    if args.out and jobs:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["source", "title", "link", "summary", "published"])
            writer.writeheader()
            writer.writerows(jobs)
        print(f"\nSaved {len(jobs)} jobs to {args.out}")


if __name__ == "__main__":
    main()
