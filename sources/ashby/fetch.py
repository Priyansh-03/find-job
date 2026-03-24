#!/usr/bin/env python3
"""Fetch jobs from Ashby via public posting API. https://developers.ashbyhq.com/docs/public-job-posting-api"""
import argparse
import csv
import requests

API = "https://api.ashbyhq.com/posting-api/job-board/{board}"


def _ashby_location_line(j: dict) -> str:
    parts: list[str] = []
    loc = j.get("location")
    if loc:
        parts.append(str(loc).strip())
    for sec in j.get("secondaryLocations") or []:
        if isinstance(sec, dict):
            n = sec.get("locationName") or sec.get("name") or ""
            if n:
                parts.append(str(n).strip())
        elif sec:
            parts.append(str(sec).strip())
    return ", ".join(dict.fromkeys(p for p in parts if p))


def fetch_ashby(board: str, include_compensation: bool = False) -> list[dict]:
    """Fetch jobs from Ashby job board."""
    url = API.format(board=board)
    if include_compensation:
        url += "?includeCompensation=true"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    jobs_raw = data.get("jobs", [])
    jobs = []
    for j in jobs_raw:
        jobs.append({
            "title": j.get("title", ""),
            "link": j.get("jobUrl", "") or j.get("applyUrl", ""),
            "company": board,
            "category": j.get("department", "") or j.get("team", ""),
            "job_type": j.get("employmentType", ""),
            "published": j.get("publishedAt", ""),
        })
    return jobs


def main():
    ap = argparse.ArgumentParser(description="Ashby job fetcher (public API)")
    ap.add_argument("--board", required=True, help="Job board name (e.g. Ashby, ramp, retool)")
    ap.add_argument(
        "--compensation",
        action="store_true",
        help="Request includeCompensation=true from the public API when supported",
    )
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()

    try:
        jobs = fetch_ashby(args.board, include_compensation=args.compensation)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"ashby: Board '{args.board}' not found (404)")
        else:
            print(f"ashby: {e}")
        return 1
    except requests.exceptions.RequestException as e:
        print(f"ashby: {e}")
        return 1

    print(f"ashby ({args.board}): {len(jobs)} jobs")
    if args.keywords:
        jobs = [
            j
            for j in jobs
            if any(
                kw.lower()
                in (
                    j["title"]
                    + j.get("company", "")
                    + j.get("category", "")
                    + j.get("location", "")
                ).lower()
                for kw in args.keywords
            )
        ]
    if args.limit > 0:
        jobs = jobs[: args.limit]
    for i, j in enumerate(jobs[:15], 1):
        print(f"  {i}. {j['title']} @ {j.get('company','')}\n     {j['link']}")
    if jobs:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["title", "link", "company", "category", "job_type", "published", "location"],
            )
            w.writeheader()
            w.writerows(jobs)
        print(f"\nSaved to {args.out}")
    return 0


if __name__ == "__main__":
    exit(main())
