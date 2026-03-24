# Job sources & slug probe status

Live HTTP probe of Greenhouse / Lever / Ashby boards (HTTP 200 on public job-board endpoints), plus an inventory of **every** fetch path `fetch_for_users.py` can use.

**Last probe:** 2026-03-24 (regenerate with `.venv/bin/python tests/probe_board_slugs.py`).

**Caveats:** One-off timeouts or rate limits can flip a slug between working and not working. Boards migrate (e.g. Greenhouse → Ashby); treat “not working” as *failed this probe*, not *permanently dead*. Large seed files are **not** fully probed here.

---

## 1. Where jobs come from (working fetchers + identifiers)

These are the **code paths** that can produce rows when you run the repo fetchers (orchestrator order is similar; JobSpy is last).

| Source type | Folder / script | How identified |
|-------------|-----------------|----------------|
| RSS / API job boards | Under `sources/`: `weworkremotely`, `remoteok-scraper`, `jobspresso`, `workingnomads`, `himalayas`, `themuse`, `realworkfromanywhere`, `dayweek4`, `authenticjobs`, `larajobs`, `jobscollider`, `vuejobs`, `remotepython`, `contentwritingjobs`, `landingjobs` | Fixed site; no slugs |
| Regional / geo APIs | `sources/jobicy`, `sources/arbeitnow` | CLI geo / location |
| Greenhouse | `sources/greenhouse-lever/fetch.py` | One slug per line in `job_boards/greenhouse_boards.txt` (board token) |
| Lever | `sources/greenhouse-lever/fetch.py` | One slug per line in `job_boards/lever_boards.txt` |
| Ashby | `sources/ashby/fetch.py` | One slug per line in `job_boards/ashby_boards.txt` (posting API job board name; case-sensitive for some) |
| Custom single-company APIs | `sources/custom-ats/` (netflix, spotify, uber) | On by default; `--no-custom-ats` to skip |
| Workday | `sources/workday/fetch.py` | Entries in `job_boards/workday_boards.json` (`--board-index` 0…n−1) |
| Jobvite | `sources/jobvite/fetch.py` | Slugs in `job_boards/jobvite_boards.txt` |
| SmartRecruiters | `sources/smartrecruiters/fetch.py` | Slugs in `job_boards/smartrecruiters_boards.txt` |
| Aggregator scrape | `sources/jobspy/fetch.py` | `--site` (e.g. Indeed, LinkedIn) + search terms |

**Discover script:** `discover_boards.py` merges built-in slug lists with `data/greenhouse_slugs_seed.txt` / `data/ashby_slugs_seed.txt`, probes each slug, and **rewrites** `job_boards/greenhouse_boards.txt`, `job_boards/lever_boards.txt`, `job_boards/ashby_boards.txt` with only boards that return 200.

---

## 2. Configured board files (probed this run)

Slugs **actually listed** in your repo `*_boards.txt` / JSON.

### `greenhouse_boards.txt` — all **working** (43/43)

`agoda`, `airbnb`, `airship`, `airtable`, `amplitude`, `arcadiacareers`, `asana`, `assetliving`, `brex`, `calendly`, `canonical`, `circleci`, `cloudflare`, `coursera`, `databricks`, `datadog`, `discord`, `dropbox`, `duolingo`, `elastic`, `energysolutions`, `figma`, `fivetran`, `gitlab`, `gusto`, `justworks`, `kallesgroup`, `lattice`, `lyft`, `mercury`, `mixpanel`, `mongodb`, `ouihelp`, `papaya`, `pinterest`, `reddit`, `remote`, `roblox`, `spacex`, `stripe`, `twitch`, `udemy`, `vercel`

### `lever_boards.txt`

| Status | Slugs |
|--------|--------|
| **Working** | `lever`, `pigment`, `theathletic`, `vrchat` |
| **Not working (this probe)** | `nielsen` |

Note: the same probe run later saw `nielsen` return 200 when checked as part of the larger Lever curated list — treat as **flaky** or re-run the script once.

### `ashby_boards.txt` — all **working** (6/6)

`Ashby`, `linear`, `notion`, `ramp`, `retool`, `vercel`

### `workday_boards.json`

Current file: **1** board — `NVIDIA` (`subdomain` nvidia, `board-index` 0). Treat as working if your fetcher run succeeds (not probed by `probe_board_slugs.py`).

### `jobvite_boards.txt` / `smartrecruiters_boards.txt`

