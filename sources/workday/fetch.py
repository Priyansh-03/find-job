#!/usr/bin/env python3
"""Fetch jobs from Workday CXS API using workday_boards.json entries."""
import argparse
import csv
import json
import sys
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
# sources/workday/fetch.py -> repo root is two levels up from this file
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "job_boards" / "workday_boards.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; job-fetch/1.0)", "Content-Type": "application/json"}


def cxs_url(sub: str, dc: str, path_seg: str) -> str:
    return f"https://{sub}.wd{dc}.myworkdayjobs.com/wday/cxs/{sub}/{path_seg}/jobs"


def job_link(sub: str, dc: str, path_seg: str, external_path: str) -> str:
    base = f"https://{sub}.wd{dc}.myworkdayjobs.com/en-US/{path_seg}"
    ep = external_path if external_path.startswith("/") else f"/{external_path}"
    return base.rstrip("/") + ep


def fetch_board(entry: dict, limit: int, offset: int = 0) -> list[dict]:
    sub = entry["subdomain"]
    dc = str(entry["datacenter_id"]).lstrip("wd")  # allow "wd5" or "5"
    if not dc.isdigit():
        dc = "".join(c for c in dc if c.isdigit()) or dc
    path_seg = entry["path_segment"]
    label = entry.get("company_label") or sub
    url = cxs_url(sub, dc, path_seg)
    body = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
    r = requests.post(url, headers=HEADERS, json=body, timeout=45)
    r.raise_for_status()
    data = r.json()
    out = []
    for p in data.get("jobPostings") or []:
        ep = p.get("externalPath") or ""
        out.append({
            "title": p.get("title") or "",
            "link": job_link(sub, dc, path_seg, ep) if ep else "",
            "company": label,
            "category": "",
            "job_type": "",
            "published": str(p.get("postedOn") or ""),
            "location": str(p.get("locationsText") or "").strip(),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Workday CXS job fetcher")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to workday_boards.json")
    ap.add_argument("--board-index", type=int, default=0, help="Index in JSON array (default first board)")
    ap.add_argument("--keywords", nargs="+")
    ap.add_argument("--limit", type=int, default=0, help="Max rows after keyword filter")
    ap.add_argument(
        "--page-size",
        type=int,
        default=20,
        help="Workday API page size (POST body limit)",
    )
    ap.add_argument("--out", default="jobs.csv")
    args = ap.parse_args()
    if not args.config.is_file():
        print(f"workday: config not found: {args.config}", file=sys.stderr)
        return 1
    raw = json.loads(args.config.read_text(encoding="utf-8"))
    boards = raw if isinstance(raw, list) else raw.get("boards", [])
    if not boards:
        print("workday: no boards in config", file=sys.stderr)
        return 1
    if args.board_index < 0 or args.board_index >= len(boards):
        print("workday: invalid --board-index", file=sys.stderr)
        return 1
    entry = boards[args.board_index]
    try:
        jobs = fetch_board(entry, limit=max(1, min(args.page_size, 50)))
    except (requests.RequestException, KeyError) as e:
        print(f"workday: {e}", file=sys.stderr)
        return 1
    if args.keywords:
        jobs = [
            j
            for j in jobs
            if any(kw.lower() in (j["title"] + j.get("company", "")).lower() for kw in args.keywords)
        ]
    if args.limit > 0:
        jobs = jobs[: args.limit]
    print(f"workday ({entry.get('company_label', entry.get('subdomain'))}): {len(jobs)} jobs")
    if jobs:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["title", "link", "company", "category", "job_type", "published", "location"],
            )
            w.writeheader()
            w.writerows(jobs)
        print(f"Saved to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
