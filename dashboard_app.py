#!/usr/bin/env python3
"""Local web dashboard: quick JobSpy (risk ip) and/or full multi-board scrape per user, with live SSE."""
from __future__ import annotations

import csv
import json
import math
import threading
import uuid
from http import HTTPStatus
from pathlib import Path
from queue import Empty, Queue
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

from fetch_for_users import (
    FetchOpts,
    build_configs,
    build_dashboard_configs,
    fetch_all_for_user,
    jobspy_sites_full_pipeline,
    parse_keywords,
    _load_timing_ema,
    _print_run_stats_block,
    _resolve_user_location_hint,
)
from location_filter import india_output_ui_filter_substrings
from paths import OUTPUT_DIR, PROJECT_ROOT, USER_CSV

app = Flask(__name__, template_folder=str(PROJECT_ROOT / "dashboard" / "templates"))


def _sanitize_for_json(obj: object) -> object:
    """Make values safe for JSON (browser ``JSON.parse`` rejects NaN/Infinity)."""
    if obj is None or isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        out: dict[str, object] = {}
        for k, v in obj.items():
            if k is None:
                continue
            out[str(k)] = _sanitize_for_json(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(v) for v in obj]
    return str(obj)


_scrape_lock = threading.Lock()
_sessions: dict[str, dict[str, Any]] = {}

# Columns the scraper reads from each user row (see fetch_for_users.main).
SCRAPER_INPUT_FIELDS = ["Name", "Roles", "Skills", "Location"]

# Default CSV header when input/user.csv is missing (no experience columns: not used by fetcher).
DEFAULT_USER_FIELDS = list(SCRAPER_INPUT_FIELDS)


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in name).replace(" ", "_").strip("_")


def _clamp_risk_per_site(n: object) -> int:
    try:
        v = int(n)
    except (TypeError, ValueError):
        return 3
    return max(1, min(v, 50))


def _dashboard_opts(*, risk_ip: bool, risk_per_site: int) -> FetchOpts:
    n = _clamp_risk_per_site(risk_per_site)
    return FetchOpts(
        ignore_title_words=[],
        user_lat=None,
        user_lng=None,
        radius_miles=None,
        page_size=0,
        jobspy_sites=["linkedin"] if risk_ip else ["indeed"],
        jobspy_results=n if risk_ip else 3,
        risk_jobspy_per_site=n,
        ashby_compensation=False,
        custom_ats=False,
        workday=False,
        jobvite=False,
        smartrecruiters=False,
        greenhouse_lever_india_only=False,
        jobs_per_source=n if risk_ip else 3,
        location_preference="",
        location_fallback=True,
        netflix_location="",
        netflix_sort_by="",
        netflix_teams=[],
        netflix_work_types=[],
    )


def _full_run_opts(*, include_linkedin: bool, risk_per_site: int) -> FetchOpts:
    """All boards + JobSpy. LinkedIn JobSpy only when ``include_linkedin`` (dashboard: risk ip checked)."""
    sites = jobspy_sites_full_pipeline(include_risky_jobspy=include_linkedin)
    n = _clamp_risk_per_site(risk_per_site)
    return FetchOpts(
        ignore_title_words=[],
        user_lat=None,
        user_lng=None,
        radius_miles=None,
        page_size=0,
        jobspy_sites=sites,
        jobspy_results=8,
        risk_jobspy_per_site=n,
        ashby_compensation=False,
        custom_ats=True,
        workday=True,
        jobvite=True,
        smartrecruiters=True,
        greenhouse_lever_india_only=False,
        jobs_per_source=1,
        location_preference="",
        location_fallback=True,
        netflix_location="",
        netflix_sort_by="",
        netflix_teams=[],
        netflix_work_types=[],
    )


