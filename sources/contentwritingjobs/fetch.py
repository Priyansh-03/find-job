#!/usr/bin/env python3
"""Fetch job digests from Content Writing Jobs RSS. https://contentwritingjobs.com/feed
Each entry is a daily digest (e.g. '15 Content Writing Jobs') linking to multiple roles."""
import argparse
import csv
import re
import feedparser

RSS_URL = "https://contentwritingjobs.com/feed"


def fetch_jobs() -> list[dict]:
    feed = feedparser.parse(RSS_URL, request_headers={"User-Agent": "Mozilla/5.0"})
    jobs = []
    for e in feed.entries:
        title = e.get("title", "")
        link = e.get("link", "")
        # Extract job count from title like "15 Content Writing Jobs (Mar 19, 2026)"
        summary = e.get("summary", "") or e.get("content", [{}])[0].get("value", "") if e.get("content") else ""
        content = getattr(e, "content", [{}])
        html = content[0].get("value", "") if content else summary
        h2_titles = re.findall(r"<h2>([^<]+)</h2>", html)
        apply_links = re.findall(r'href="(https?://[^"]+)"[^>]*>Apply Now', html)
        for i, url in enumerate(apply_links[:25]):
            job_title = h2_titles[i] if i < len(h2_titles) else title
            job_title = re.sub(r"^\d+\.\s*", "", job_title).strip()[:200]
            jobs.append({"title": job_title, "link": url, "company": "", "category": "", "job_type": "", "published": e.get("published", "")})
        if not apply_links:
            jobs.append({"title": title, "link": link, "company": "", "category": "", "job_type": "", "published": e.get("published", "")})
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    jobs = fetch_jobs()
    print(f"Content Writing Jobs: {len(jobs)} jobs")
    if args.keywords:
        jobs = [j for j in jobs if any(kw.lower() in j["title"].lower() for kw in args.keywords)]
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
