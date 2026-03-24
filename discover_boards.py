#!/usr/bin/env python3
"""
Discover public job boards: Greenhouse, Lever, Ashby.
Writes working boards to job_boards/greenhouse_boards.txt, lever_boards.txt, ashby_boards.txt.
Loads optional seed slug lists from data/greenhouse_slugs_seed.txt and data/ashby_slugs_seed.txt.
"""
import requests
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
JOB_BOARDS_DIR = SCRIPT_DIR / "job_boards"
JOB_BOARDS_DIR.mkdir(parents=True, exist_ok=True)
TIMEOUT = 8

# ----- Greenhouse (legacy API first, boards-api on 404 — same as greenhouse-lever/fetch.py) -----
GH_BOARDS_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
GH_LEGACY_API = "https://api.greenhouse.io/v1/boards/{slug}/jobs"
GH_SLUGS = [
    "stripe", "figma", "airtable", "canonical", "cloudflare", "spacex", "agoda",
    "discord", "dropbox", "twitch", "gitlab", "vercel", "datadog", "brex", "mercury",
    "reddit", "pinterest", "lyft", "airbnb", "mongodb", "elastic", "databricks",
    "amplitude", "mixpanel", "asana", "circleci", "fivetran", "coursera", "udemy",
    "duolingo", "roblox", "calendly", "lattice", "gusto", "justworks", "papaya",
    "kallesgroup", "airship", "energysolutions", "arcadiacareers", "assetliving", "ouihelp",
    "remote", "box", "zapier", "notion", "linear", "sentry", "posthog", "plaid", "ramp", "deel",
    "uber", "snap", "snowflake", "segment", "heap", "canva", "invision", "framer",
    "monday", "clickup", "render", "railway", "fly", "retool", "airbyte", "dbt",
    "quizlet", "niantic", "unity", "epic", "culture-amp", "rippling",
    "6sense", "acquire", "adhocexternal", "adquick", "anchorage", "appannie", "away", "bind",
    "bitmex", "bombas", "braceai", "calicolabs", "callisto", "cameraiq", "capsulecares", "careof",
    "cerebral", "circle", "civisanalytics", "cobaltio", "createme", "dailyharvest", "datagrail",
    "depop", "dfinity", "dharma", "diaco", "digit", "doitintl", "drop", "eden18", "eero",
    "eightsleep", "entelo", "everlane", "fernish", "fetchpackage", "fluxx", "flyhomes", "github",
    "greenbits", "guildeducation", "gumgum", "heal", "himshers", "incrediblehealthinc", "jopwell",
    "klara", "legion", "libra", "lightship", "liveramp", "lumahealth", "m1finance", "mercato",
    "misen", "monzo", "morty", "mythicalgames", "near", "nomnom", "oasislabs", "omadahealth",
    "omaze", "outsetmedical", "pathlight", "pathstream", "patreon", "pilothq", "poshmark",
    "postmates", "productiv", "propel", "quip", "rational", "room", "roostify", "skylotechnologies",
    "split", "sprinklr", "squire", "statestitle", "strava", "thefarmersdog", "therealreal",
    "threads", "tia", "tomorrowhealth", "trove", "tubitv", "twilio", "twistbioscience", "udacity",
    "urban", "verikai", "whipmediagroup", "whiteops", "within", "xmotorsai", "yext", "yipitdata",
    "zero",
]

# ----- Lever -----
LEVER_API = "https://api.lever.co/v0/postings/{slug}?mode=json"
LEVER_SLUGS = [
    "pigment", "coforma", "lever", "theathletic", "vrchat", "fanatics", "nielsen",
    "nvidia", "netflix", "shopify", "square", "block", "adobe", "salesforce",
    "intel", "amd", "qualcomm", "broadcom", "serviceNow", "servicenow",
    "att", "verizon", "tmobile", "comcast", "charter",
    "jpmorgan", "goldmansachs", "morganstanley", "citigroup", "bankofamerica",
    "walmart", "target", "costco", "homedepot", "lowes",
    "tesla", "rivian", "lucid", "gm", "ford",
    "meta", "apple", "google", "amazon", "microsoft",
    "coinbase", "kraken", "binance", "blockfi",
    "okta", "auth0", "cyberark", "paloaltonetworks",
    "atlassian", "zendesk", "freshworks", "hubspot", "salesforce",
    "crowdstrike", "zscaler", "fortinet", "checkpoint",
    "datadog", "newrelic", "dynatrace", "splunk",
    "snowflake", "databricks", "confluent", "elastic",
    "figma", "miro", "webflow", "abstract",
    "notion", "coda", "slite", "craft",
    "robinhood", "sofi", "chime", "affirm",
]

