# Fetcher Options & Filters

See `docs/README.md` for the full documentation map.

All working fetchers, their CLI options, and safe usage. **JobSpy** `linkedin` is **supported** but **tier C** (IP block / rate limit): run **last** via `fetch_for_users.py`; prefer `indeed` for routine runs. **Naukri** is not wired in this project (API often blocks with reCAPTCHA).

## Quick reference

| Use case | Fetcher | Command |
|----------|---------|---------|
| India jobs | jobicy | `--geo apac` |
| India jobs | arbeitnow, dayweek4 | `--location india` |
| India jobs | himalayas, workingnomads, themuse | `--location india` |
| India jobs | remoteok-scraper | default or `--location india` |
| Frontend only | realworkfromanywhere | `--category frontend` |
| Frontend only | weworkremotely | `--category frontend` |
| Search term | himalayas | `--query frontend` |
| Search term | jobicy | `--keywords "react"` |
| Company jobs | greenhouse-lever | `--source greenhouse --company stripe` |
| Company filter | remoteok, himalayas, arbeitnow, dayweek4, jobicy, themuse, workingnomads | `--company Stripe` |
| Salary min | remoteok, himalayas | `--salary-min 80000` |
| Job type | himalayas, arbeitnow, jobicy, workingnomads | `--job-type full_time` |
| Date (since) | remoteok, himalayas, arbeitnow, dayweek4, jobicy, themuse, workingnomads | `--since 7` |
| Category (API) | realworkfromanywhere, weworkremotely | `--category frontend` |
| Keywords filter | (most) | `--keywords react python` |
| JobSpy (safe) | jobspy | `--site indeed` (avoid linkedin for routine runs) |

---

## arbeitnow
**Source:** API `https://arbeitnow.com/api/job-board-api` (no auth)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--page` | int | 1 | Page number |
| `--per-page` | int | 50 | Jobs per page |
| `--location` | str | — | Post-filter: india, remote, worldwide |
| `--company` | str | — | Post-filter: company name (partial match) |
| `--job-type` | str | — | Post-filter: full-time, part-time, contract |
| `--since` | int | 0 | Only jobs from last N days |
| `--keywords` | str+ | — | Post-filter: match in title/company/category |
| `--limit` | int | 0 | Max jobs to output (0=all) |
| `--out` | str | jobs.csv | Output CSV |

**India:** `--location india` (post-filter on `location`)

---

## authenticjobs
**Source:** RSS default `https://authenticjobs.com/feed/` or job-feed with `search_location` (e.g. [India-filtered feed](https://authenticjobs.com/?feed=job_feed&job_types=freelance%2Cfull-time%2Cinternship%2Cpart-time&search_location=india)) when `--search-location` is set (orchestrator passes it from the user’s location hint).

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--search-location` | str | — | RSS `search_location` slug (e.g. `india`); empty = default global feed |
| `--keywords` | str+ | — | Post-filter on title/summary |
| `--limit` | int | 0 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |

**Note:** A regional feed can legitimately return **zero** items if the board has no matching postings.

---

## contentwritingjobs
**Source:** RSS `https://contentwritingjobs.com/feed` (digest)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--keywords` | str+ | — | Post-filter on title |
| `--limit` | int | 0 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |

---

