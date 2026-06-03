"""
LLM Prompt Generator with GEO awareness + current-year context injection.

Loads YAML templates from ``keyword_ai/prompts/keyword_expansion_templates.yaml``
and produces ready-to-send prompts that include:

- The current year (no more hardcoded "2024" style references)
- Regional/market guidance (NA, EU, APAC, LATAM, MEA, GLOBAL)
- Intent modifier suggestions (commercial / informational / etc.)
- Optional AEO and GEO prompt add-ons

Usage:
    from keyword_ai.services.llm_prompt_generator import build_expansion_prompt

    prompt, metadata = build_expansion_prompt(
        keyword="seo tools",
        n=10,
        target_region="NA",
        target_audience="SaaS marketers",
        include_aeo=True,
    )
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - yaml is a soft dep
    yaml = None

from ..utils.year_injector import build_year_context, inject_current_year

logger = logging.getLogger(__name__)


SUPPORTED_REGIONS = ("NA", "EU", "APAC", "LATAM", "MEA", "GLOBAL")
DEFAULT_REGION = "GLOBAL"

_TEMPLATES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "prompts", "keyword_expansion_templates.yaml"
)

_templates_cache: Optional[Dict] = None


def _load_templates() -> Dict:
    global _templates_cache
    if _templates_cache is not None:
        return _templates_cache
    if not yaml:
        logger.warning("PyYAML not installed - using minimal built-in templates.")
        _templates_cache = _builtin_templates()
        return _templates_cache
    try:
        with open(_TEMPLATES_PATH, "r", encoding="utf-8") as f:
            _templates_cache = yaml.safe_load(f) or _builtin_templates()
    except FileNotFoundError:
        logger.warning("Prompt template file not found: %s", _TEMPLATES_PATH)
        _templates_cache = _builtin_templates()
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to load prompt templates: %s", exc)
        _templates_cache = _builtin_templates()
    return _templates_cache


def _builtin_templates() -> Dict:
    """Minimal fallback templates when YAML file unavailable."""
    return {
        "keyword_expansion_base": {
            "GLOBAL": (
                'Generate {n} long-tail keyword variations for "{keyword}" relevant '
                "in {current_year}. Focus on emerging trends and broad consumer intent."
            ),
        },
        "geo_prompt_addons": "",
        "aeo_prompt_addons": "",
        "intent_modifiers": {},
    }


def _resolve_region(target_region: Optional[str]) -> str:
    if not target_region:
        return DEFAULT_REGION
    region = target_region.upper().strip()
    if region in SUPPORTED_REGIONS:
        return region
    return DEFAULT_REGION


def build_expansion_prompt(
    keyword: str,
    n: int = 10,
    target_region: Optional[str] = None,
    target_audience: Optional[str] = None,
    trend_focus: Optional[str] = None,
    include_geo: bool = True,
    include_aeo: bool = True,
    existing_keywords: Optional[List[str]] = None,
) -> Tuple[str, Dict]:
    """
    Build a region-aware, year-aware keyword expansion prompt.

    Returns:
        (prompt_text, metadata)
        metadata = {
            "prompt_version": "v2.2",
            "llm_model": (set by caller),
            "temperature": (set by caller),
            "region": "NA",
            "year": 2025,
            "trend_focus": "AI tools",
        }
    """
    templates = _load_templates()
    region = _resolve_region(target_region)
    year_ctx = build_year_context()

    base_section_map = templates.get("keyword_expansion_base", {}) or {}
    base_template = (
        base_section_map.get(region)
        or base_section_map.get("GLOBAL")
        or _builtin_templates()["keyword_expansion_base"]["GLOBAL"]
    )

    formatted_base = base_template.format(
        keyword=keyword,
        n=n,
        current_year=year_ctx["current_year"],
        target_region=region,
        target_audience=target_audience or "general audience",
        trend_focus=trend_focus or "current market trends",
    )

    sections: List[str] = [formatted_base.strip()]

    if include_geo:
        geo_addon = templates.get("geo_prompt_addons", "")
        if geo_addon:
            sections.append(geo_addon.format(target_region=region).strip())

    if include_aeo:
        aeo_addon = templates.get("aeo_prompt_addons", "")
        if aeo_addon:
            sections.append(aeo_addon.strip())

    if existing_keywords:
        existing_str = ", ".join(existing_keywords[:30])
        sections.append(f"AVOID duplicating any of these existing keywords:\n{existing_str}")

    sections.append(
        "Respond ONLY with valid JSON in the format:\n"
        "{\n"
        '  "suggestions": [\n'
        '    {\n'
        '      "keyword": "example keyword",\n'
        '      "intent": "Informational",\n'
        '      "region": "' + region + '",\n'
        '      "aeo_friendly": true,\n'
        '      "reasoning": "Why this matters",\n'
        '      "recommendation": "Specific action"\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    prompt_text = "\n\n".join(sections)
    # Final pass: ensure no stray {current_year} placeholders remain
    prompt_text = inject_current_year(prompt_text)

    metadata = {
        "prompt_version": "v2.2",
        "region": region,
        "year": year_ctx["current_year"],
        "trend_focus": trend_focus,
        "include_geo": include_geo,
        "include_aeo": include_aeo,
    }
    return prompt_text, metadata


def get_intent_modifiers(intent: str = "commercial") -> List[str]:
    """Return ready-to-fill intent modifier templates for a given intent."""
    templates = _load_templates()
    modifiers = templates.get("intent_modifiers", {}) or {}
    return list(modifiers.get(intent.lower(), []))


def apply_intent_modifiers(keyword: str, intent: str = "commercial") -> List[str]:
    """Apply intent modifier templates to a keyword and inject current year."""
    out: List[str] = []
    for tmpl in get_intent_modifiers(intent):
        try:
            applied = tmpl.format(keyword=keyword, current_year=build_year_context()["current_year"])
            out.append(applied)
        except KeyError:
            continue
    return out