# ----- Ashby -----
ASHBY_API = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
ASHBY_SLUGS = [
    "Ashby", "ramp", "retool", "notion", "linear", "vercel", "stripe",
    "figma", "airtable", "discord", "dropbox", "spotify", "slack", "github",
    "box", "zapier", "twitch", "gitlab", "datadog", "sentry", "posthog",
    "plaid", "brex", "mercury", "deel", "remote", "reddit", "pinterest",
    "lyft", "uber", "airbnb", "mongodb", "elastic", "amplitude", "mixpanel",
    "asana", "monday", "circleci", "fivetran", "coursera", "udemy", "duolingo",
    "calendly", "lattice", "gusto", "rippling", "culture-amp", "cultureamp",
    "webflow", "supabase", "replicate", "runway", "midjourney",
    "anthropic", "openai", "cohere", "stability", "huggingface",
    "retool", "airtable", "coda", "notion", "slite",
    "deel", "remote", "oyster", "papaya", "globalization",
    "ramp", "brex", "mercury", "relay", "n26",
]


def _load_seed_lines(rel: str) -> list[str]:
    path = DATA_DIR / rel
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip().lower()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def probe(api_url: str, slug: str) -> bool:
    """Return True if board exists."""
    try:
        r = requests.get(api_url.format(slug=slug), timeout=TIMEOUT)
        return r.status_code == 200
    except Exception:
        return False


def probe_greenhouse(slug: str) -> bool:
    """True if either legacy or boards-api returns 200."""
    for tmpl in (GH_LEGACY_API, GH_BOARDS_API):
        try:
            r = requests.get(tmpl.format(slug=slug), timeout=TIMEOUT)
            if r.status_code == 404:
                continue
            return r.status_code == 200
        except Exception:
            continue
    return False


def discover(name: str, api: str, slugs: list[str], out_file: Path) -> list[str]:
    """Probe slugs and return working ones."""
    print(f"\n--- {name} ---")
    working = []
    for i, slug in enumerate(slugs, 1):
        if name == "Greenhouse":
            ok = probe_greenhouse(slug)
        else:
            ok = probe(api, slug)
        status = "✓" if ok else "✗"
        print(f"  [{i}/{len(slugs)}] {slug}: {status}")
        if ok:
            working.append(slug)
    working = sorted(set(working))
    out_file.write_text("\n".join(working) + "\n", encoding="utf-8")
    print(f"Found {len(working)} → {out_file.name}")
    return working


def main():
    print("Discovering public job boards...")
    gh_seed = _load_seed_lines("greenhouse_slugs_seed.txt")
    ash_seed = _load_seed_lines("ashby_slugs_seed.txt")
    gh_slugs = sorted(set(GH_SLUGS + gh_seed))
    ash_slugs = sorted(set(ASHBY_SLUGS + ash_seed))
    if gh_seed:
        print(f"  (+{len(gh_seed)} Greenhouse slugs from data/greenhouse_slugs_seed.txt)")
    if ash_seed:
        print(f"  (+{len(ash_seed)} Ashby slugs from data/ashby_slugs_seed.txt)")
    discover("Greenhouse", GH_BOARDS_API, gh_slugs, JOB_BOARDS_DIR / "greenhouse_boards.txt")
    discover("Lever", LEVER_API, LEVER_SLUGS, JOB_BOARDS_DIR / "lever_boards.txt")
    discover("Ashby", ASHBY_API, ash_slugs, JOB_BOARDS_DIR / "ashby_boards.txt")
    print("\nDone. Run fetch_for_users.py to use discovered boards.")


if __name__ == "__main__":
    main()
