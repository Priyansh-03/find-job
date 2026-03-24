#!/usr/bin/env python3
"""Smoke check: expected directories and path constants after repo layout refactor."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paths import (  # noqa: E402
    DOCS_DIR,
    GREENHOUSE_BOARDS,
    INPUT_DIR,
    JOB_BOARDS_DIR,
    LOG_DIR,
    OUTPUT_DIR,
    SOURCES_DIR,
    TESTS_DIR,
    USER_CSV,
)


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    assert DOCS_DIR.is_dir(), DOCS_DIR
    assert JOB_BOARDS_DIR.is_dir(), JOB_BOARDS_DIR
    assert SOURCES_DIR.is_dir(), SOURCES_DIR
    assert (SOURCES_DIR / "himalayas" / "fetch.py").is_file()
    assert OUTPUT_DIR.is_dir(), OUTPUT_DIR
    assert INPUT_DIR.is_dir(), INPUT_DIR
    assert LOG_DIR.is_dir(), LOG_DIR
    assert TESTS_DIR.is_dir(), TESTS_DIR
    assert USER_CSV.is_file(), f"Missing {USER_CSV}"
    assert GREENHOUSE_BOARDS.is_file(), f"Missing {GREENHOUSE_BOARDS}"
    print("layout OK:", USER_CSV.relative_to(ROOT), "sources/himalayas/fetch.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
