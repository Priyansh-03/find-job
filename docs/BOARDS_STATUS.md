# 140 Job Boards – Status

Explored APIs/RSS for boards from your list. Many require auth, return 403, or have no public endpoint.

---

## 📊 Totals

| Metric | Count |
|--------|-------|
| **Total working fetchers** | 19 |
| **With India filter** | 11 |
| **Working (can fetch jobs)** | 19 |
| **Not working (probed, no usable access)** | 144 |
| **Total explored** | **164** |

*Others* = Jobicy, Arbeitnow, Greenhouse/Lever, JobSpy platforms, etc.

## ✅ Have working fetcher

| # | Platform | Folder | Type |
|---|----------|--------|------|
| 2 | We Work Remotely | weworkremotely | RSS |
| 4 | RemoteOK | remoteok-scraper | API |
| 6 | Jobspresso | jobspresso | RSS |
| 7 | Working Nomads | workingnomads | API |
| 9 | Himalayas | himalayas | API |
| 67 | The Muse | themuse | API |
| 84 | Real Work From Anywhere | realworkfromanywhere | RSS |
| 85 | 4 Day Week | dayweek4 | API |
| 86 | Authentic Jobs | authenticjobs | RSS |
| 99 | Larajobs | larajobs | RSS |
| 105 | JobsCollider | jobscollider | RSS |
| 120 | Vue.js Jobs | vuejobs | RSS |
| 135 | Remote Python | remotepython | RSS |
| 15 | Content Writing Jobs | contentwritingjobs | RSS |
| — | Landing Jobs | landingjobs | RSS |

**Plus:** jobspy (Indeed, LinkedIn, Google — **not** Glassdoor, Naukri, or ZipRecruiter in this repo), greenhouse-lever (Greenhouse/Lever APIs), jobicy, arbeitnow

---

## 🇮🇳 India filter support

| Folder | India filter | How |
|--------|--------------|-----|
| remoteok-scraper | ✅ | `--location india` (post-filter, default includes india) |
| jobspy | ✅ | `--country india` (API-level for Indeed) |
| jobicy | ✅ | `--geo apac` (API-level, APAC = Asia incl. India) |
| arbeitnow | ✅ | `--location india` (post-filter) |
| himalayas | ✅ | `--location india` (post-filter on locationRestrictions) |
| dayweek4 | ✅ | `--location india` (post-filter) |
| workingnomads | ✅ | `--location india` (post-filter) |
| weworkremotely | ❌ | RSS, no location in entries |
| jobspresso | ❌ | RSS, no location |
| themuse | ✅ | `--location india` (post-filter) |
| jobscollider | ❌ | RSS, no location |
| larajobs, vuejobs, remotepython, authenticjobs | ❌ | RSS, no location field |

---

## ❌ Explored – no public API/RSS or blocked

| Platform | Result |
|----------|--------|
| FlexJobs | Paywalled |
| Remote.co | No RSS (404) |
| Pangian | No API found |
| AngelList/Wellfound | Needs cookies/Apify |
| Stack Overflow Jobs | 404 |
| Dribbble Jobs | 404 |
| JustRemote | No RSS |
| NoDesk | 404 |
| Otta | HTML SPA |
| Contra | 404 |
| Workew | Blog feed, not jobs |
| Dice | JobSpy has it |
| CareerBuilder | Needs API key |
| Glassdoor | Not wired (JobSpy path unreliable); omitted in this repo |
| GitHub Jobs | Deprecated |
| GitHub Careers | 404 |
| Upwork | No pip package |
| 80,000 Hours | API 404 "Invalid request" |
| Jooble | Needs approval |
| Welcome To The Jungle | 403 Algolia |
| Rejobs | — |
| PowerToFly | 404 |
| Virtual Vocations | 404 |
| Daily Remote | 404 |
| Diversify Tech | No API |
| Skip The Drive | No RSS |
| Built In | 404 |
| freelancermap | 404 |
| Guru | 404 |
| Hasjob | 404 |
| ClearanceJobs | 403 |
| Findjobit | 404 |
| Ruby On Remote | 403 |
| Remote Index | 403 |
| Drupal Jobs | 403 |
| tokenjobs.io | HTML |
| Niceboard | Login required |
| hiring.lat | 404 |

---

## 🔍 Explored (batch 2 – remaining ~65)

| Platform | Result |
|----------|--------|
| Superpath, Turing, Toptal, TotalJobs | 404 |
| Women Who Code, WeAreDistributed | 404 / timeout |
| MarketingHire, Creative Circle, Remote4Me | RSS 200 (MarketingHire/Creative: blog-style; Remote4Me: 0 entries) |
| foxhunch, askhunch, usemassive | ConnectionError / 404 / 400 |
| TechCareers, Hcareers, MedReps | 404 |
| ABA Career Center, Remote of Asia | ConnectionError |
| HigherEdJobs, InternMatch, Bot-Jobs, ClojureJobboard | 200 HTML (not RSS) |
| RemoteHabits, Remotees, Freelancer, Virtual Vocations | 404 |
| Remote Freelance | SSLError |
| Remote Rocketship | 403 |
| InstaHyre | 403 |
| GolangProjects, Drupal, Findjobit, PowerToFly | 404 |
| Diversify Tech | 404 |
| DevOpsJobs, Remote Works, zuhausejobs, whoishiring | Timeout |
| Remote Backend/Frontend Jobs | 200 HTML |
| Ruby On Remote | 403 Cloudflare |
| Slasify, Stream Native, Web3Jobs, Workana | 404 |
| Dataaxy, Career Vault, Vollna | 404 |
| SlashJobs | 502 |
| tokenjobs | 200 HTML |

