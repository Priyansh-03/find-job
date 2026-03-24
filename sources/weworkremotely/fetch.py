#!/usr/bin/env python3
"""Fetch jobs from WeWorkRemotely RSS feed. Uses requests (feed blocks curl)."""
import argparse
import csv
import requests
import feedparser

RSS_BASE = "https://weworkremotely.com"
# Official feeds from weworkremotely.com/remote-job-rss-feed
CATEGORY_FEEDS = {
    "all": "/remote-jobs.rss",
    "customer-support": "/categories/remote-customer-support-jobs.rss",
    "product": "/categories/remote-product-jobs.rss",
    "fullstack": "/categories/remote-full-stack-programming-jobs.rss",
    "backend": "/categories/remote-back-end-programming-jobs.rss",
    "frontend": "/categories/remote-front-end-programming-jobs.rss",
    "programming": "/categories/remote-programming-jobs.rss",
    "sales-marketing": "/categories/remote-sales-and-marketing-jobs.rss",
    "management-finance": "/categories/remote-management-and-finance-jobs.rss",
    "design": "/categories/remote-design-jobs.rss",
    "devops": "/categories/remote-devops-sysadmin-jobs.rss",
    "other": "/categories/all-other-remote-jobs.rss",
}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/119.0"
ARTICLE_PATTERNS = ("how to", "guide", "article", "top 10", "5 free", "tips", "blog:")


def is_article(title: str) -> bool:
    t = title.lower()
    return any(p in t for p in ARTICLE_PATTERNS)


def fetch_jobs(category: str = "all") -> list[dict]:
    path = CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["all"])
    url = RSS_BASE + path
    # WWR blocks curl/simple clients; use requests with browser User-Agent
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    feed = feedparser.parse(r.content)
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
    ap.add_argument("--category", choices=list(CATEGORY_FEEDS), default="all", help="Feed category")
    ap.add_argument("--keywords", nargs="+", help="Filter by keywords")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    jobs = fetch_jobs(category=args.category)
    print(f"WeWorkRemotely: {len(jobs)} jobs")
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