## dayweek4
**Source:** API `https://4dayweek.io/api` (no auth)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--keywords` | str+ | — | Post-filter on title/company/category |
| `--location` | str | — | Post-filter: india, worldwide |
| `--company` | str | — | Post-filter: company name (partial match) |
| `--since` | int | 0 | Only jobs from last N days |
| `--limit` | int | 0 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |

**India:** `--location india` (post-filter on location_country/continent)

---

## greenhouse-lever
**Source:** Greenhouse `boards-api.greenhouse.io` / Lever `api.lever.co` (no auth)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--source` | choice | **required** | `greenhouse` or `lever` |
| `--company` | str | **required** | Board token (e.g. figma, stripe, pigment) |
| `--keywords` | str+ | — | Post-filter on title/company/category |
| `--india-only` | flag | off | Keep rows whose API **location** string matches India (substring: `india`, `bengaluru`, `mumbai`, …). **Not** a Greenhouse server filter — see [Job Board API](https://developer.greenhouse.io/job-board.html) |
| `--limit` | int | 0 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |

**Example:** `--source greenhouse --company stripe`

**India:** `--india-only` (post-filter on `location.name` for Greenhouse; Lever uses `categories.location` + `allLocations`). CSV includes a `location` column when present.

---

## himalayas
**Source:** API `https://himalayas.app/jobs/api` (no auth)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--query`, `-q` | str | engineer | **API-level** search query |
| `--location` | str | — | Post-filter: india, worldwide |
| `--company` | str | — | Post-filter: company name (partial match) |
| `--job-type` | str | — | Post-filter: Full Time, Part Time, Contract |
| `--salary-min` | int | — | Post-filter: min salary |
| `--salary-max` | int | — | Post-filter: max salary |
| `--since` | int | 0 | Only jobs from last N days |
| `--size` | int | 100 | Max jobs fetched from API |
| `--limit` | int | 0 | Max jobs to output |
| `--keywords` | str+ | — | Post-filter on title/company/category |
| `--out` | str | jobs.csv | Output CSV |

**India:** `--location india` (post-filter on `locationRestrictions`)

---

## jobicy
**Source:** API `https://jobicy.com/api/v2/remote-jobs` (no auth)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--count` | int | 20 | Max jobs (1–100, **API-level**) |
| `--keywords` | str | — | **API-level** search |
| `--geo` | str | — | **API-level**: apac, emea, latam, usa, canada, uk (India→apac) |
| `--company` | str | — | Post-filter: company name (partial match) |
| `--job-type` | str | — | Post-filter: Full-Time, Part-Time, Contract |
| `--since` | int | 0 | Only jobs from last N days |
| `--limit` | int | 0 | Max jobs to output |
| `--out` | str | jobs.csv | Output CSV |

**India:** `--geo apac` (APAC = Asia incl. India)

---

## jobscollider
**Source:** RSS

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--keywords` | str+ | — | Post-filter |
| `--limit` | int | 0 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |

---

## jobspresso
**Source:** RSS `https://jobspresso.co/feed/?post_type=job_listing`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--keywords` | str+ | — | Post-filter |
| `--limit` | int | 0 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |

---

## jobspy
**Source:** JobSpy (Indeed, LinkedIn, Google, etc.)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--search` | str | software engineer | Search term |
| `--location` | str | remote | Location filter |
| `--site` | choice | indeed | indeed, linkedin, google |
| `--country` | str | usa | Country (usa, india, uk, canada) |
| `--results` | int | 10 | Max results (keep low) |
| `--hours` | int | 168 | Jobs within last N hours |
| `--no-remote` | flag | — | Don't filter by remote |
| `--keywords` | str+ | — | Post-filter |
| `--limit` | int | 0 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |

**Avoid:** `--site linkedin` for high-volume automated runs (blocking risk). Prefer `--site indeed`.

**India:** `--country india` (API-level for Indeed)

---

## landingjobs
**Source:** RSS `https://landing.jobs/feed`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--limit` | int | 0 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |

---

## larajobs
**Source:** RSS `https://larajobs.com/feed`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--keywords` | str+ | — | Post-filter |
| `--limit` | int | 0 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |

---

## realworkfromanywhere
**Source:** RSS (category feeds)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--category` | choice | all | all, frontend, backend, fullstack, mobile, devops, ai, data, security, qa, web3, product-designer, design, product-manager |
| `--keywords` | str+ | — | Post-filter |
| `--limit` | int | 0 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |

**API-level category:** Use `--category frontend` for `/remote-frontend-jobs/rss.xml`, etc.

---

## remoteok-scraper (fetch_jobs.py)
**Source:** API `https://remoteok.com/api` (no auth)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--keywords` | str+ | frontend, react, vue... | Match in position/tags/description |
| `--location` | str+ | india, gurugram, remote... | Location keywords |
| `--company` | str | — | Post-filter: company name (partial match) |
| `--salary-min` | int | — | Post-filter: min salary |
| `--salary-max` | int | — | Post-filter: max salary |
| `--no-full-time` | flag | — | Include part-time/contract |
| `--since` | int | 30 | Only jobs from last N days (0=all) |
| `--limit` | int | 50 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |
| `--no-csv` | flag | — | Console only |

**India:** Default includes india, gurugram, gurgaon, remote, worldwide, asia.

---

## remoteok-scraper (fetch_rss_jobs.py)
**Source:** Multiple RSS feeds (WWR, Jobspresso, AuthenticJobs, etc.)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--keywords` | str+ | — | Post-filter |
| `--limit` | int | 0 | Max jobs |
| `--sources` | str+ | all | Only these: WeWorkRemotely, Jobspresso, AuthenticJobs, Larajobs, RemotePython |
| `--out` | str | — | Output CSV (empty=no CSV) |

**Note:** `fetch_rss_jobs.py` FEEDS includes some 404/blocked feeds. Working: WeWorkRemotely, Jobspresso, AuthenticJobs, Larajobs, RemotePython. Use `--sources WeWorkRemotely Jobspresso AuthenticJobs Larajobs RemotePython` for reliable fetches.

---

## remotepython
**Source:** RSS `https://www.remotepython.com/latest/jobs/feed/` or `/jobs/rss/`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--keywords` | str+ | — | Post-filter |
| `--limit` | int | 0 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |

---


---

## themuse
**Source:** API `https://www.themuse.com/api/public/jobs` (no auth)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--pages` | int | 5 | Pages to fetch (20 jobs/page) |
| `--location` | str | — | Post-filter: india |
| `--company` | str | — | Post-filter: company name (partial match) |
| `--since` | int | 0 | Only jobs from last N days |
| `--keywords` | str+ | — | Post-filter |
| `--limit` | int | 0 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |

**India:** `--location india` (post-filter on locations string)

---

## vuejobs
**Source:** RSS `https://vuejobs.com/feed`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--keywords` | str+ | — | Post-filter |
| `--limit` | int | 0 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |

---

## weworkremotely
**Source:** RSS (category feeds)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--category` | choice | all | all, customer-support, product, fullstack, backend, frontend, programming, sales-marketing, management-finance, design, devops, other |
| `--keywords` | str+ | — | Post-filter |
| `--limit` | int | 0 | Max jobs |
| `--out` | str | jobs.csv | Output CSV |

**API-level category:** Different RSS per category (e.g. `frontend` → remote-front-end-programming-jobs.rss).

---

## workingnomads
**Source:** API (exposed_jobs or elasticsearch)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--api` | choice | elasticsearch | exposed_jobs (~29 recent) or elasticsearch (~5K) |
| `--location` | str | — | Post-filter: india |
| `--company` | str | — | Post-filter: company name (partial match) |
| `--job-type` | str | — | Post-filter: full-time, part-time, etc. |
| `--since` | int | 0 | Only jobs from last N days |
| `--limit` | int | 50 | Max jobs to output |
| `--size` | int | 100 | Max jobs from API (elasticsearch only) |
| `--keywords` | str+ | — | Post-filter |
| `--out` | str | jobs.csv | Output CSV |

**India:** `--location india` (post-filter on locations)

---

## Summary: India filter

| Folder | India filter | How |
|--------|--------------|-----|
| remoteok-scraper | ✅ | Default or `--location india` |
| jobspy | ✅ | `--country india` (avoid linkedin for routine runs) |
| jobicy | ✅ | `--geo` from hint (`apac` for India, `usa`, `uk`, `canada`, … — see Jobicy API) |
| arbeitnow | ✅ | `--location india` |
| himalayas | ✅ | `--location india` |
| dayweek4 | ✅ | `--location india` |
| workingnomads | ✅ | `--location india` |
| themuse | ✅ | `--location india` |
| weworkremotely | ❌ | No location in feed |
| jobspresso, jobscollider, larajobs, vuejobs, remotepython | ❌ | No location field |
| authenticjobs | ✅ | Optional RSS `search_location` (orchestrator); CSV has no location column |
| contentwritingjobs, landingjobs | ❌ | No location |
| realworkfromanywhere | ❌ | No location |
| greenhouse-lever | ✅ | `--india-only` (client-side on API location strings) |
| ashby | ✅ | API `location` (+ secondaries); orchestrator substring filter on `location`+`title` when hint set |
| spotify-ats, uber-ats, workday | ✅ | Structured location in API response → CSV `location` column |

---

## Summary: API-level filters (server-side)

| Fetcher | API-level options |
|---------|-------------------|
| jobicy | `--keywords`, `--geo` (apac, emea, usa...) |
| himalayas | `--query` (search) |
| jobspy | `--search`, `--location`, `--country`, `--site` |
| realworkfromanywhere | `--category` (frontend, backend, etc.) |
| weworkremotely | `--category` (frontend, backend, etc.) |
| greenhouse-lever | `--company`, `--source`, `--india-only` (client-side) |
| workingnomads | `--api` (exposed_jobs vs elasticsearch), `--size` |
| remoteok-scraper | `--keywords`, `--location`, `--since` (all post-filter but applied before limit) |

---

## Safe usage (no blocking risk)

- **arbeitnow, dayweek4, himalayas, jobicy** – Public APIs, no auth
- **remoteok-scraper** – Public API
- **themuse** – Public API
- **weworkremotely, jobspresso, authenticjobs, realworkfromanywhere** – RSS with requests UA
- **contentwritingjobs, landingjobs, larajobs, remotepython, vuejobs** – RSS
- **greenhouse-lever** – Public company APIs
- **workingnomads** – Exposed + ES API
- **jobspy** – Supported here: `indeed`, `linkedin`, `google`. **Tier C (run last / highest block risk):** `linkedin`. The orchestrator runs **one subprocess per site** in `--jobspy-sites` (default = all except `linkedin` unless `--jobspy-risk-sites`) **after** Greenhouse/Lever/Ashby and other sources.

---

## fetch_for_users.py (orchestrator)

**Layout:** User list in `input/user.csv`; board list files and `workday_boards.json` in `job_boards/`; **fetcher implementations** (Greenhouse-Lever, JobSpy, Workday, etc.) in **`sources/`**; per-user CSVs and scratch file in `output/`; **run logs** and timing EMA in **`logs/`** (see [`paths.py`](../paths.py)). Docs live under `docs/`.

**Keyword shaping:** Per-source rules and log lines (`[kw] source: …`) live in [`source_keyword_policy.py`](../source_keyword_policy.py) (e.g. Jobicy = one token, Himalayas = one phrase, JobSpy = one `--search` phrase + up to 3 post-filter terms, default cap 5 keywords).

**Sources (default):** Every line in `job_boards/greenhouse_boards.txt`, `lever_boards.txt`, `ashby_boards.txt`, all aggregators, Workday/Jobvite/SmartRecruiters/custom ATS (all **on** by default if files exist), and JobSpy sites (default **excludes** `linkedin` unless `--jobspy-risk-sites` or explicit `--jobspy-sites`). Child fetchers write to `output/_scratch.csv`; the orchestrator reads it after each run. Each full run writes **`logs/fetch_YYYYMMDD_HHMMSS.log`** (mirror of console) and updates **`logs/source_timing_ema.json`** for **duration estimates** on the next run; use **`--eta-interval N`** to print per-user ETA every N sources (`0` = off).

**Duplicate URLs:** After title/geo filters, rows with the same normalized URL are merged into **one** row; extra sources are combined in the `source` column (e.g. `remoteok+himalayas`). End-of-run logs include counts for sources, failures, and merges.

| Option | Description |
|--------|-------------|
| `--ignore-title` | Comma-separated words; jobs whose **title** contains any word (case-insensitive) are dropped after merge |
| `--location-lat`, `--location-lng`, `--location-radius-miles` | Optional Haversine filter using `data/latitude_longitude.json` (place names matched as substrings in title/link/company) |
| `--page-size` | Optional batch/page hint for Jobicy, Greenhouse/Lever (compat), Netflix, Uber, Workday |
| `--jobs-per-source` | Max jobs kept per board/source (default **1**); passed as child `--limit` |
| `--location-preference` | If set, overrides the per-user `Location` column for location-aware fetchers (Himalayas, JobSpy country, etc.). If unset and `Location` is blank, the hint defaults to **india** |
| `--no-location-fallback` | Disable the second pass with broader location/geo when the prefer pass returns no jobs |
| `--all-sources` | No-op with current defaults (everything already on); kept for scripts that passed it before |
| `--jobspy-sites` | Comma-separated list; default = all supported sites **except** `linkedin`; use `--jobspy-risk-sites` to add LinkedIn. One JobSpy subprocess per site, last in pipeline |
| `--jobspy-site` | Single site; if set, overrides `--jobspy-sites` to exactly one site |
| `--jobspy-results` | Max JobSpy scrape results per query (default 8; capped by `--jobs-per-source`) |
| `--ashby-compensation` | Adds `includeCompensation=true` to Ashby public API |
| `--custom-ats` / `--no-custom-ats` | Include or skip Netflix, Spotify, Uber (default: on) |
| `--greenhouse-india-only` | Passes `--india-only` to every Greenhouse and Lever run (India / Indian-city substring on API location fields) |
| `--netflix-location` | Netflix API `location=` (e.g. `Mumbai,India`) — careers URL parity |
| `--netflix-team` | Repeatable; Team facet (e.g. `Data & Insights`, `Engineering`) |
| `--netflix-work-type` | Repeatable; `onsite` or `remote` |
| `--netflix-sort-by` | `relevance`, `new`, or `old` (careers `sort_by`) |
| `--workday` / `--no-workday` | Include or skip `job_boards/workday_boards.json` (default: on) |
| `--jobvite` / `--no-jobvite` | Include or skip `job_boards/jobvite_boards.txt` (default: on) |
| `--smartrecruiters` / `--no-smartrecruiters` | Include or skip `job_boards/smartrecruiters_boards.txt` (default: on) |
| `--eta-interval N` | Print remaining-time estimate for the current user every N sources (default **10**; `0` disables) |

**Fetcher order:** Core APIs and boards → optional custom ATS / Workday / Jobvite / SR → **JobSpy last**.

---

## sources/workday/fetch.py

| Option | Default | Description |
|--------|---------|-------------|
| `--config` | `job_boards/workday_boards.json` | JSON array of `{subdomain, datacenter_id, path_segment, company_label}` |
| `--board-index` | 0 | Which entry in the array |
| `--page-size` | 20 | POST `limit` |
| `--keywords`, `--limit`, `--out` | — | Same pattern as other fetchers |

---

## custom-ats (Netflix / Spotify / Uber)

| Script | Notes |
|--------|------|
| `sources/custom-ats/netflix/fetch.py` | `--page-size` (default 10); careers-style `--query`, `--location`, repeatable `--team` / `--work-type`, `--sort-by` (`relevance`/`new`/`old`). If strict filters return no rows, relaxes in order (work type → teams → location → catalog) unless `--no-fallback`. Orchestrator passes `--query` from the user’s first keyword when `--custom-ats` is on |
| `sources/custom-ats/spotify/fetch.py` | Single API response |
| `sources/custom-ats/uber/fetch.py` | `--page-size` = POST `limit` (default 50) |

---

## jobvite & smartrecruiters

| Script | Required | Notes |
|--------|----------|------|
| `sources/jobvite/fetch.py` | `--slug` | HTML list at `jobs.jobvite.com/{slug}-careers/jobs` |
| `sources/smartrecruiters/fetch.py` | `--slug` | `careers.smartrecruiters.com/{slug}/` |

---

## Discovery & seeds

| Script | Purpose |
|--------|---------|
| `tests/import_stapply_slugs.py` | Download stapply CSVs → `data/greenhouse_slugs_seed.txt`, `data/ashby_slugs_seed.txt` |
| `tests/discover_career_web_sources.py` | Probe `data/careers_domains_seed.txt` → `job_boards/sitemap_boards.json`, `job_boards/rss_feed_boards.json` |
| `discover_boards.py` | Merges seed files into Greenhouse/Ashby slug lists before probing |

**Greenhouse fetch:** `sources/greenhouse-lever/fetch.py` tries `api.greenhouse.io` first, then `boards-api.greenhouse.io` on 404.

---

## Filters by field

| Fetcher | Location | Company | Salary | Job type | Date (since) | Job title |
|---------|----------|---------|--------|----------|--------------|-----------|
| remoteok-scraper | ✅ | ✅ | ✅ min/max | ✅ (full-time) | ✅ | ✅ (keywords) |
| himalayas | ✅ | ✅ | ✅ min/max | ✅ | ✅ | ✅ (query API) |
| jobicy | ✅ (geo) | ✅ | ❌ | ✅ | ✅ | ✅ (keywords API) |
| arbeitnow | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ (keywords) |
| dayweek4 | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ (keywords) |
| themuse | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ (keywords) |
| workingnomads | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ (keywords) |
| greenhouse-lever | ✅ (`--india-only`) | ✅ (board) | ❌ | ❌ | ❌ | ✅ (keywords) |
| jobspy | ✅ | ❌ | ❌ | ❌ | ✅ (hours) | ✅ (search) |
| RSS fetchers | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (keywords) |
