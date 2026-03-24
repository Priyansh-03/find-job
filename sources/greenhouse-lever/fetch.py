#!/usr/bin/env python3
"""Fetch jobs from Greenhouse and Lever via their public APIs.
Inspired by https://github.com/MarcusKyung/greenhouse.io-scraper
No Selenium - uses API only."""
import argparse
import csv
import requests

GH_BOARDS_API = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
GH_LEGACY_API = "https://api.greenhouse.io/v1/boards/{company}/jobs"
LEVER_API = "https://api.lever.co/v0/postings/{company}?mode=json"

# Client-side only: Greenhouse has no server-side India filter (see Job Board API).
# Keep in sync with location_filter.INDIA_HINT_SUBSTRINGS (posting text may omit "India").
_INDIA_SUBSTRINGS = (
    "india",
    "indian",
    "bengaluru",
    "bangalore",
    "mumbai",
    "delhi",
    "hyderabad",
    "pune",
    "chennai",
    "kolkata",
    "jaipur",
    "gurgaon",
    "gurugram",
    "noida",
    "ahmedabad",
    "bhubaneswar",
    "kochi",
    "cochin",
)


def _location_text_suggests_india(text: str) -> bool:
    if not text or not text.strip():
        return False
    t = text.lower()
    return any(s in t for s in _INDIA_SUBSTRINGS)


def _greenhouse_location_name(raw: dict) -> str:
    loc = raw.get("location")
    if isinstance(loc, dict):
        return str(loc.get("name") or "")
    if isinstance(loc, str):
        return loc
    return ""


def _lever_location_blob(categories: dict) -> str:
    if not categories:
        return ""
    parts = []
    loc = categories.get("location")
    if loc:
        parts.append(str(loc))
    for x in categories.get("allLocations") or []:
        parts.append(str(x))
    return " ".join(parts)


def fetch_greenhouse(company: str, *, india_only: bool = False) -> list[dict]:
    """Fetch jobs from Greenhouse: try legacy API first, then boards-api on 404."""
    last_err = None
    for url in (GH_LEGACY_API.format(company=company), GH_BOARDS_API.format(company=company)):
        r = requests.get(url, timeout=30)
        if r.status_code == 404:
            last_err = r
            continue
        r.raise_for_status()
        data = r.json()
        break
    else:
        if last_err is not None:
            last_err.raise_for_status()
        raise requests.exceptions.HTTPError("404", response=last_err)
    jobs_raw = data.get("jobs", [])
    jobs = []
    for j in jobs_raw:
        loc_name = _greenhouse_location_name(j)
        if india_only and not _location_text_suggests_india(loc_name):
            continue
        jobs.append({
            "title": j.get("title", ""),
            "link": j.get("absolute_url", ""),
            "company": j.get("company_name", company),
            "category": "",
            "job_type": "",
            "published": j.get("first_published", ""),
            "location": loc_name,
        })
    return jobs


def fetch_lever(company: str, *, india_only: bool = False) -> list[dict]:
    """Fetch jobs from Lever API."""
    url = LEVER_API.format(company=company)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        return []
    jobs = []
    for j in data:
        cats = j.get("categories") or {}
        loc_blob = _lever_location_blob(cats)
        if india_only and not _location_text_suggests_india(loc_blob):
            continue
        jobs.append({
            "title": j.get("text", ""),
            "link": j.get("hostedUrl", "") or j.get("applyUrl", ""),
            "company": company,
            "category": cats.get("team", "") or cats.get("department", ""),
            "job_type": cats.get("commitment", ""),
            "published": j.get("createdAt", ""),
            "location": loc_blob.strip() or (cats.get("location") or ""),
        })
    return jobs


def main():
    ap = argparse.ArgumentParser(description="Greenhouse & Lever job fetcher (API, no Selenium)")
    ap.add_argument("--source", choices=["greenhouse", "lever"], required=True)
    ap.add_argument("--company", required=True,
        help="Board token (e.g. figma, stripe for Greenhouse; pigment, lever for Lever)")
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument(
        "--page-size",
        type=int,
        default=0,
        help="Reserved; Greenhouse/Lever return full listings in one response (no effect).",
    )
    ap.add_argument(
        "--india-only",
        action="store_true",
        help="Keep rows whose location string matches India (substring on API location fields; no server-side filter)",
    )
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()

    try:
        if args.source == "greenhouse":
            jobs = fetch_greenhouse(args.company, india_only=args.india_only)
        else:
            jobs = fetch_lever(args.company, india_only=args.india_only)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"{args.source}: Board '{args.company}' not found (404)")
        else:
            print(f"{args.source}: {e}")
        return 1
    except requests.exceptions.RequestException as e:
        print(f"{args.source}: {e}")
        return 1

    print(f"{args.source} ({args.company}): {len(jobs)} jobs")
    if args.keywords:
        jobs = [
            j
            for j in jobs
            if any(kw.lower() in (j["title"] + j.get("company", "") + j.get("category", "")).lower() for kw in args.keywords)
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
                extrasaction="ignore",
            )
            w.writeheader()
            w.writerows(jobs)
        print(f"\nSaved to {args.out}")
    return 0


if __name__ == "__main__":
    exit(main())
