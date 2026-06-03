"""
GEO + AEO Signal Analyzer.

Adds two new scoring layers to keyword opportunities:

1. GEO Targeting Layer
   - Categorizes keywords by geographic scope (local / regional / national / international)
   - Detects location modifiers (city names, country codes, "near me")
   - Suggests regional optimization opportunities

2. AEO (Answer Engine Optimization) Layer
   - Identifies AI-friendly keywords (ChatGPT / Gemini / Copilot patterns)
   - Scores keywords on AI answer generation probability (0-100)
   - Recommends content formats for AI extraction (FAQ, definition, list)

Usage:
    from keyword_ai.services.geo_aeo_analyzer import analyze_geo_aeo

    signals = analyze_geo_aeo("plumber near me", page_topic="Local plumbing services")
    # {
    #   "geo_data": {...},
    #   "aeo_signals": {...},
    # }
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Location modifier lexicons
# ---------------------------------------------------------------------------

LOCAL_MODIFIERS = {
    "near me", "nearby", "in my area", "around me",
    "open now", "delivery", "local", "best near",
}

# Region -> example countries / market identifiers
REGION_MAP: Dict[str, List[str]] = {
    "NA": ["usa", "us", "united states", "canada", "ca", "mexico", "mx"],
    "EU": [
        "uk", "united kingdom", "england", "scotland", "wales", "ireland",
        "germany", "france", "spain", "italy", "netherlands", "sweden",
        "norway", "denmark", "finland", "poland",
    ],
    "APAC": [
        "australia", "au", "japan", "jp", "singapore", "sg", "india", "in",
        "china", "cn", "hong kong", "korea", "kr", "thailand", "indonesia",
        "philippines", "vietnam", "malaysia",
    ],
    "LATAM": ["brazil", "br", "argentina", "ar", "chile", "cl", "colombia"],
    "MEA": ["uae", "saudi arabia", "south africa", "egypt", "israel", "turkey"],
}

# Sample city/country tokens (lightweight; could be expanded with a dataset)
COMMON_CITY_TOKENS = {
    # US
    "new york", "los angeles", "chicago", "houston", "phoenix", "philadelphia",
    "san antonio", "san diego", "dallas", "san francisco", "seattle", "boston",
    "austin", "denver", "miami", "atlanta",
    # UK / EU
    "london", "manchester", "birmingham", "berlin", "munich", "paris", "madrid",
    "barcelona", "amsterdam", "rome", "milan", "dublin",
    # APAC
    "sydney", "melbourne", "tokyo", "osaka", "singapore", "mumbai", "delhi",
    "bangalore", "shanghai", "beijing", "hong kong", "seoul",
    # Pakistan/local
    "karachi", "lahore", "islamabad", "rawalpindi", "faisalabad", "peshawar",
}


# ---------------------------------------------------------------------------
# AEO signal heuristics
# ---------------------------------------------------------------------------

# AI-prompt patterns (questions, definitions, comparisons, "best/top" lists)
AEO_QUESTION_STARTERS = (
    "what", "how", "why", "when", "where", "who",
    "which", "can", "is", "are", "should", "do", "does",
)

AEO_FORMAT_HINTS = {
    "definition": [
        "what is", "definition of", "meaning of",
        # trailing tokens — e.g. "seo definition", "ai meaning"
        "definition", "meaning", "explained", "overview", "introduction",
    ],
    "list": [
        "best", "top", "list of", "examples of",
        "types of", "ways to", "tips for", "tools for",
    ],
    "tutorial": [
        "how to", "guide to", "tutorial", "step by step",
        "understanding", "learn", "beginner", "for beginners",
        "getting started",
    ],
    "comparison": [
        "vs", "versus", "compared to", "difference between",
        "alternative", "alternatives", "comparison",
    ],
    "faq": [
        "should i", "can i", "do i need", "is it worth",
        "when to", "why use", "who uses", "how does",
    ],
}


@dataclass
class GeoData:
    primary_scope: str = "national"              # local | regional | national | international
    detected_locations: List[str] = field(default_factory=list)
    detected_regions: List[str] = field(default_factory=list)
    has_local_modifier: bool = False
    geo_score: int = 0                            # 0-100
    search_volume_by_region: Dict[str, Optional[int]] = field(default_factory=dict)

    def as_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AEOSignals:
    score: int = 0                                # 0-100
    ai_friendly: bool = False
    suggested_formats: List[str] = field(default_factory=list)
    matched_patterns: List[str] = field(default_factory=list)
    answer_extraction_likelihood: str = "low"     # low | medium | high

    def as_dict(self) -> Dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# GEO analysis
# ---------------------------------------------------------------------------

def _detect_locations(keyword_lower: str) -> Tuple[List[str], List[str]]:
    """Return (matched_city_tokens, matched_regions) from a lowercased keyword."""
    matched_cities: List[str] = []
    matched_regions: List[str] = []

    for city in COMMON_CITY_TOKENS:
        if city in keyword_lower:
            matched_cities.append(city)

    for region, tokens in REGION_MAP.items():
        for token in tokens:
            pattern = rf"\b{re.escape(token)}\b"
            if re.search(pattern, keyword_lower):
                matched_regions.append(region)
                break  # one match per region is enough

    return matched_cities, matched_regions


def _has_local_modifier(keyword_lower: str) -> bool:
    return any(mod in keyword_lower for mod in LOCAL_MODIFIERS)


def analyze_geo(
    keyword: str,
    regional_volume_data: Optional[Dict[str, int]] = None,
) -> GeoData:
    """
    Classify a keyword geographically and surface region-specific signals.

    Args:
        keyword: The keyword phrase.
        regional_volume_data: Optional dict like {"US": 12000, "UK": 800} from
            SEMrush / DataForSEO.

    Returns:
        GeoData dataclass.
    """
    # Note: page_topic parameter was removed as it was not being used in the analysis
    if not keyword:
        return GeoData()

    keyword_lower = keyword.lower().strip()
    cities, regions = _detect_locations(keyword_lower)
    has_local = _has_local_modifier(keyword_lower)

    # Determine scope
    if has_local:
        scope = "local"
        geo_score = 90
    elif cities:
        scope = "local"
        geo_score = 80
    elif len(regions) >= 2:
        scope = "international"
        geo_score = 70
    elif len(regions) == 1:
        scope = "regional"
        geo_score = 60
    else:
        scope = "national"
        geo_score = 30

    return GeoData(
        primary_scope=scope,
        detected_locations=cities,
        detected_regions=regions,
        has_local_modifier=has_local,
        geo_score=geo_score,
        search_volume_by_region=regional_volume_data or {},
    )


# ---------------------------------------------------------------------------
# AEO analysis
# ---------------------------------------------------------------------------

def _aeo_format_hints(keyword_lower: str) -> Tuple[List[str], List[str]]:
    """
    Return (suggested_formats, matched_patterns).

    Multi-word patterns are matched as substrings; single-word patterns
    are matched on word boundaries to avoid false positives
    (e.g. 'list' inside 'specialist').
    """
    suggested: List[str] = []
    matched: List[str] = []
    tokens = keyword_lower.split()
    for fmt, patterns in AEO_FORMAT_HINTS.items():
        for p in patterns:
            if " " in p:
                # multi-word: substring match
                hit = p in keyword_lower
            else:
                # single-word: whole-word match only
                hit = p in tokens
            if hit:
                if fmt not in suggested:
                    suggested.append(fmt)
                matched.append(p)
                break
    return suggested, matched


def analyze_aeo(keyword: str) -> AEOSignals:
    """
    Score a keyword on AI/Answer Engine friendliness.

    AEO score factors:
    - Question starter (what/how/why/...) -> +25
    - Recognized format hint (definition, list, tutorial, comparison, faq) -> +20 per match (cap 60)
    - Long-tail (>= 4 words) -> +15
    - Generic single-word -> -10
    """
    if not keyword:
        return AEOSignals()

    kw_lower = keyword.lower().strip()
    tokens = kw_lower.split()

    score = 20  # baseline
    matched_patterns: List[str] = []

    # Word count bonus — long-tail keywords are inherently more AEO-friendly
    if len(tokens) >= 6:
        score += 20
    elif len(tokens) >= 4:
        score += 15
    elif len(tokens) >= 3:
        score += 10
    elif len(tokens) == 1:
        score -= 10

    if tokens and tokens[0] in AEO_QUESTION_STARTERS:
        score += 25
        matched_patterns.append(f"question_starter:{tokens[0]}")

    suggested_formats, format_hits = _aeo_format_hints(kw_lower)
    # First hit +20, additional hits +10 each (diminishing returns), cap at 40
    if format_hits:
        score += 20 + min(20, 10 * (len(format_hits) - 1))
    matched_patterns.extend(format_hits)

    score = max(0, min(100, score))

    if score >= 75:
        likelihood = "high"
    elif score >= 50:
        likelihood = "medium"
    else:
        likelihood = "low"

    return AEOSignals(
        score=score,
        ai_friendly=score >= 55,
        suggested_formats=suggested_formats or (["faq"] if score >= 50 else []),
        matched_patterns=matched_patterns,
        answer_extraction_likelihood=likelihood,
    )


# ---------------------------------------------------------------------------
# Combined entry point
# ---------------------------------------------------------------------------

def analyze_geo_aeo(
    keyword: str,
    page_topic: str = "",
    regional_volume_data: Optional[Dict[str, int]] = None,
) -> Dict:
    """
    Compute both GEO + AEO signals for a keyword.

    Returns dict with keys ``geo_data`` and ``aeo_signals`` matching the
    schema from the implementation prompt.
    """
    geo = analyze_geo(keyword, regional_volume_data=regional_volume_data)
    aeo = analyze_aeo(keyword)
    return {
        "geo_data": {
            "regions": geo.detected_regions,
            "primary_scope": geo.primary_scope,
            "detected_locations": geo.detected_locations,
            "has_local_modifier": geo.has_local_modifier,
            "geo_score": geo.geo_score,
            "search_volume_by_region": geo.search_volume_by_region,
        },
        "aeo_signals": aeo.as_dict(),
    }


def analyze_keywords_batch(
    keywords: List[str],
    regional_volume_data: Optional[Dict[str, Dict[str, int]]] = None,
) -> List[Dict]:
    """
    Analyze a batch of keywords. ``regional_volume_data`` maps
    keyword -> {region -> volume}.
    """
    out: List[Dict] = []
    for kw in keywords or []:
        if not kw:
            continue
        rvd = (regional_volume_data or {}).get(kw, {}) if regional_volume_data else {}
        out.append({"keyword": kw, **analyze_geo_aeo(kw, regional_volume_data=rvd)})
    return out
