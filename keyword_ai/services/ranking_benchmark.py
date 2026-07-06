"""Offline evaluation metrics for keyword ranking releases."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List


def is_malformed_keyword(keyword: str) -> bool:
    words = str(keyword or "").strip().split()
    if not 2 <= len(words) <= 12:
        return True
    if len(keyword) > 120 or not re.search(r"[A-Za-z]", keyword):
        return True
    return any(len(word) > 35 for word in words)


def precision_at_k(predicted: Iterable[str], accepted: Iterable[str], k: int = 10) -> float:
    predicted = [item.lower().strip() for item in predicted][:k]
    accepted = {item.lower().strip() for item in accepted}
    if not predicted:
        return 0.0
    return sum(item in accepted for item in predicted) / len(predicted)


def evaluate_cases(cases: List[Dict], k: int = 10) -> Dict:
    precisions = []
    predicted_count = 0
    accepted_count = 0
    malformed_count = 0

    for case in cases:
        predicted = case.get("predicted", [])
        accepted = case.get("accepted", [])
        precisions.append(precision_at_k(predicted, accepted, k=k))
        predicted_count += len(predicted)
        accepted_count += sum(
            keyword.lower().strip() in {item.lower().strip() for item in accepted}
            for keyword in predicted
        )
        malformed_count += sum(is_malformed_keyword(keyword) for keyword in predicted)

    return {
        "cases": len(cases),
        "precision_at_10": round(sum(precisions) / len(precisions), 4) if precisions else 0.0,
        "acceptance_rate": round(accepted_count / predicted_count, 4) if predicted_count else 0.0,
        "malformed_keyword_rate": round(malformed_count / predicted_count, 4) if predicted_count else 0.0,
    }