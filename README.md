# Job Scrape Dashboard

Multi-source job scraping dashboard with Flask + SSE, India-first filtering defaults, and per-user CSV outputs.

## Start here

- **Docs hub:** `docs/README.md`
- **Local run:** `./run.sh`
- **Production WSGI:** `app/wsgi.py`

## Repo layout

```text
.
├── app/                         # Production app entrypoints
├── dashboard/                   # UI templates
├── docs/                        # Project documentation
├── input/                       # Input CSV templates
├── job_boards/                  # Board slug/config files
├── sources/                     # Individual source fetchers
├── tests/                       # Probes, smoke scripts, test helpers
├── dashboard_app.py             # Flask dashboard app
├── fetch_for_users.py           # Main orchestration pipeline
├── requirements.txt
└── run.sh                       # Canonical local runner
```

## Quick commands

```bash
# local
./run.sh

# production
gunicorn app.wsgi:app -b 0.0.0.0:$PORT -w 1
```

## Recency behavior

- Dashboard `last hours` (default `24`) is applied per source.
- If a source returns no jobs in the requested window, fallback automatically expands for that source:
  - requested window -> `7d` -> `all-time`
- This keeps 24h preference while avoiding empty results from sources with sparse/old/undated postings.

