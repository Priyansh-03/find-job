# Quickstart

## 1) Create virtual environment

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

## 2) Prepare input file

```bash
cp input/user.example.csv input/user.csv
```

Edit `input/user.csv`:

- `Name`: output file suffix (`output/jobs_<Name>.csv`)
- `Roles` + `Skills`: search keywords
- `Location`: location hint (blank defaults to India-first behavior)

## 3) Run dashboard

```bash
./run.sh
```

Open `http://127.0.0.1:5050`.

## 4) Run from UI

1. Select user
2. Select `all job boards` and/or `risk ip`
3. Start scraping
4. Review live logs and output table

## Recency window (last 24h)

- Use `last hours` in the dashboard (default `24`).
- Recency works per source with automatic fallback:
  - requested hours -> `7 days` -> `all-time`
- Fallback triggers per source only when the tighter window has no rows.