No active slugs (comment placeholders only).

---

## 3. Curated lists inside `discover_boards.py` (full probe)

These are the **built-in** slug sets in `discover_boards.py` (before merging the huge seed files). Counts: **176** Greenhouse, **81** Lever, **65** Ashby (after `set()` dedupe).

### Greenhouse — working (88)

`6sense`, `agoda`, `airbnb`, `airship`, `airtable`, `amplitude`, `arcadiacareers`, `asana`, `assetliving`, `bitmex`, `bombas`, `brex`, `calendly`, `calicolabs`, `canonical`, `cerebral`, `circleci`, `civisanalytics`, `cloudflare`, `cobaltio`, `coursera`, `dailyharvest`, `databricks`, `datadog`, `datagrail`, `dfinity`, `digit`, `discord`, `doitintl`, `dropbox`, `duolingo`, `elastic`, `energysolutions`, `everlane`, `figma`, `fivetran`, `fluxx`, `gitlab`, `gumgum`, `gusto`, `justworks`, `kallesgroup`, `lattice`, `legion`, `lightship`, `lumahealth`, `lyft`, `mercury`, `mixpanel`, `mongodb`, `monzo`, `morty`, `mythicalgames`, `nomnom`, `omadahealth`, `ouihelp`, `outsetmedical`, `papaya`, `pathstream`, `pilothq`, `pinterest`, `poshmark`, `productiv`, `propel`, `quip`, `reddit`, `remote`, `roblox`, `skylotechnologies`, `spacex`, `stripe`, `thefarmersdog`, `tia`, `tomorrowhealth`, `trove`, `tubitv`, `twilio`, `twistbioscience`, `twitch`, `udacity`, `udemy`, `vercel`, `xmotorsai`, `yext`, `yipitdata`, `zero`

### Greenhouse — not working this probe (88)

`acquire`, `adhocexternal`, `adquick`, `airbyte`, `anchorage`, `appannie`, `away`, `bind`, `box`, `braceai`, `callisto`, `cameraiq`, `canva`, `capsulecares`, `careof`, `circle`, `clickup`, `createme`, `culture-amp`, `dbt`, `deel`, `depop`, `dharma`, `diaco`, `drop`, `eden18`, `eero`, `eightsleep`, `entelo`, `epic`, `fernish`, `fetchpackage`, `fly`, `flyhomes`, `framer`, `github`, `greenbits`, `guildeducation`, `heal`, `heap`, `himshers`, `incrediblehealthinc`, `invision`, `jopwell`, `klara`, `libra`, `linear`, `liveramp`, `m1finance`, `mercato`, `misen`, `monday`, `near`, `niantic`, `notion`, `oasislabs`, `omaze`, `pathlight`, `patreon`, `plaid`, `posthog`, `postmates`, `quizlet`, `railway`, `ramp`, `rational`, `render`, `retool`, `rippling`, `room`, `roostify`, `segment`, `sentry`, `snap`, `snowflake`, `split`, `sprinklr`, `squire`, `statestitle`, `strava`, `therealreal`, `threads`, `uber`, `unity`, `urban`, `verikai`, `whipmediagroup`, `whiteops`, `within`, `zapier`

Many failures are **wrong host** (company moved off Greenhouse), **renamed board token**, or **guess slugs** — not necessarily that the company has no careers page.

### Lever — working this probe (9)

`atlassian`, `binance`, `freshworks`, `kraken`, `lever`, `nielsen`, `pigment`, `theathletic`, `vrchat`

### Lever — not working this probe (72)

`abstract`, `adobe`, `affirm`, `amazon`, `amd`, `apple`, `att`, `auth0`, `bankofamerica`, `block`, `blockfi`, `broadcom`, `charter`, `checkpoint`, `chime`, `citigroup`, `coda`, `coforma`, `coinbase`, `comcast`, `confluent`, `costco`, `craft`, `crowdstrike`, `cyberark`, `databricks`, `datadog`, `dynatrace`, `elastic`, `fanatics`, `figma`, `ford`, `fortinet`, `gm`, `goldmansachs`, `google`, `homedepot`, `hubspot`, `intel`, `jpmorgan`, `lowes`, `lucid`, `meta`, `microsoft`, `miro`, `morganstanley`, `netflix`, `newrelic`, `notion`, `nvidia`, `okta`, `paloaltonetworks`, `qualcomm`, `rivian`, `robinhood`, `salesforce`, `serviceNow`, `servicenow`, `shopify`, `slite`, `snowflake`, `sofi`, `splunk`, `square`, `target`, `tesla`, `tmobile`, `verizon`, `walmart`, `webflow`, `zendesk`, `zscaler`

