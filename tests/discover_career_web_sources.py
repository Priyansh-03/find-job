#!/usr/bin/env python3
"""
Phase-1 discovery: probe seed hosts for job-related sitemaps and RSS/Atom feeds.
Writes job_boards/sitemap_boards.json and job_boards/rss_feed_boards.json (inventories — narrow in Phase 2).

Usage:
  python tests/discover_career_web_sources.py --seed-file data/careers_domains_seed.txt
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"

UA = {"User-Agent": "Mozilla/5.0 (compatible; career-discovery/1.0)"}

SITEMAP_HINTS = ("/job", "/jobs", "/careers", "/position", "/vacancy", "/opening", "/opportunit")
EXTRA_SITEMAP_PATHS = (
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/wp-sitemap.xml",
    "/sitemap_jobs.xml",
    "/sitemaps/sitemap.xml",
)
RSS_PATHS = (
    "/feed",
    "/feed.xml",
    "/rss.xml",
    "/atom.xml",
    "/jobs.xml",
    "/careers/feed",
    "/blog/feed",
    "/vacancies.xml",
)


def _load_hosts(path: Path) -> list[str]:
    hosts: list[str] = []
    if not path.is_file():
        return hosts
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        s = re.sub(r"^https?://", "", s, flags=re.I)
        s = s.split("/")[0].lower()
        if s:
            hosts.append(s)
    return sorted(set(hosts))


def _get(url: str, timeout: int = 15) -> tuple[int, str]:
    try:
        r = requests.get(url, headers=UA, timeout=timeout)
        return r.status_code, r.text or ""
    except requests.RequestException:
        return 0, ""


def _sitemaps_from_robots(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("sitemap:"):
            out.append(line.split(":", 1)[1].strip())
    return out


def _xml_ns(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_sitemap_locs(xml_text: str, max_locs: int = 500) -> list[str]:
    locs: list[str] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return locs
    tag = _xml_ns(root.tag)
    if tag == "sitemapindex":
        for el in root.iter():
            if _xml_ns(el.tag) == "loc" and el.text:
                locs.append(el.text.strip())
                if len(locs) >= max_locs:
                    break
    elif tag == "urlset":
        for el in root.iter():
            if _xml_ns(el.tag) == "loc" and el.text:
                locs.append(el.text.strip())
                if len(locs) >= max_locs:
                    break
    return locs


def _job_like_url(url: str) -> bool:
    u = url.lower()
    return any(h in u for h in SITEMAP_HINTS)


def probe_sitemaps(host: str, max_child_sitemaps: int = 20) -> dict:
    base = f"https://{host}"
    result: dict = {"host": host, "sitemaps": [], "sample_job_like_urls": [], "job_like_count_estimate": 0}
    seen_sm: set[str] = set()

    code, robots_txt = _get(f"{base}/robots.txt")
    if code == 200:
        for sm in _sitemaps_from_robots(robots_txt):
            if sm not in seen_sm:
                seen_sm.add(sm)
                result["sitemaps"].append({"url": sm, "source": "robots.txt"})

    for path in EXTRA_SITEMAP_PATHS:
        url = base + path
        code, body = _get(url)
        if code != 200 or not body:
            continue
        head = body.strip()[:800].lower()
        if "urlset" in head or "sitemapindex" in head or head.startswith("<?xml"):
            if url not in seen_sm:
                seen_sm.add(url)
                result["sitemaps"].append({"url": url, "source": "probe"})

    job_like: list[str] = []

    def collect_from_xml(xml_body: str) -> None:
        try:
            root = ET.fromstring(xml_body)
        except ET.ParseError:
            return
        tag = _xml_ns(root.tag)
        if tag == "sitemapindex":
            n = 0
            for el in root.iter():
                if _xml_ns(el.tag) != "loc" or not el.text:
                    continue
                if n >= max_child_sitemaps:
                    break
                n += 1
                ccode, cbody = _get(el.text.strip())
                if ccode != 200 or not cbody:
                    continue
                for loc in _parse_sitemap_locs(cbody):
                    if _job_like_url(loc):
                        job_like.append(loc)
        else:
            for loc in _parse_sitemap_locs(xml_body):
                if _job_like_url(loc):
                    job_like.append(loc)

    for sm_entry in list(result["sitemaps"]):
        sm_url = sm_entry["url"]
        code, body = _get(sm_url)
        if code != 200 or not body:
            continue
        collect_from_xml(body)

    result["sample_job_like_urls"] = job_like[:30]
    result["job_like_count_estimate"] = len(job_like)
    result["confidence"] = "high" if job_like else ("low" if result["sitemaps"] else "none")
    return result


def _looks_like_feed(body: str) -> bool:
    b = body.strip()[:2000].lower()
    return "<rss" in b or "<feed" in b and "xmlns" in b or "application/rss" in b


def probe_rss(host: str) -> dict:
    base = f"https://{host}"
    result: dict = {"host": host, "feeds": []}
    for path in RSS_PATHS:
        url = base + path
        code, body = _get(url)
        if code != 200 or not body:
            continue
        if not _looks_like_feed(body):
            continue
        fmt = "rss" if "<rss" in body[:500].lower() else "atom"
        result["feeds"].append({"url": url, "format_guess": fmt, "bytes": len(body)})
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Discover career sitemaps and RSS feeds for seed hosts")
    ap.add_argument("--seed-file", type=Path, default=DATA_DIR / "careers_domains_seed.txt")
    jb = PROJECT_DIR / "job_boards"
    ap.add_argument("--out-sitemap", type=Path, default=jb / "sitemap_boards.json")
    ap.add_argument("--out-rss", type=Path, default=jb / "rss_feed_boards.json")
    ap.add_argument("--delay", type=float, default=0.4, help="Seconds between hosts")
    ap.add_argument("--max-hosts", type=int, default=0, help="0 = no limit")
    args = ap.parse_args()

    hosts = _load_hosts(args.seed_file)
    if not hosts:
        print(f"No hosts in {args.seed_file} — add one hostname per line.", file=sys.stderr)
        return 1
    if args.max_hosts:
        hosts = hosts[: args.max_hosts]

    sitemap_rows = []
    rss_rows = []
    for i, host in enumerate(hosts, 1):
        print(f"[{i}/{len(hosts)}] {host} …", flush=True)
        sitemap_rows.append(probe_sitemaps(host))
        rss_rows.append(probe_rss(host))
        if args.delay > 0:
            time.sleep(args.delay)

    args.out_sitemap.parent.mkdir(parents=True, exist_ok=True)
    args.out_sitemap.write_text(json.dumps(sitemap_rows, indent=2), encoding="utf-8")
    args.out_rss.write_text(json.dumps(rss_rows, indent=2), encoding="utf-8")
    print(f"Wrote {args.out_sitemap} ({len(sitemap_rows)} hosts)")
    print(f"Wrote {args.out_rss} ({len(rss_rows)} hosts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
