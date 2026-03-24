#!/usr/bin/env python3
"""Fetch jobs from Real Work From Anywhere RSS. Category feeds available."""
import argparse
import csv
import feedparser

RSS_BASE = "https://www.realworkfromanywhere.com"
# From realworkfromanywhere.com/rss-feeds
CATEGORY_FEEDS = {
    "all": "/rss.xml",
    "frontend": "/remote-frontend-jobs/rss.xml",
    "backend": "/remote-backend-jobs/rss.xml",
    "fullstack": "/remote-fullstack-jobs/rss.xml",
    "mobile": "/remote-mobile-jobs/rss.xml",
    "devops": "/remote-devops-jobs/rss.xml",
    "ai": "/remote-ai-jobs/rss.xml",
    "data": "/remote-data-jobs/rss.xml",
    "security": "/remote-security-jobs/rss.xml",
    "qa": "/remote-quality-assurance-jobs/rss.xml",
    "web3": "/remote-web3-jobs/rss.xml",
    "product-designer": "/remote-product-designer-jobs/rss.xml",
    "design": "/remote-design-jobs/rss.xml",
    "product-manager": "/remote-product-manager-jobs/rss.xml",
}
ARTICLE_PATTERNS = ("how to", "guide", "article", "top 10", "5 free", "tips", "blog:")


def is_article(title: str) -> bool:
    t = (title or "").lower()
    return any(p in t for p in ARTICLE_PATTERNS)


def fetch_jobs(category: str = "all") -> list[dict]:
    path = CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["all"])
    url = RSS_BASE + path
    feed = feedparser.parse(url)
    jobs = []
    for e in feed.entries:
        title = getattr(e, "title", "") or ""
        if is_article(title):
            continue
        jobs.append({
            "title": title,
            "link": getattr(e, "link", "") or "",
            "summary": (getattr(e, "summary", "") or "")[:200],
            "published": getattr(e, "published", "") or "",
        })
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", choices=list(CATEGORY_FEEDS), default="all", help="Feed category")
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    jobs = fetch_jobs(category=args.category)
    print(f"Real Work From Anywhere: {len(jobs)} jobs")
    if args.keywords:
        jobs = [j for j in jobs if any(kw.lower() in (j["title"] + j["summary"]).lower() for kw in args.keywords)]
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
