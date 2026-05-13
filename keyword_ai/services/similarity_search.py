import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from .embeddings import get_embeddings


# A small built-in seed vocabulary for expansion.
# In production you can replace this with a loaded CSV word list.
SEED_VOCABULARY = [
    "best", "top", "cheap", "affordable", "buy", "review", "guide",
    "how to", "tutorial", "vs", "comparison", "alternative", "near me",
    "online", "free", "download", "software", "tool", "service", "price",
    "example", "template", "tips", "strategy", "2026", "beginner",
    "advanced", "professional", "course", "learn",
]


def expand_keywords(
    seed_keywords: list[str],
    vocabulary: list[str] = None,
    top_k: int = 10,
    similarity_threshold: float = 0.4,
) -> list[dict]:
    """
    Given a list of seed keywords (from KeyBERT), find semantically similar
    terms from the vocabulary using cosine similarity on embeddings.

    Returns a list of dicts sorted by similarity score (descending).
    """
    if vocabulary is None:
        vocabulary = SEED_VOCABULARY

    if not seed_keywords or not vocabulary:
        return []

    # Build candidate phrases by combining seeds + modifiers
    candidates = []
    for seed in seed_keywords:
        for modifier in vocabulary:
            candidates.append(f"{seed} {modifier}")
            candidates.append(f"{modifier} {seed}")

    # Deduplicate
    candidates = list(set(candidates))

    # Encode everything
    seed_embeddings = get_embeddings(seed_keywords)       # (n_seeds, 384)
    candidate_embeddings = get_embeddings(candidates)     # (n_candidates, 384)

    # Average seed vector as the query
    query_vector = seed_embeddings.mean(axis=0, keepdims=True)  # (1, 384)

    # Compute cosine similarity between query and all candidates
    scores = cosine_similarity(query_vector, candidate_embeddings)[0]  # (n_candidates,)

    # Filter and rank
    results = []
    for phrase, score in zip(candidates, scores):
        if score >= similarity_threshold:
            results.append({"keyword": phrase, "similarity_score": round(float(score), 4)})

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results[:top_k]