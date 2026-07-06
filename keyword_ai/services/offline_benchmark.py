"""Versioned offline keyword opportunity bands.

These bands are explicitly modeled. They never represent measured search volume,
CPC, or live ranking difficulty.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict


_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "offline_keyword_benchmarks.json"


@lru_cache(maxsize=1)
def load_benchmarks() -> Dict:
    with _DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def classify_keyword_opportunity(keyword: str) -> Dict:
    data = load_benchmarks()
    words = [word for word in keyword.lower().split() if word]
    word_count = len(words)
    phrase = " ".join(words)

    commercial_hits = [term for term in data["commercial_terms"] if term in phrase]
    transactional_hits = [term for term in data["transactional_terms"] if term in phrase]
    competition_hits = [term for term in data["competition_terms"] if term in phrase]
    is_question = bool(words and words[0] in data["question_terms"])

    if word_count <= 2:
        demand_key = "high"
    elif word_count <= 4:
        demand_key = "medium"
    elif word_count <= 6:
        demand_key = "low"
    else:
        demand_key = "very_low"

    if is_question and demand_key == "high":
        demand_key = "medium"
    if transactional_hits and demand_key in {"low", "very_low"}:
        demand_key = "medium"

    commercial_value = (
        "High" if transactional_hits
        else "Medium" if commercial_hits
        else "Low"
    )
    competition = (
        "High" if word_count <= 2 or len(competition_hits) >= 2
        else "Moderate" if competition_hits or commercial_hits
        else "Low"
    )
    band = data["demand_bands"][demand_key]

    return {
        "demand_level": band["label"],
        "modeled_range": band["range"],
        "commercial_value": commercial_value,
        "competition_band": competition,
        "confidence": "low",
        "provenance": "dataset_modeled",
        "dataset_version": data["version"],
        "methodology": data["methodology"],
        "evidence": {
            "word_count": word_count,
            "question_format": is_question,
            "commercial_modifiers": commercial_hits,
            "transactional_modifiers": transactional_hits,
        },
    }