def _read_users() -> tuple[list[str], list[dict[str, str]]]:
    if not USER_CSV.is_file():
        return list(DEFAULT_USER_FIELDS), []
    with open(USER_CSV, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        fieldnames = reader.fieldnames or list(DEFAULT_USER_FIELDS)
        rows = [dict(r) for r in reader]
    return list(fieldnames), rows


def _write_jobs_csv(user_name: str, rows: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe = _safe_filename(user_name) or "unnamed"
    path = OUTPUT_DIR / f"jobs_{safe}.csv"
    fieldnames = [
        "title",
        "link",
        "company",
        "location",
        "category",
        "job_type",
        "published",
        "source",
    ]
    for row in rows:
        for k in row:
            if k not in fieldnames:
                fieldnames.append(k)

    def q(v: object) -> str:
        s = str(v) if v is not None else ""
        if "," in s or '"' in s or "\n" in s:
            return '"' + s.replace('"', '""') + '"'
        return s

    with open(path, "w", encoding="utf-8") as f:
        f.write(", ".join(q(k) for k in fieldnames) + "\n")
        for row in rows:
            f.write(", ".join(q(row.get(k, "")) for k in fieldnames) + "\n")


def _read_jobs_csv(user_name: str) -> list[dict[str, str]]:
    safe = _safe_filename(user_name) or "unnamed"
    path = OUTPUT_DIR / f"jobs_{safe}.csv"
    if not path.is_file():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        raw = list(csv.DictReader(f, skipinitialspace=True))
    out: list[dict[str, str]] = []
    for row in raw:
        clean: dict[str, str] = {}
        for k, v in row.items():
            if k is None:
                continue
            key = str(k).strip()
            if not key:
                continue
            clean[key] = "" if v is None else str(v)
        if clean:
            out.append(clean)
    return out


@app.route("/")
def index():
    return render_template(
        "index.html",
        india_output_filter_tokens=india_output_ui_filter_substrings(),
    )


@app.get("/api/users")
def api_users():
    fieldnames, rows = _read_users()
    return jsonify(
        {
            "fieldnames": fieldnames,
            "form_fields": [c for c in SCRAPER_INPUT_FIELDS if c in fieldnames]
            or list(SCRAPER_INPUT_FIELDS),
            "users": rows,
        }
    )


@app.post("/api/users")
def api_users_add():
    payload = request.get_json(force=True, silent=True) or {}
    fieldnames, rows = _read_users()
    for col in SCRAPER_INPUT_FIELDS:
        if col not in fieldnames:
            fieldnames.append(col)
    row = {k: "" for k in fieldnames}
    for k in fieldnames:
        if k in SCRAPER_INPUT_FIELDS:
            row[k] = str(payload.get(k, "")).strip()
    if not row.get("Name", "").strip():
        return jsonify({"error": "Name is required"}), HTTPStatus.BAD_REQUEST
    rows.append(row)
    USER_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return jsonify({"ok": True, "users": rows})


@app.get("/api/jobs")
def api_jobs():
    name = (request.args.get("name") or "").strip()
    if not name:
        return jsonify({"rows": []})
    return jsonify({"rows": _read_jobs_csv(name)})


@app.post("/api/scrape")
def api_scrape_start():
    if not _scrape_lock.acquire(blocking=False):
        return jsonify({"error": "A scrape is already running."}), HTTPStatus.CONFLICT
    try:
        body = request.get_json(force=True, silent=True) or {}
        user_index = int(body.get("user_index", 0))
        risk_ip = bool(body.get("risk_ip"))
        all_job_boards = bool(body.get("all_job_boards"))
        risk_per_site = _clamp_risk_per_site(body.get("risk_jobspy_per_site", 3))
        if not risk_ip and not all_job_boards:
            _scrape_lock.release()
            return jsonify(
                {"error": "Select at least one: risk ip and/or all job boards."}
            ), HTTPStatus.BAD_REQUEST
        _, rows = _read_users()
        if user_index < 0 or user_index >= len(rows):
            _scrape_lock.release()
            return jsonify({"error": "Invalid user index."}), HTTPStatus.BAD_REQUEST
        user = rows[user_index]
        name = (user.get("Name") or "").strip() or "(unnamed)"
        token = str(uuid.uuid4())
        q: Queue = Queue()
        _sessions[token] = {"queue": q, "user": name}

        def run() -> None:
            if all_job_boards:
                # Omit JobSpy LinkedIn unless user explicitly opted into “risk ip”.
                opts = _full_run_opts(
                    include_linkedin=risk_ip,
                    risk_per_site=risk_per_site,
                )
                configs_ov: list[tuple[str, str]] | None = None
                eta = 10
            else:
                opts = _dashboard_opts(risk_ip=risk_ip, risk_per_site=risk_per_site)
                configs_ov = build_dashboard_configs(risk_ip=risk_ip)
                eta = 0

            roles = user.get("Roles", "") or ""
            skills = user.get("Skills", "") or ""
            csv_loc = user.get("Location", "") or ""
            kw_tuple = parse_keywords(roles, skills)
            loc_hint = _resolve_user_location_hint(opts.location_preference, csv_loc)
            timing = _load_timing_ema()
            prog_state: dict[str, Any] = {}

            def emit_line(msg: str = "") -> None:
                q.put({"event": "log", "line": msg})

            def on_progress(delta: list[dict], full: list[dict]) -> None:
                _write_jobs_csv(name, full)
                q.put({"event": "rows", "rows": delta, "full_count": len(full)})

            preview = build_configs(opts) if configs_ov is None else configs_ov
            try:
                q.put(
                    {
                        "event": "started",
                        "user": name,
                        "risk_ip": risk_ip,
                        "all_job_boards": all_job_boards,
                        "risk_jobspy_per_site": risk_per_site,
                        "source_count": len(preview),
                        "sources": [c[0] for c in preview[:40]],
                    }
                )
                emit_line(
                    "Hint: each [OK] line is jobs kept from that source only (capped per board). "
                    "The same apply URL on multiple boards becomes one output row after dedupe."
                )
                emit_line(
                    "Title/geo filters also run once at the end — see 'Run summary' below when finished."
                )
                _jobs, fails, stats = fetch_all_for_user(
                    kw_tuple,
                    opts,
                    loc_hint,
                    timing_ema=timing,
                    emit=emit_line,
                    eta_every=eta,
                    configs_override=configs_ov,
                    progress_emit=on_progress,
                    progress_state=prog_state,
                )
                _write_jobs_csv(name, _jobs)
                _print_run_stats_block("\n--- Run summary ---", stats, emit=emit_line)
                q.put(
                    {
                        "event": "done",
                        "user": name,
                        "stats": stats,
                        "failures": len(fails),
                    }
                )
            except Exception as e:
                q.put({"event": "error", "message": str(e)})
            finally:
                _scrape_lock.release()

        threading.Thread(target=run, daemon=True).start()
        return jsonify({"token": token})
    except Exception:
        _scrape_lock.release()
        raise


@app.get("/api/stream/<token>")
def api_stream(token: str):
    sess = _sessions.get(token)
    if not sess:
        return Response("Unknown or expired session", status=HTTPStatus.GONE)
    q: Queue = sess["queue"]

    def gen():
        while True:
            try:
                item = q.get(timeout=20)
            except Empty:
                yield ": keepalive\n\n"
                continue
            yield "data: " + json.dumps(_sanitize_for_json(item), ensure_ascii=False) + "\n\n"
            if item.get("event") in ("done", "error"):
                _sessions.pop(token, None)
                break

    return Response(
        gen(),
        mimetype="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def main() -> None:
    app.run(host="127.0.0.1", port=5050, debug=False, threaded=True)


if __name__ == "__main__":
    main()
