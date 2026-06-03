"""
Shared Intent Detection Utility.

Single source of truth for keyword search-intent indicator words and
rule-based classification logic used across the keyword_ai pipeline.

Consumers:
- ml_models/relevance_scorer_v2.py (feature extraction)
- ml_models/suggestion_generator.py (seed filtering)
- services/intent_classifier.py (advanced classification)
- services/traffic_enrichment.py (signal estimation)
"""

from __future__ import annotations

from typing import Dict, List, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Canonical indicator word lists
# ─────────────────────────────────────────────────────────────────────────────

INFORMATIONAL_INDICATORS: List[str] = [
    "what", "how", "why", "when", "where", "who", "which",
    "guide", "tutorial", "explained", "meaning", "definition",
    "learn", "understand", "examples", "tips", "ideas",
    "vs", "versus", "difference between", "comparison",
]

NAVIGATIONAL_INDICATORS: List[str] = [
    "login", "signin", "signup", "sign in", "sign up",
    "official", "website", "homepage", "app", "download",
    "portal", "dashboard", "account", "profile",
]

TRANSACTIONAL_INDICATORS: List[str] = [
    "buy", "purchase", "order", "shop", "price", "cost",
    "discount", "deal", "coupon", "sale", "cheap", "affordable",
    "free shipping", "add to cart", "checkout", "pay",
    "hire", "get", "free trial", "sign up", "subscribe",
    "book", "schedule", "demo",
]

COMMERCIAL_INDICATORS: List[str] = [
    "best", "top", "review", "reviews", "compare", "comparison",
    "vs", "alternative", "alternatives to", "features",
    "pros and cons", "rating", "recommended", "which is better",
    "software", "tool", "service", "agency", "company",
    "provider", "platform",
]


# ─────────────────────────────────────────────────────────────────────────────
# Core classification function
# ─────────────────────────────────────────────────────────────────────────────

def classify_keyword_intent(keyword: str) -> Dict[str, float]:
    """
    Rule-based intent classification returning normalised scores.

    Returns:
        Dict with keys: informational, navigational, transactional, commercial.
        Values are 0.0–1.0 (normalised by the highest-scoring intent).
    """
    keyword_lower = keyword.lower()

    scores = {
        "informational": _match_score(keyword_lower, INFORMATIONAL_INDICATORS),
        "navigational": _match_score(keyword_lower, NAVIGATIONAL_INDICATORS),
        "transactional": _match_score(keyword_lower, TRANSACTIONAL_INDICATORS),
        "commercial": _match_score(keyword_lower, COMMERCIAL_INDICATORS),
    }

    max_score = max(scores.values())
    if max_score > 0:
        scores = {k: round(v / max_score, 3) for k, v in scores.items()}

    return scores


def get_primary_intent(keyword: str) -> str:
    """Return the single dominant intent label for a keyword."""
    scores = classify_keyword_intent(keyword)
    if not any(scores.values()):
        return "informational"  # safe default
    return max(scores, key=scores.get)


def get_intent_features(keyword: str) -> List[float]:
    """
    Return 3-element binary feature vector for ML models:
    [informational, transactional_or_commercial, navigational]
    """
    keyword_lower = keyword.lower()
    is_info = any(w in keyword_lower for w in INFORMATIONAL_INDICATORS)
    is_trans = any(w in keyword_lower for w in TRANSACTIONAL_INDICATORS)
    is_comm = any(w in keyword_lower for w in COMMERCIAL_INDICATORS)
    is_nav = any(w in keyword_lower for w in NAVIGATIONAL_INDICATORS)
    return [float(is_info), float(is_trans or is_comm), float(is_nav)]


def has_commercial_intent(keyword: str) -> bool:
    """Quick check if a keyword has transactional or commercial intent."""
    kw = keyword.lower()
    return (
        any(w in kw for w in TRANSACTIONAL_INDICATORS)
        or any(w in kw for w in COMMERCIAL_INDICATORS)
    )


def has_question_intent(keyword: str) -> bool:
    """Quick check if a keyword is question-based (informational)."""
    question_starters = [
        "what", "how", "why", "when", "where", "who", "which",
        "can", "does", "is", "are", "will",
    ]
    kw = keyword.lower()
    return any(kw.startswith(q) for q in question_starters) or kw.endswith("?")


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _match_score(keyword_lower: str, indicators: List[str]) -> float:
    """Count indicator matches in keyword."""
    return sum(1.0 for ind in indicators if ind in keyword_lower)
