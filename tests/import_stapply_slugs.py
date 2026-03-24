#!/usr/bin/env python3
"""
Fetch stapply-ai/ats-scrapers CSVs and write slug seed files for discover_boards.py.

Default sources (override with --greenhouse-csv / --ashby-csv):
  https://raw.githubusercontent.com/stapply-ai/ats-scrapers/main/greenhouse/greenhouse_companies.csv
  https://raw.githubusercontent.com/stapply-ai/ats-scrapers/main/ashby/companies.csv

Outputs (under project data/):
  greenhouse_slugs_seed.txt
  ashby_slugs_seed.txt

Run periodically or once before discover_boards.py. Large Greenhouse lists make discovery slow — trim seeds if needed.
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path
from urllib.parse import unquote
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"

DEFAULT_GH_CSV = (
    "https://raw.githubusercontent.com/stapply-ai/ats-scrapers/main/greenhouse/greenhouse_companies.csv"
)
DEFAULT_ASHBY_CSV = "https://raw.githubusercontent.com/stapply-ai/ats-scrapers/main/ashby/companies.csv"

GH_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:job-boards|boards)\.greenhouse\.io/([^/?#]+)", re.I
)
ASHBY_URL_RE = re.compile(r"(?:https?://)?(?:www\.)?jobs\.ashbyhq\.com/([^/?#]+)", re.I)


def fetch_text(url: str, timeout: int = 60) -> str:
    req = Request(url, headers={"User-Agent": "import_stapply_slugs/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def slugs_from_csv(text: str, pattern: re.Pattern[str]) -> set[str]:
    found: set[str] = set()
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return found
    for row in reader:
        blob = " ".join(str(v or "") for v in row.values())
        for m in pattern.finditer(blob):
            slug = unquote(m.group(1).strip().rstrip("/"))
            if slug:
                found.add(slug.lower())
    return found


def write_lines(path: Path, slugs: set[str], merge: bool) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: set[str] = set()
    if merge and path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip().lower()
            if s and not s.startswith("#"):
                existing.add(s)
    all_slugs = sorted(existing | slugs) if merge else sorted(slugs)
    path.write_text("\n".join(all_slugs) + ("\n" if all_slugs else ""), encoding="utf-8")
    return len(all_slugs)


def main() -> int:
    ap = argparse.ArgumentParser(description="Import Greenhouse/Ashby slugs from stapply CSVs into data/")
    ap.add_argument("--greenhouse-csv", default=DEFAULT_GH_CSV, help="URL or path to greenhouse CSV")
    ap.add_argument("--ashby-csv", default=DEFAULT_ASHBY_CSV, help="URL or path to Ashby CSV")
    ap.add_argument(
        "--merge",
        action="store_true",
        help="Merge with existing seed files instead of replacing",
    )
    ap.add_argument("--gh-out", type=Path, default=DATA_DIR / "greenhouse_slugs_seed.txt")
    ap.add_argument("--ashby-out", type=Path, default=DATA_DIR / "ashby_slugs_seed.txt")
    ap.add_argument("--skip-greenhouse", action="store_true")
    ap.add_argument("--skip-ashby", action="store_true")
    args = ap.parse_args()

    def load_csv(src: str) -> str:
        if src.startswith("http://") or src.startswith("https://"):
            return fetch_text(src)
        return Path(src).read_text(encoding="utf-8")

    try:
        if not args.skip_greenhouse:
            text = load_csv(args.greenhouse_csv)
            gh = slugs_from_csv(text, GH_URL_RE)
            n = write_lines(args.gh_out, gh, merge=args.merge)
            print(f"Greenhouse: {len(gh)} slugs from CSV → {args.gh_out} ({n} total lines)")
        if not args.skip_ashby:
            text = load_csv(args.ashby_csv)
            ash = slugs_from_csv(text, ASHBY_URL_RE)
            n = write_lines(args.ashby_out, ash, merge=args.merge)
            print(f"Ashby: {len(ash)} slugs from CSV → {args.ashby_out} ({n} total lines)")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
