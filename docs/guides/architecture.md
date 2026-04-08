# Architecture

## Main flow

1. `dashboard_app.py` serves UI and API endpoints.
2. UI starts scrape via API and receives live SSE events.
3. `fetch_for_users.py` orchestrates source fetchers under `sources/`.
4. Per-user output is written as CSV to `output/`.
5. UI reloads rows from CSV when run completes.

## Core modules

- `dashboard_app.py` - Flask routes, SSE stream, CSV read/write helpers
- `fetch_for_users.py` - source orchestration, filters, dedupe, summary stats
- `source_keyword_policy.py` - per-source keyword shaping
- `location_filter.py` - India/default location matching helpers
- `sources/*` - source-specific fetch implementations

## Source strategy

- Prefer API/RSS sources first (stable, lower block risk)
- Run risky scraping sources later (for example LinkedIn via JobSpy)
- Apply location/title/keyword filtering before final merge and dedupe