---

## 🔍 Explored (batch 3 – remaining ~32)

| Platform | Result |
|----------|--------|
| **Content Writing Jobs** | ✅ **RSS working** – digest with Apply links, 157+ jobs |
| Working Not Working | 200 but 0 entries |
| jobbox.io | 200 but 0 entries |
| Work at a Startup | 404 |
| Outsourcely | Timeout |
| Hubstaff Talent | 404 |
| Crossover | 200 HTML (no RSS) |
| Randstad India | 200 (check ct) |
| ManpowerGroup India | 200 (check ct) |
| Startups Gallery | Timeout |
| JobBoardAI | — |
| Hidden Jobs | Timeout |
| Cryptocurrency Jobs | 404 |
| HackerX | — |
| HN Hiring | Algolia 200 (returns HN threads, not job objects) |
| JOBBOX.io | 200, 0 feed entries |
| Remote AI/Backend/Frontend/Game Jobs | 200 HTML |
| RemoteJobs.lat | 404 |
| UI/UX Jobs Board | 403 |
| EmbeddedJobs | 404 |
| UN Talent | 200 (returns HTML, not JSON) |
| remote.io | 200 HTML |
| GitHub Gitter, GitHub Discussions | (part of GitHub ecosystem) |
| ABC Consultants, Kelly, TeamLease | (India recruiters – need specific URLs) |

*Google Jobs* – covered by JobSpy (`--site google`). Naukri is not enabled in this repo’s orchestrator.

---

## 🔍 Explored (batch 4 – final ~20)

| Platform | Result |
|----------|--------|
| **Landing Jobs** | ✅ **RSS working** – 54+ jobs |
| Gun.io | 200 RSS (12 entries, blog-style content) |
| Remote100K, RemotelyOne, Jobbatical, Arc, Braintrust | 404 |
| Lemon.io, Remotesome, Flexiple, Codementor | 404 |
| Simplified, Remote Job Guru, Joblist, Ladder | 404 |
| Remote Team | 403 |
| Pallet | SSL error |
| Remote Jobs Club | SSL error |
| Who is Hiring, We Love Remote, Remote Circle | 200 HTML (non-RSS) |
| Hired, Turing | 200 HTML (non-RSS) |
| Remote.com, Remote Base, Remote Jobs | 404 |
| SimplyHired, Recruit.net | 404 |

*Jobicy RSS* – already covered by jobicy fetcher.

---

## 🔑 Need API key / auth

- CareerBuilder, Findwork, Guru, Jooble, Adzuna

---

## 📍 JobSpy covers

- LinkedIn, Google Jobs (via `jobspy --site`; Glassdoor, Naukri, ZipRecruiter omitted)

### IP-block risk tiers (orchestration)

| Tier | When to use | Sites (examples) |
|------|-------------|-------------------|
| **A** | First — stable public APIs | Greenhouse, Lever, Ashby, Jobicy, RSS/API boards |
| **B** | After A | JobSpy **Indeed**, Google; Netflix/Spotify/Uber/Workday-style APIs |
| **C** | **Last** — aggressive anti-bot | JobSpy **LinkedIn** |

`fetch_for_users.py` runs **JobSpy after** other sources. Prefer `--jobspy-site indeed` for daily runs; LinkedIn needs low `--risk-jobspy-per-site` / `--jobspy-results` and often proxies per upstream JobSpy docs.

---

## ✅ Additional integrated sources (plan)

| Area | Path | Notes |
|------|------|--------|
| Ashby | `ashby/` | Optional `--compensation` on public API |
| Workday | `sources/workday/`, `job_boards/workday_boards.json` | CXS POST; on by default (`--no-workday` to skip) |
| Netflix / Spotify / Uber | `sources/custom-ats/` | on by default (`--no-custom-ats` to skip) |
| Jobvite | `jobvite/`, `jobvite_boards.txt` | `--jobvite` |
| SmartRecruiters | `smartrecruiters/`, `smartrecruiters_boards.txt` | `--smartrecruiters` |
| Stapply seeds | `tests/import_stapply_slugs.py` → `data/*_seed.txt` | Used by `discover_boards.py` |
| Sitemap + RSS discovery | `tests/discover_career_web_sources.py` | `data/careers_domains_seed.txt` → `job_boards/sitemap_boards.json`, `job_boards/rss_feed_boards.json` |

---

## ❌ All non-working boards (single table)

