"""Candidate quality gate for evidence-bearing keyword analysis."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Tuple


_FRAGMENT_ENDINGS = {
    "enable", "enables", "facilitate", "facilitates", "streamline",
    "operational", "digital", "customer", "built",
}
_GENERIC_WORDS = {
    "business", "system", "systems", "process", "processes", "solution",
    "solutions", "experience", "experiences", "operational", "digital",
    "customer", "commerce", "development", "challenge",
}
_MARKETING_PATTERNS = (
    r"^trusted by\b",
    r"^capabilities?\b.*\bbuilds? for\b",
    r"^modern\b.*\bruns? on\b",
    r"^built\b",
    r"\bcompanies building\b",
)

_QUESTION_STARTERS = {
    "what", "why", "how", "when", "where", "who", "which", "can", "does", "is", "are",
}


def assess_candidate(keyword: str, page_text: str = "") -> Dict:
    normalized = " ".join(re.findall(r"[a-z0-9][a-z0-9+.#'-]*", (keyword or "").lower()))
    words = normalized.split()
    reasons: List[str] = []

    if not words or len(words) > 8:
        reasons.append("length")
    elif len(words) == 1 and (len(words[0]) < 4 or words[0] in _GENERIC_WORDS):
        reasons.append("length")
    if len(set(words)) != len(words):
        reasons.append("repeated_words")
    if words and words[-1] in _FRAGMENT_ENDINGS and words[0] not in _QUESTION_STARTERS:
        reasons.append("fragment_ending")
    if len(words) >= 3 and words[-2:] in (["digital", "experiences"], ["operational", "customer"]):
        reasons.append("awkward_sequence")
    if words and all(word in _GENERIC_WORDS for word in words):
        reasons.append("generic_fragment")
    if any(re.search(pattern, normalized) for pattern in _MARKETING_PATTERNS):
        reasons.append("marketing_sentence")

    exact_page_match = bool(normalized and normalized in (page_text or "").lower())
    score = 100
    score -= 35 * len(reasons)
    if exact_page_match:
        score += 10
    if words and words[0] in _QUESTION_STARTERS:
        score += 5
    score = max(0, min(100, score))

    return {
        "keyword": normalized,
        "accepted": not reasons and score >= 55,
        "quality_score": score,
        "reasons": reasons,
        "exact_page_match": exact_page_match,
        "provenance": "observed_page" if exact_page_match else "candidate_model",
    }


def filter_candidates(
    keywords: Iterable[str],
    page_text: str = "",
    limit: int = 15,
) -> Tuple[List[str], List[Dict]]:
    accepted: List[str] = []
    diagnostics: List[Dict] = []
    seen = set()

    for keyword in keywords:
        result = assess_candidate(keyword, page_text)
        diagnostics.append(result)
        normalized = result["keyword"]
        if result["accepted"] and normalized not in seen:
            seen.add(normalized)
            accepted.append(normalized)
        if len(accepted) >= limit:
            break

    return accepted, diagnostics
