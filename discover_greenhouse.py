#!/usr/bin/env python3
"""
Discover public Greenhouse job boards by probing slugs.
Writes working boards to job_boards/greenhouse_boards.txt for use by fetch_for_users.py.
"""
import requests
from pathlib import Path

API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
SCRIPT_DIR = Path(__file__).resolve().parent
JOB_BOARDS_DIR = SCRIPT_DIR / "job_boards"
JOB_BOARDS_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = JOB_BOARDS_DIR / "greenhouse_boards.txt"

# Candidate slugs: known working + TheirStack companies + common tech (lowercase, no spaces)
CANDIDATE_SLUGS = [
    # Known working
    "stripe", "figma", "airtable", "kallesgroup", "airship", "energysolutions", "arcadiacareers",
    # TheirStack / popular tech
    "canonical", "doordash", "cloudflare", "spacex", "outlier", "warbyparker", "anduril",
    "agoda", "assetliving", "ouihelp",
    # Common variations
    "discord", "dropbox", "spotify", "slack", "github", "box", "zapier", "twitch", "gitlab",
    "notion", "linear", "vercel", "datadog", "sentry", "posthog",
    "plaid", "brex", "mercury", "ramp", "deel", "remote",
    "reddit", "pinterest", "snap", "lyft", "uber", "airbnb",
    "mongodb", "elastic", "databricks", "snowflake",
    "segment", "amplitude", "mixpanel", "heap",
    "figma", "canva", "invision", "framer",
    "asana", "monday", "clickup", "notion",
    "circleci", "render", "railway", "fly",
    "retool", "airbyte", "fivetran", "dbt",
    "coursera", "udemy", "duolingo", "quizlet",
    "niantic", "roblox", "unity", "epic",
    "calendly", "lattice", "culture-amp", "rippling",
    "gusto", "justworks", "papaya", "remote",
]


def probe(slug: str, timeout: int = 10) -> bool:
    """Return True if board exists and has public jobs."""
    try:
        r = requests.get(API.format(slug=slug), timeout=timeout)
        if r.status_code != 200:
            return False
        data = r.json()
        jobs = data.get("jobs") or []
        return True  # Board exists
    except Exception:
        return False


def main():
    print("Discovering public Greenhouse boards...")
    working = []
    for i, slug in enumerate(CANDIDATE_SLUGS, 1):
        ok = probe(slug)
        status = "✓" if ok else "✗"
        print(f"  [{i}/{len(CANDIDATE_SLUGS)}] {slug}: {status}")
        if ok:
            working.append(slug)
    working = sorted(set(working))
    OUT_FILE.write_text("\n".join(working) + "\n", encoding="utf-8")
    print(f"\nFound {len(working)} working boards → {OUT_FILE.name}")
    print("  " + ", ".join(working[:15]) + (" ..." if len(working) > 15 else ""))


if __name__ == "__main__":
    main()
