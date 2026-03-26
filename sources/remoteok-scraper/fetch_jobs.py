#!/usr/bin/env python3
"""
Remote OK Job Fetcher

Fetches jobs from https://remoteok.com/api with customizable filters.
Based on kelynst/job_scraper and Remote OK API structure.
Project default: India + Indian cities only (aligned with remote-jobs-in-india).
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlencode

import requests

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from location_filter import location_substrings_for_hint

_DEFAULT_INDIA_LOCATION_TOKENS = location_substrings_for_hint("india")

API_URL = "https://remoteok.com/api"
# Remote OK returns HTML / redirect loops for identifiable bot UAs, especially with ?location=…
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetch_all_jobs(*, api_params: dict[str, str] | None = None) -> list[dict]:
    """Fetch jobs from Remote OK public API (same feed as the site; optional query e.g. location=india)."""
    url = API_URL
    if api_params:
        q = urlencode(api_params)
        if q:
            url = f"{API_URL}?{q}"
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: Remote OK API returned {r.status_code}")
        if r.status_code == 403:
            print("  (Likely blocked by Cloudflare or Render IP restriction)")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    text = (r.text or "").lstrip()
    if text and not text.startswith("["):
        print(f"ERROR: Remote OK API returned non-JSON (Length: {len(text)})")
        if "cloudflare" in text.lower():
            print("  (Blocked by Cloudflare challenge page)")
        sys.exit(1)
    data = r.json()

    # First element is API metadata; jobs follow
    if isinstance(data, list) and data and isinstance(data[0], dict) and "legal" in data[0]:
        jobs = data[1:]
    else:
        jobs = data if isinstance(data, list) else []

    return jobs


def filter_jobs(
    jobs: list[dict],
    keywords: list[str] | None = None,
    location_filter: list[str] | None = None,
    company_filter: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    full_time_only: bool = True,
    since_days: int = 0,
    since_hours: float = 0.0,
) -> list[dict]:
    """Filter jobs by keywords, location, and employment type."""
    if not jobs:
        return []

    def job_dt_utc(job: dict) -> datetime | None:
        """
        RemoteOK jobs include either:
        - `epoch` (unix seconds) or
        - `date` (ISO timestamp)
        """
        epoch = job.get("epoch")
        if epoch is not None:
            try:
                return datetime.fromtimestamp(float(epoch), tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                pass
        date_str = job.get("date") or ""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(str(date_str).replace("Z", "+00:00")).astimezone(timezone.utc)
        except (ValueError, TypeError):
            return None

    def get_text(job: dict) -> str:
        """Get searchable text from a job."""
        parts = [
            job.get("position", ""),
            job.get("company", ""),
            job.get("description", ""),
            job.get("location", ""),
        ]
        tags = job.get("tags") or []
        if isinstance(tags, list):
            parts.append(" ".join(str(t) for t in tags))
        else:
            parts.append(str(tags))
        return " ".join(parts).lower()

    def get_location(job: dict) -> str:
        loc = job.get("location") or ""
        return str(loc).lower()

    filtered = []
    for job in jobs:
        text = get_text(job)
        loc = get_location(job)

        # Keywords filter: position OR tags OR description
        if keywords:
            keyword_match = any(
                kw.lower() in text for kw in keywords
            )
            if not keyword_match:
                continue

        # Location filter: India, Gurugram
        if location_filter:
            loc_match = any(
                loc_kw.lower() in loc or loc_kw.lower() in text
                for loc_kw in location_filter
            )
            if not loc_match:
                continue

        # Company filter
        if company_filter:
            if company_filter.lower() not in (job.get("company", "") or "").lower():
                continue

        # Salary filter
        smin = job.get("salary_min")
        smax = job.get("salary_max")
        if salary_min is not None and (smin is None or smin < salary_min):
            continue
        if salary_max is not None and (smax is None or smax > salary_max):
            continue

        # Full-time filter: exclude part-time, contract only if explicitly stated
        if full_time_only:
            # Exclude if explicitly part-time or contract (when we want full-time)
            exclude_terms = ["part-time", "part time", "contractor only", "freelance only"]
            if any(exc in text for exc in exclude_terms):
                continue
            # Prefer jobs that mention full-time, but don't exclude remote/flexible
            # (many remote jobs don't specify, we include them)

        # Date filter
        # Always filter using the job's own `epoch`/`date` field (client-side),
        # not relying on any RemoteOK API query params.
        if since_hours and since_hours > 0:
            dt = job_dt_utc(job)
            if dt is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=float(since_hours))
                if dt < cutoff:
                    continue
        elif since_days:
            dt = job_dt_utc(job)
            if dt is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(days=int(since_days))
                if dt < cutoff:
                    continue

        filtered.append(job)

    return filtered


def normalize_job(job: dict) -> dict:
    """Extract key fields for output."""
    def get(key, default=""):
        val = job.get(key, default)
        return "" if val is None else str(val)

    tags = job.get("tags") or []
    tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)

    salary = ""
    if job.get("salary_min") or job.get("salary_max"):
        salary = f"{job.get('salary_min', 0)}-{job.get('salary_max', 0)}"

    loc = get("location")
    loc_l = loc.lower().replace(" ", "")
    if loc_l in ("remoteok", "remoteok.com"):
        loc = ""

    return {
        "id": get("id"),
        "position": get("position"),
        "company": get("company"),
        "location": loc,
        "salary": salary or get("salary"),
        "url": get("url") or get("apply_url"),
        "tags": tags_str,
        "date": get("date"),
    }


def main():
    ap = argparse.ArgumentParser(
        description="Fetch Remote OK jobs (defaults: India geography + ?location=india; use --global-remoteok-api for the full feed)."
    )
    ap.add_argument(
        "--keywords",
        nargs="+",
        default=["frontend", "front-end", "react", "vue", "javascript", "developer", "vibe", "coder"],
        help="Keywords to match in position/tags/description",
    )
    ap.add_argument(
        "--location",
        nargs="+",
        default=None,
        metavar="TOKEN",
        help="OR-match on job location + text (default: India + major Indian cities only)",
    )
    ap.add_argument(
        "--api-location",
        default="india",
        metavar="VALUE",
        help="API query location= (default: india). Ignored with --global-remoteok-api.",
    )
    ap.add_argument(
        "--global-remoteok-api",
        action="store_true",
        help="Use https://remoteok.com/api with no ?location= (broader feed; still filtered by --location tokens)",
    )
    ap.add_argument("--company", help="Filter by company name (partial match)")
    ap.add_argument("--salary-min", type=int, help="Min salary (e.g. 80000)")
    ap.add_argument("--salary-max", type=int, help="Max salary (e.g. 200000)")
    ap.add_argument("--no-full-time", action="store_true", help="Include part-time/contract")
    ap.add_argument("--since", type=int, default=30, help="Only jobs from last N days (0=all)")
    ap.add_argument(
        "--since-hours",
        type=float,
        default=0.0,
        help="Only jobs from last N hours (0=disabled). Overrides --since days when > 0.",
    )
    ap.add_argument("--limit", type=int, default=50, help="Max jobs to output (0=unlimited)")
    ap.add_argument("--out", default="jobs.csv", help="Output CSV file")
    ap.add_argument("--no-csv", action="store_true", help="Only print to console, no CSV")
    args = ap.parse_args()

    loc_tokens = args.location if args.location is not None else list(_DEFAULT_INDIA_LOCATION_TOKENS)

    print("Fetching jobs from Remote OK API...")
    if args.global_remoteok_api:
        api_params = None
    else:
        q = (args.api_location or "").strip()
        api_params = {"location": q} if q else None
    jobs = fetch_all_jobs(api_params=api_params)
    print(f"  Fetched {len(jobs)} total jobs")

    filtered = filter_jobs(
        jobs,
        keywords=args.keywords,
        location_filter=loc_tokens,
        company_filter=args.company,
        salary_min=args.salary_min,
        salary_max=args.salary_max,
        full_time_only=not args.no_full_time,
        since_days=args.since if args.since else 0,
        since_hours=args.since_hours if args.since_hours else 0.0,
    )
    print(f"  Filtered to {len(filtered)} matching jobs")

    # Apply limit
    if args.limit:
        filtered = filtered[: args.limit]

    # Print to console
    for i, job in enumerate(filtered, 1):
        norm = normalize_job(job)
        print(f"\n{i}. {norm['position']} @ {norm['company']}")
        print(f"   Location: {norm['location']}")
        print(f"   URL: {norm['url']}")

    # Save to CSV
    if not args.no_csv and filtered:
        fieldnames = ["id", "position", "company", "location", "salary", "url", "tags", "date"]
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for job in filtered:
                writer.writerow(normalize_job(job))
        print(f"\nSaved {len(filtered)} jobs to {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
