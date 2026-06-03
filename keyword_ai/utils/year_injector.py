"""
Dynamic Year Injection Utility.

Replaces hardcoded year references with the current year across LLM outputs,
prompts, and template responses. Centralized for consistency.

Usage:
    from keyword_ai.utils.year_injector import inject_current_year, current_year

    text = inject_current_year("Complete SEO Guide {current_year}")
    # -> "Complete SEO Guide 2025"

    year = current_year()  # -> 2025
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


# Placeholder tokens recognized by the injector
PLACEHOLDER_TOKENS = (
    "{current_year}",
    "{CURRENT_YEAR}",
    "{year}",
    "{YEAR}",
)

# Heuristic regex to catch outdated standalone year mentions (2018-2025)
# in marketing/SEO text. Avoids touching version numbers or codes by
# requiring word boundaries.
_OUTDATED_YEAR_RE = re.compile(r"\b(20(?:1[8-9]|2[0-5]))\b")


def current_year(year: Optional[int] = None) -> int:
    """Return the current calendar year, or the provided override."""
    if year is not None:
        return int(year)
    return datetime.now().year


def inject_current_year(text: str, year: Optional[int] = None) -> str:
    """
    Replace ``{current_year}`` placeholders with the actual year.

    Args:
        text: String potentially containing ``{current_year}`` placeholders.
        year: Optional explicit year override (defaults to ``datetime.now().year``).

    Returns:
        Text with placeholders replaced by the resolved year.
    """
    if not isinstance(text, str) or not text:
        return text

    resolved = str(current_year(year))
    for token in PLACEHOLDER_TOKENS:
        if token in text:
            text = text.replace(token, resolved)
    return text


def refresh_outdated_years(text: str, year: Optional[int] = None) -> str:
    """
    Replace outdated standalone year references (2018-2024) with the current year.

    Use sparingly — only for LLM/marketing output where stale years should be
    refreshed automatically. Will NOT touch the current/future year, version
    numbers, or non-year four-digit codes that fall outside the outdated range.
    """
    if not isinstance(text, str) or not text:
        return text

    resolved = str(current_year(year))
    return _OUTDATED_YEAR_RE.sub(resolved, text)


def inject_in_dict(
    data: Union[Dict[str, Any], List[Any], str],
    year: Optional[int] = None,
    refresh_outdated: bool = False,
) -> Any:
    """
    Recursively walk a dict/list structure and inject the current year into all strings.

    Args:
        data: Arbitrary JSON-serializable structure (dict, list, str, etc.).
        year: Optional explicit year override.
        refresh_outdated: When True, also rewrite stale 20xx year mentions.

    Returns:
        New structure with all string values year-injected.
    """
    if isinstance(data, dict):
        return {
            key: inject_in_dict(value, year=year, refresh_outdated=refresh_outdated)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [
            inject_in_dict(item, year=year, refresh_outdated=refresh_outdated)
            for item in data
        ]
    if isinstance(data, str):
        out = inject_current_year(data, year=year)
        if refresh_outdated:
            out = refresh_outdated_years(out, year=year)
        return out
    return data


def build_year_context(year: Optional[int] = None) -> Dict[str, Any]:
    """
    Build a context dict used by prompt templates for year-aware generation.

    Returns:
        {
            "current_year": 2025,
            "next_year": 2026,
            "previous_year": 2024,
            "year_label": "in 2025",
        }
    """
    year_val = current_year(year)
    return {
        "current_year": year_val,
        "next_year": year_val + 1,
        "previous_year": year_val - 1,
        "year_label": f"in {year_val}",
    }