| Platform | Reason |
|----------|--------|
| 80,000 Hours | API 404 "Invalid request" |
| ABA Career Center | ConnectionError |
| Adzuna | Needs API key |
| AngelList/Wellfound | Needs cookies/Apify |
| Arc | 404 |
| AskHunch | 404 / 400 |
| Bot-Jobs | 200 HTML (not RSS) |
| Braintrust | 404 |
| Built In | 404 |
| CareerBuilder | Needs API key |
| Career Vault | 404 |
| ClearanceJobs | 403 |
| ClojureJobboard | 200 HTML (not RSS) |
| Codementor | 404 |
| Contra | 404 |
| Creative Circle | RSS blog-style |
| Crypto Jobs List | 403 Cloudflare |
| Crossover | 200 HTML (no RSS) |
| Daily Remote | 404 |
| Dataaxy | 404 |
| DevOpsJobs | Timeout |
| Diversify Tech | No API / 404 |
| ABC Consultants, Kelly, TeamLease | India recruiters (need specific URLs) |
| Dribbble Jobs | 404 |
| Drupal | 404 / 403 |
| Drupal Jobs | 403 |
| EmbeddedJobs | 404 |
| Findjobit | 404 |
| Findwork | Needs API key |
| FlexJobs | Paywalled |
| Flexiple | 404 |
| foxhunch | ConnectionError |
| freelancermap | 404 |
| Freelancer | 404 |
| GitHub Careers | 404 |
| GitHub Jobs | Deprecated |
| Glassdoor | Not wired (JobSpy path unreliable); omitted in this repo |
| Dice | JobSpy has it |
| GolangProjects | 404 |
| Gun.io | RSS blog-style (12 entries) |
| Guru | 404 / Needs API key |
| HackerX | — |
| Hasjob | 404 |
| Hcareers | 404 |
| Hidden Jobs | Timeout |
| HigherEdJobs | 200 HTML (not RSS) |
| Hired | 200 HTML (non-RSS) |
| hiring.lat | 404 |
| HiringCafe | 403 Cloudflare |
| Hubstaff Talent | 404 |
| HN Hiring | Algolia (HN threads, not jobs) |
| InstaHyre | 403 |
| InternMatch | 200 HTML (not RSS) |
| Jobbatical | 404 |
| JobBoardAI | — |
| jobbox.io | 200, 0 entries |
| JOBBOX.io | 200, 0 entries |
| Joblist | 404 |
| Jooble | Needs approval |
| JustRemote | No RSS |
| Ladder | 404 |
| Lemon.io | 404 |
| ManpowerGroup India | 200 (check ct) |
| MarketingHire | RSS blog-style |
| MedReps | 404 |
| No Fluff Jobs | API 400 (salaryCurrency) |
| NoDesk | 404 |
| Niceboard | Login required |
| Otta | HTML SPA |
| Outsourcely | Timeout |
| Pallet | SSL error |
| Pangian | No API found |
| PowerToFly | 404 |
| Randstad India | 200 (check ct) |
| Recruit.net | 404 |
| Remote AI/Backend/Frontend/Game Jobs | 200 HTML |
| Remote Base | 404 |
| Remote Jobs | 404 |
| Remote Jobs Club | SSL error |
| Remote.com | 404 |
| Remote.co | No RSS (404) |
| Remote Freelance | SSLError |
| Remote Index | 403 |
| Remote Job Guru | 404 |
| Remote of Asia | ConnectionError |
| Remote Rocketship | 403 |
| Remote Team | 403 |
| Remote4Me | RSS 0 entries |
| RemoteBackendJobs | — |
| RemoteCircle | 200 HTML (non-RSS) |
| RemoteHabits | 404 |
| RemoteJobs.lat | 404 |
| Remotees | 404 |
| Remotesome | 404 |
| RemotelyOne | 404 |
| Remote100K | 404 |
| remote.io | 200 HTML |
| Remote Works | Timeout |
| Rejobs | — |
| Ruby On Remote | 403 |
| SlashJobs | 502 |
| Slasify | 404 |
| Simplified | 404 |
| SimplyHired | 404 |
| Skip The Drive | No RSS |
| Stack Overflow Jobs | 404 |
| Startups Gallery | Timeout |
| Stream Native | 404 |
| Superpath | 404 |
| TechCareers | 404 |
| tokenjobs.io | HTML |
| tokenjobs | 200 HTML |
| TotalJobs | 404 |
| Toptal | 404 |
| Turing | 404 / 200 HTML |
| UI/UX Jobs Board | 403 |
| UN Talent | 200 HTML (not JSON) |
| Upwork | No pip package |
| usemassive | 400 |
| Virtual Vocations | 404 |
| Vollna | 404 |
| We Love Remote | 200 HTML (non-RSS) |
| WeAreDistributed | 404 / timeout |
| Web3Jobs | 404 |
| Welcome To The Jungle | 403 Algolia |
| Who is Hiring | 200 HTML (non-RSS) |
| whoishiring | Timeout |
| Women Who Code | 404 |
| Work at a Startup | 404 |
| Workana | 404 |
| Workew | Blog feed, not jobs |
| Working Not Working | 200, 0 entries |
| zuhausejobs | Timeout |
