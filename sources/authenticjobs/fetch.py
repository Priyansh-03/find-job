#!/usr/bin/env python3
"""Fetch jobs from AuthenticJobs RSS feed. Excludes blog articles.

Optional ``search_location`` uses the job_feed API, e.g. ``india``:
https://authenticjobs.com/?feed=job_feed&search_location=india
"""
from __future__ import annotations

import argparse
import csv
from urllib.parse import urlencode

import feedparser

RSS_DEFAULT = "https://authenticjobs.com/feed/"
ARTICLE_PATTERNS = (
    "how to",
    "guide",
    "article",
    "top 10",
    "5 free",
    "tips",
    "blog:",
    "career transition",
    "roles that will",
)


def is_article(title: str) -> bool:
    t = title.lower()
    return any(p in t for p in ARTICLE_PATTERNS)


def feed_url(search_location: str = "") -> str:
    if not (search_location or "").strip():
        return RSS_DEFAULT
    q = urlencode(
        {
            "feed": "job_feed",
            "job_types": "freelance,full-time,internship,part-time",
            "search_location": search_location.strip().lower(),
        }
    )
    return f"https://authenticjobs.com/?{q}"


def fetch_jobs(*, search_location: str = "") -> list[dict]:
    url = feed_url(search_location)
    feed = feedparser.parse(url)
    jobs = []
    for e in feed.entries:
        title = getattr(e, "title", "") or ""
        if is_article(title):
            continue
        jobs.append(
            {
                "title": title,
                "link": getattr(e, "link", "") or "",
                "summary": getattr(e, "summary", "")[:200] if getattr(e, "summary", None) else "",
                "published": getattr(e, "published", "") or "",
            }
        )
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument(
        "--search-location",
        default="",
        help="Authentic Jobs RSS search_location slug (e.g. india); default global feed",
    )
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    loc = (args.search_location or "").strip()
    jobs = fetch_jobs(search_location=loc)
    print(f"AuthenticJobs: {len(jobs)} jobs (articles excluded){f'; search_location={loc!r}' if loc else ''}")
    if args.keywords:
        jobs = [
            j
            for j in jobs
            if any(kw.lower() in (j["title"] + j["summary"]).lower() for kw in args.keywords)
        ]
    if args.limit:
        jobs = jobs[: args.limit]
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
