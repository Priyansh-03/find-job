# Job Scrape Dashboard

This repo scrapes job listings from multiple sources and lets you review results in a simple local web UI (Flask + SSE).

## What’s included

- `fetch_for_users.py`: Orchestrates fetching from many job sources based on `input/user.csv`
- `dashboard_app.py`: Flask dashboard (start scrape, live log, jobs table)
- `dashboard/templates/index.html`: UI (light mode), source chips, and table filters
- `sources/*`: Individual fetchers (API/RSS-based where possible)

## Local setup

### 1) Install dependencies

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

### 2) Prepare input CSV

Create `input/user.csv` from the template:

```bash
cp input/user.example.csv input/user.csv
```

Edit `input/user.csv`:

- `Name`: used for output filename (`output/jobs_<Name>.csv`)
- `Roles` + `Skills`: keywords used to search (e.g. `ai, nlp, rag`)
- `Location`: location hint (blank defaults to India behavior)

## Run locally (dashboard)

```bash
.venv/bin/python dashboard_app.py
```

Open:

- http://127.0.0.1:5050

## Run a scrape

1. Select a user from the dropdown
2. Choose one or both modes:
   - **all job boards**: multi-source scrape
   - **risk ip**: JobSpy only (LinkedIn when enabled)
3. Click **Start scraping**
4. Watch the table fill in live and check the live log panel

## Outputs

- Jobs are written to: `output/jobs_<Name>.csv`
- The dashboard reloads from that CSV when scraping finishes.

## Production (Gunicorn)

Gunicorn start command (Flask WSGI):

```bash
gunicorn dashboard_app:app -b 0.0.0.0:8000 -w 1
```

## Notes

- Some sources may provide an apply URL that redirects to an external ATS (the UI shows the discovery source and stores the final link).
- The dashboard includes an **India only** table filter (does not modify the CSV written on disk).

