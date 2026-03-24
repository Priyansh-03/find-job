"""Location hints → India/geo tokens, Authentic Jobs slug, Jobicy geo, and row filtering.

Used by fetch_for_users (orchestrator) and available on sys.path for fetcher scripts."""
from __future__ import annotations

INDIA_HINT_SUBSTRINGS: tuple[str, ...] = (
    "india",
    "indian",
    "bengaluru",
    "bangalore",
    "mumbai",
    "delhi",
    "hyderabad",
    "pune",
    "chennai",
    "kolkata",
    "jaipur",
    "gurgaon",
    "gurugram",
    "noida",
    "ahmedabad",
)

# Extra metros / cities (dashboard output filter + future matchers).
INDIA_EXTRA_CITY_SUBSTRINGS: tuple[str, ...] = (
    "coimbatore",
    "bhopal",
    "indore",
    "vadodara",
    "baroda",
    "surat",
    "lucknow",
    "kanpur",
    "nagpur",
    "patna",
    "ranchi",
    "guwahati",
    "amritsar",
    "ludhiana",
    "varanasi",
    "mysore",
    "mysuru",
    "thiruvananthapuram",
    "trivandrum",
    "visakhapatnam",
    "vizag",
    "nashik",
    "madurai",
    "jodhpur",
    "raipur",
    "kota",
    "gwalior",
    "faridabad",
    "ghaziabad",
    "thane",
    "agra",
    "bhubaneswar",
    "kochi",
    "cochin",
)

# States / UTs as written in English job ads (dashboard India-only output filter).
INDIA_STATE_UT_SUBSTRINGS: tuple[str, ...] = (
    "andhra pradesh",
    "arunachal pradesh",
    "assam",
    "bihar",
    "chhattisgarh",
    "goa",
    "gujarat",
    "haryana",
    "himachal pradesh",
    "jharkhand",
    "karnataka",
    "kerala",
    "madhya pradesh",
    "maharashtra",
    "manipur",
    "meghalaya",
    "mizoram",
    "nagaland",
    "odisha",
    "orissa",
    "punjab",
    "rajasthan",
    "sikkim",
    "tamil nadu",
    "telangana",
    "tripura",
    "uttar pradesh",
    "uttarakhand",
    "west bengal",
    "jammu and kashmir",
    "jammu & kashmir",
    "ladakh",
    "puducherry",
    "pondicherry",
    "chandigarh",
    "andaman",
    "nicobar",
    "delhi ncr",
    "national capital region",
    "ncr",
)

NEUTRAL_LOCATION_HINTS: frozenset[str] = frozenset(
    {"worldwide", "global", "anywhere", "remote", "ww", ""}
)


def location_suggests_india(text: str) -> bool:
    t = (text or "").lower()
    return any(tok in t for tok in INDIA_HINT_SUBSTRINGS)


def india_output_ui_filter_substrings() -> list[str]:
    """Tokens for the dashboard “India only” output filter (longest first for multi-word states)."""
    merged: list[str] = []
    for t in (
        *INDIA_HINT_SUBSTRINGS,
        *INDIA_EXTRA_CITY_SUBSTRINGS,
        *INDIA_STATE_UT_SUBSTRINGS,
    ):
        s = (t or "").strip().lower()
        if s and s not in merged:
            merged.append(s)
    merged.sort(key=len, reverse=True)
    return merged


def location_substrings_for_hint(hint: str) -> list[str]:
    """Lowercase substrings for matching job text when filtering (empty = no filter)."""
    h = (hint or "").strip().lower()
    if not h or h in NEUTRAL_LOCATION_HINTS:
        return []
    if location_suggests_india(h):
        return list(dict.fromkeys((*INDIA_HINT_SUBSTRINGS, "india", "indian")))
    parts = [p.strip().lower() for p in h.replace(",", " ").split() if len(p.strip()) >= 2]
    return list(dict.fromkeys(parts if parts else [h]))


def parse_comma_substrings(s: str) -> list[str]:
    return [x.strip().lower() for x in (s or "").split(",") if x.strip()]


def job_text_blob(job: dict, fields: tuple[str, ...]) -> str:
    chunks: list[str] = []
    for k in fields:
        v = job.get(k)
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            chunks.extend(str(x) for x in v)
        else:
            chunks.append(str(v))
    return " ".join(chunks)


def filter_jobs_by_location_substrings(
    jobs: list[dict],
    substrings: list[str],
    *,
    fields: tuple[str, ...] = (
        "title",
        "link",
        "summary",
        "company",
        "category",
        "location",
    ),
) -> list[dict]:
    if not substrings:
        return jobs
    subs = [s.lower() for s in substrings if s]
    if not subs:
        return jobs

    def ok(j: dict) -> bool:
        blob = job_text_blob(j, fields).lower()
        return any(s in blob for s in subs)

    return [j for j in jobs if ok(j)]


def authentic_jobs_search_location_slug(hint: str) -> str:
    """Authentic Jobs ``search_location`` RSS param, or '' for the default feed."""
    h = (hint or "").strip().lower()
    if not h or h in NEUTRAL_LOCATION_HINTS:
        return ""
    if location_suggests_india(h):
        return "india"
    token = h.split()[0]
    if token.isalpha() and 2 <= len(token) <= 32:
        return token
    return ""


def jobicy_geo_from_hint(hint: str) -> str:
    """Map user hint to Jobicy API ``geo`` (empty = all regions)."""
    h = (hint or "").strip().lower()
    if not h or h in NEUTRAL_LOCATION_HINTS:
        return ""
    if location_suggests_india(h):
        return "apac"
    geo_map: dict[str, str] = {
        "usa": "usa",
        "us": "usa",
        "america": "usa",
        "united states": "usa",
        "uk": "uk",
        "united kingdom": "uk",
        "britain": "uk",
        "england": "uk",
        "canada": "canada",
        "germany": "germany",
        "france": "france",
        "spain": "spain",
        "australia": "australia",
        "japan": "japan",
        "singapore": "singapore",
        "brazil": "brazil",
        "mexico": "mexico",
        "europe": "emea",
        "eu": "emea",
        "emea": "emea",
        "latam": "latam",
        "apac": "apac",
    }
    if h in geo_map:
        return geo_map[h]
    first = h.split(",")[0].strip().split()[0] if h else ""
    return geo_map.get(first, "")


def merge_location_cells(a: str, b: str) -> str:
    """Combine two location strings when deduping the same job URL."""
    x, y = (a or "").strip(), (b or "").strip()
    if not y:
        return x
    if not x:
        return y
    if y.lower() in x.lower() or x.lower() in y.lower():
        return x if len(x) >= len(y) else y
    return f"{x}; {y}"
