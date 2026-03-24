#!/usr/bin/env python3
"""Per-fetcher keyword shaping for the orchestrator.

Each public API has different semantics (one token vs many vs single search phrase).
We trim to what the fetcher can use and return a log line for stdout.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KeywordAdapt:
    """Keywords to pass to the child CLI (after --keywords or as --query/--search)."""

    keywords: list[str]
    """For --query / --search single string, put one element: the full phrase."""

    search_phrase: str | None
    """Optional override for JobSpy/Himalayas-style single-string search."""

    log_line: str
    """Empty if nothing was dropped or special-cased."""


def _fmt_dropped(used: list[str], dropped: list[str]) -> str:
    if not dropped:
        return ""
    tail = ", ".join(dropped[:6])
    if len(dropped) > 6:
        tail += ", …"
    return f"omitted {len(dropped)} keyword(s): {tail}"


def adapt_keywords_for_source(source: str, raw: list[str]) -> KeywordAdapt:
    """
    Map orchestrator keyword list to what this source accepts.

    `source` is the orchestrator name (e.g. jobicy, himalayas, jobspy-indeed).
    """
    kw = [x for x in (raw or []) if x and str(x).strip()]
    if not kw:
        kw = ["manager", "remote"]

    # --- Single API search token (Jobicy HTTP param is one string; we send one CLI token) ---
    if source == "jobicy":
        chosen = [kw[0]]
        dropped = kw[1:]
        msg = (
            f"Jobicy search uses one keyword for the API; using {chosen[0]!r}. "
            + (_fmt_dropped(chosen, dropped) or "no extra terms passed.")
        )
        return KeywordAdapt(keywords=chosen, search_phrase=None, log_line=msg)

    # --- Single query string (Himalayas --query) ---
    if source == "himalayas":
        phrase = " ".join(kw[:2]) if len(kw) >= 2 else kw[0]
        dropped = kw[2:] if len(kw) > 2 else []
        msg = f"Himalayas --query is one phrase; using {phrase!r}."
        if dropped:
            msg += " " + _fmt_dropped([phrase], dropped)
        return KeywordAdapt(keywords=[phrase], search_phrase=phrase, log_line=msg)

    # --- JobSpy: one search string + optional post-filter keywords ---
    if source.startswith("jobspy-"):
        phrase_tokens = kw[:3]
        phrase = " ".join(phrase_tokens)
        dropped = kw[3:]
        msg = f"JobSpy uses one --search phrase; using {phrase!r}."
        if dropped:
            msg += " " + _fmt_dropped(phrase_tokens, dropped)
        # post-filter: same first 3 tokens max (child nargs+)
        return KeywordAdapt(keywords=phrase_tokens, search_phrase=phrase, log_line=msg)

    # --- Netflix public API query ---
    if source == "netflix-ats":
        phrase = " ".join(kw[:2]) if len(kw) >= 2 else kw[0]
        dropped = kw[2:] if len(kw) > 2 else []
        msg = f"Netflix --query is one phrase; using {phrase!r}."
        if dropped:
            msg += " " + _fmt_dropped([phrase], dropped)
        return KeywordAdapt(keywords=[phrase], search_phrase=phrase, log_line=msg)

    # --- landingjobs: fetcher ignores keywords ---
    if source == "landingjobs":
        return KeywordAdapt(
            keywords=[],
            search_phrase=None,
            log_line="landingjobs has no keyword filter; returning up to --limit rows from the feed.",
        )

    # --- Default: up to 5 terms for nargs+ RSS/API post-filters ---
    cap = 5
    if len(kw) <= cap:
        return KeywordAdapt(keywords=kw, search_phrase=None, log_line="")
    chosen = kw[:cap]
    dropped = kw[cap:]
    return KeywordAdapt(
        keywords=chosen,
        search_phrase=None,
        log_line=f"this source uses up to {cap} keywords; " + _fmt_dropped(chosen, dropped),
    )
