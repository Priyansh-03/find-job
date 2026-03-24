"""Project directory layout (single place for paths used by fetchers and tools)."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DOCS_DIR = PROJECT_ROOT / "docs"
JOB_BOARDS_DIR = PROJECT_ROOT / "job_boards"
SOURCES_DIR = PROJECT_ROOT / "sources"
OUTPUT_DIR = PROJECT_ROOT / "output"
INPUT_DIR = PROJECT_ROOT / "input"
TESTS_DIR = PROJECT_ROOT / "tests"
LOG_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"

# Rolling average seconds per orchestrator source name (updated after each run)
SOURCE_TIMING_EMA_JSON = LOG_DIR / "source_timing_ema.json"

FETCHER_SCRATCH_CSV = OUTPUT_DIR / "_scratch.csv"

GREENHOUSE_BOARDS = JOB_BOARDS_DIR / "greenhouse_boards.txt"
LEVER_BOARDS = JOB_BOARDS_DIR / "lever_boards.txt"
ASHBY_BOARDS = JOB_BOARDS_DIR / "ashby_boards.txt"
JOBVITE_BOARDS = JOB_BOARDS_DIR / "jobvite_boards.txt"
SMARTRECRUITERS_BOARDS = JOB_BOARDS_DIR / "smartrecruiters_boards.txt"
WORKDAY_BOARDS_JSON = JOB_BOARDS_DIR / "workday_boards.json"
RSS_FEED_BOARDS_JSON = JOB_BOARDS_DIR / "rss_feed_boards.json"
SITEMAP_BOARDS_JSON = JOB_BOARDS_DIR / "sitemap_boards.json"

USER_CSV = INPUT_DIR / "user.csv"
