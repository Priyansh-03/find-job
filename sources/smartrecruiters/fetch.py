#!/usr/bin/env python3
"""Scrape SmartRecruiters careers listing HTML."""
import argparse
import csv
import re
import sys
from urllib.parse import urljoin

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; job-fetch/1.0)"}
# Opening cards link to smartrecruiters.com or careers host
LINK_RE = re.compile(
    r'href=["\']([^"\']*(?:smartrecruiters\.com|/job/)[^"\']+)["\']',
    re.I,
)


def fetch_smartrecruiters(slug: str) -> list[dict]:
    base = f"https://careers.smartrecruiters.com/{slug}/"
    r = requests.get(base, headers=HEADERS, timeout=45)
    r.raise_for_status()
    text = r.text
    seen: set[str] = set()
    jobs: list[dict] = []
    for m in LINK_RE.finditer(text):
        href = m.group(1).replace("&amp;", "&")
        if "/job/" not in href.lower() and "smartrecruiters.com" not in href.lower():
            continue
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = urljoin(base, href)
        if href in seen:
            continue
        seen.add(href)
        jobs.append({
            "title": "",
            "link": href,
            "company": slug,
            "category": "",
            "job_type": "",
            "published": "",
        })
    return jobs


def main() -> int:
    ap = argparse.ArgumentParser(description="SmartRecruiters careers HTML")
    ap.add_argument("--slug", required=True, help="careers.smartrecruiters.com/{slug}")
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    try:
        jobs = fetch_smartrecruiters(args.slug)
    except requests.RequestException as e:
        print(f"smartrecruiters: {e}", file=sys.stderr)
        return 1
    if args.keywords:
        jobs = [j for j in jobs if any(kw.lower() in j["link"].lower() for kw in args.keywords)]
    if args.limit > 0:
        jobs = jobs[: args.limit]
    print(f"smartrecruiters ({args.slug}): {len(jobs)} job links")
    if jobs:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["title", "link", "company", "category", "job_type", "published"])
            w.writeheader()
            w.writerows(jobs)
        print(f"Saved to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
