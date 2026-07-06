"""Dynamic evidence-candidate retrieval and local cross-encoder reranking."""

from __future__ import annotations

from typing import Dict, Iterable, List

import numpy as np

from .embeddings import get_embeddings
from .model_manager import get_reranker_model


_SOURCE_BONUS = {
    "observed_serp": 0.10,
    "competitor_heading": 0.08,
    "competitor_content": 0.06,
    "observed_page": 0.06,
    "keybert": 0.05,
    "tfidf": 0.04,
}


def _normalize_scores(values: np.ndarray) -> np.ndarray:
    if not len(values):
        return values
    low, high = float(values.min()), float(values.max())
    if high - low < 1e-8:
        return np.full_like(values, 0.5, dtype=np.float32)
    return ((values - low) / (high - low)).astype(np.float32)


def rank_evidence_candidates(
    page_summary: str,
    content_embedding: np.ndarray,
    candidates: Iterable[Dict],
    top_k: int = 30,
    dense_shortlist: int = 60,
    use_cross_encoder: bool = True,
) -> List[Dict]:
    """Rank only candidates discovered from this page, its SERPs, or competitors."""
    deduplicated: Dict[str, Dict] = {}
    for item in candidates:
        keyword = " ".join(str(item.get("keyword", "")).lower().split())
        if not keyword:
            continue
        sources = set(item.get("sources") or [item.get("source", "unknown")])
        if keyword in deduplicated:
            deduplicated[keyword]["sources"] = sorted(
                set(deduplicated[keyword]["sources"]) | sources
            )
        else:
            deduplicated[keyword] = {"keyword": keyword, "sources": sorted(sources)}

    rows = list(deduplicated.values())
    if not rows or content_embedding is None or not len(content_embedding):
        return []

    keyword_vectors = get_embeddings([row["keyword"] for row in rows])
    dense_scores = keyword_vectors @ content_embedding
    order = np.argsort(dense_scores)[::-1][:dense_shortlist]
    shortlisted = [rows[index] for index in order]
    shortlisted_dense = np.asarray([dense_scores[index] for index in order], dtype=np.float32)

    cross_raw = None
    ranking_method = "dense_only"
    if use_cross_encoder and shortlisted:
        try:
            reranker = get_reranker_model()
            pairs = [(row["keyword"], page_summary) for row in shortlisted]
            cross_raw = np.asarray(
                reranker.predict(pairs, show_progress_bar=False),
                dtype=np.float32,
            ).reshape(-1)
            ranking_method = "cross_encoder"
        except Exception:
            cross_raw = None

    dense_normalized = _normalize_scores(shortlisted_dense)
    cross_normalized = _normalize_scores(cross_raw) if cross_raw is not None else dense_normalized

    results = []
    for index, row in enumerate(shortlisted):
        source_bonus = max(
            (_SOURCE_BONUS.get(source, 0.0) for source in row["sources"]),
            default=0.0,
        )
        score = (
            0.50 * float(cross_normalized[index])
            + 0.40 * float(dense_normalized[index])
            + source_bonus
        )
        results.append({
            **row,
            "dense_similarity": round(float(shortlisted_dense[index]), 4),
            "reranker_score": round(float(cross_normalized[index]), 4),
            "relevance_score": round(min(1.0, score) * 100, 2),
            "ranking_method": ranking_method,
            "provenance": "dynamic_evidence_ranking",
        })

    results.sort(key=lambda item: item["relevance_score"], reverse=True)
    return results[:top_k]