Most of these are **not real Lever board tokens** (the list mixes obvious guesses). Only a handful are expected to be public Lever JSON boards.

### Ashby — working this probe (20)

`Ashby`, `airtable`, `cohere`, `deel`, `linear`, `mercury`, `notion`, `openai`, `oyster`, `plaid`, `posthog`, `ramp`, `reddit`, `relay`, `retool`, `runway`, `sentry`, `supabase`, `vercel`, `zapier`

### Ashby — not working this probe (45)

`airbnb`, `amplitude`, `anthropic`, `asana`, `box`, `brex`, `calendly`, `circleci`, `coda`, `coursera`, `culture-amp`, `cultureamp`, `datadog`, `discord`, `dropbox`, `duolingo`, `elastic`, `figma`, `fivetran`, `github`, `gitlab`, `globalization`, `gusto`, `huggingface`, `lattice`, `lyft`, `midjourney`, `mixpanel`, `monday`, `mongodb`, `n26`, `papaya`, `pinterest`, `remote`, `replicate`, `rippling`, `slack`, `slite`, `spotify`, `stability`, `stripe`, `twitch`, `uber`, `udemy`, `webflow`

Again: many are **guessed** public board names; companies often use non-obvious Ashby board IDs.

---

## 4. Seed files (not fully listed here)

| File | Role |
|------|------|
| `data/greenhouse_slugs_seed.txt` | Thousands of tokens (e.g. from stapply import); merged into discovery when you run `discover_boards.py` |
| `data/ashby_slugs_seed.txt` | Same for Ashby (lines lowercased in code — may break case-sensitive boards) |

**Not probed** in this document line-by-line. Run `discover_boards.py` periodically to refresh working `*_boards.txt` from seeds + built-in lists.

---

## 5. India-relevant sources

**Strong India signal (CLI / API / filter):**

| Source | Notes |
|--------|--------|
| `jobspy/fetch.py` | `--country india` for Indeed; India location strings for other sites |
| `remoteok-scraper` | `--location india` (and related tokens) |
| `himalayas` | `--location india` |
| `arbeitnow` | `--location india` |
| `dayweek4`, `workingnomads`, `themuse` | `--location india` post-filter |
| `jobicy` | `--geo apac` (Asia-Pacific; includes India) |
| `sources/greenhouse-lever/fetch.py` | `--india-only` — client-side match on Greenhouse `location.name` / Lever location fields (no server India filter; [API](https://developer.greenhouse.io/job-board.html)) |
| `fetch_for_users.py` | `--greenhouse-india-only` — applies the above to all Greenhouse + Lever boards in one run |

**Remote / global RSS or APIs (India only if job text says so):** `weworkremotely`, `jobspresso`, `realworkfromanywhere`, `authenticjobs`, `larajobs`, `jobscollider`, `vuejobs`, `remotepython`, `contentwritingjobs`, `landingjobs` — use keywords + optional `fetch_for_users.py` `--location-lat` / `--location-lng` / `--location-radius-miles` + `data/latitude_longitude.json` if you add India coordinates.

**Greenhouse & Lever (verified):** The public Job Board APIs return structured location text ([Greenhouse docs](https://developer.greenhouse.io/job-board.html)). There is **no server-side `country=India` parameter**; filtering **client-side** on `location.name` (Greenhouse) and `categories.location` / `allLocations` (Lever) **does work** — e.g. Stripe and Databricks boards return many `Bengaluru`, `Mumbai, India`, `Remote - India` style strings. This repo implements that as `sources/greenhouse-lever/fetch.py --india-only` and `fetch_for_users.py --greenhouse-india-only` (substring match on India + major Indian cities; not perfect for every wording).

**Ashby / Workday / Netflix / Spotify / Uber:** No India-specific parameter in our fetchers; use keywords, Netflix’s own location facet, or geo/title heuristics elsewhere in the orchestrator.

---

## 6. Regenerate

```bash
.venv/bin/python tests/probe_board_slugs.py > probe_board_slugs_latest.json
.venv/bin/python discover_boards.py   # refresh job_boards/* from probes + seeds
```

Raw JSON from the last structured probe is intended to be pasted or diffed from `probe_board_slugs_latest.json` if you save it after running the command above.
