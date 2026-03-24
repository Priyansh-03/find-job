# Remote OK Job Scraper

Fetches remote job listings from the [Remote OK API](https://remoteok.com/api) with filters for role, location, and employment type.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Scripts

| Script | Source | Description |
|--------|--------|-------------|
| `fetch_jobs.py` | Remote OK API | Main job fetcher with filters |
| `fetch_rss_jobs.py` | RSS feeds | WeWorkRemotely, Jobspresso, DynamiteJobs, etc. |

## Usage

**RSS feeds (12 job boards):**

```bash
python fetch_rss_jobs.py
python fetch_rss_jobs.py --keywords frontend developer --limit 20 --out rss_jobs.csv
python fetch_rss_jobs.py --sources WeWorkRemotely Jobspresso AuthenticJobs
```

**Frontend / Vibe coder jobs in India (Gurugram) – full time:**

```bash
python fetch_jobs.py \
  --keywords frontend "front-end" react vue javascript developer vibe coder \
  --location india gurugram gurgaon remote worldwide \
  --since 60 \
  --limit 30 \
  --out frontend_india_jobs.csv
```

**All options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--keywords` | Keywords for position/tags/description | frontend, developer, etc. |
| `--location` | Location keywords | india, gurugram, remote, worldwide |
| `--no-full-time` | Include part-time/contract | (off) |
| `--since N` | Jobs from last N days (0 = all) | 30 |
| `--limit N` | Max jobs to output | 50 |
| `--out FILE` | Output CSV file | jobs.csv |
| `--no-csv` | Only print to console | (off) |

## References

- [Remote OK API](https://remoteok.com/api)
- [Filtered search example](https://remoteok.com/remote-engineer+python-jobs?benefits=unlimited_vacation&location=region_LA&min_salary=120000)
- [DebanilBora/Remote-Python-Job-Scrapper](https://github.com/DebanilBora/Remote-Python-Job-Scrapper) (HTML scraping)
- [kelynst/job_scraper](https://github.com/kelynst/job_scraper) (API-based)

## API Terms

Per Remote OK API terms: link back to Remote OK and mention it as the source. Do not use the Remote OK logo without permission.
