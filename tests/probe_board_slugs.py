#!/usr/bin/env python3
"""Probe Greenhouse / Lever / Ashby slugs; print JSON for SLUG_SOURCES_STATUS.md."""
from __future__ import annotations

import importlib.util
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 6
WORKERS = 20


def load_discover():
    spec = importlib.util.spec_from_file_location("disc", ROOT / "discover_boards.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_board_file(name: str) -> list[str]:
    p = ROOT / "job_boards" / name
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def probe_one(mod, kind: str, slug: str) -> tuple[str, bool]:
    try:
        if kind == "gh":
            ok = mod.probe_greenhouse(slug)
        elif kind == "lever":
            ok = mod.probe(mod.LEVER_API, slug)
        else:
            ok = mod.probe(mod.ASHBY_API, slug)
        return slug, ok
    except Exception:
        return slug, False


def probe_many(mod, kind: str, slugs: list[str]) -> tuple[list[str], list[str]]:
    ok_l, bad_l = [], []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(probe_one, mod, kind, s): s for s in slugs}
        for fut in as_completed(futs):
            slug, hit = fut.result()
            (ok_l if hit else bad_l).append(slug)
    return sorted(ok_l), sorted(bad_l)


def main() -> int:
    mod = load_discover()
    # Patch faster timeout on module probes
    mod.TIMEOUT = TIMEOUT

    gh_curated = sorted(set(mod.GH_SLUGS))
    lever_curated = sorted(set(mod.LEVER_SLUGS))
    ash_curated = sorted(set(mod.ASHBY_SLUGS))

    cfg_gh = load_board_file("greenhouse_boards.txt")
    cfg_lv = load_board_file("lever_boards.txt")
    cfg_ash = load_board_file("ashby_boards.txt")

    print("Probing config files...", file=sys.stderr)
    cgh_ok, cgh_bad = probe_many(mod, "gh", cfg_gh)
    clv_ok, clv_bad = probe_many(mod, "lever", cfg_lv)
    cash_ok, cash_bad = probe_many(mod, "ashby", cfg_ash)

    print("Probing discover_boards curated lists...", file=sys.stderr)
    gh_ok, gh_bad = probe_many(mod, "gh", gh_curated)
    lv_ok, lv_bad = probe_many(mod, "lever", lever_curated)
    ash_ok, ash_bad = probe_many(mod, "ashby", ash_curated)

    blob = {
        "curated_list_sizes": {
            "greenhouse": len(gh_curated),
            "lever": len(lever_curated),
            "ashby": len(ash_curated),
        },
        "curated": {
            "greenhouse": {"working": gh_ok, "not_working": gh_bad},
            "lever": {"working": lv_ok, "not_working": lv_bad},
            "ashby": {"working": ash_ok, "not_working": ash_bad},
        },
        "config_files": {
            "greenhouse_boards.txt": {"working": cgh_ok, "not_working": cgh_bad},
            "lever_boards.txt": {"working": clv_ok, "not_working": clv_bad},
            "ashby_boards.txt": {"working": cash_ok, "not_working": cash_bad},
        },
    }
    print(json.dumps(blob, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
