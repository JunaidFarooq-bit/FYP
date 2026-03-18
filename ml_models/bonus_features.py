"""
==============================================================
STEP 9: BONUS FEATURES
==============================================================
Advanced keyword analysis features:
  1. Keyword Intent Classification
  2. Keyword Clustering
  3. Long-tail Keyword Generation
  4. Topic Expansion

These build on top of the same Sentence Transformer embeddings,
so no additional model downloads are needed.
"""

import re
import json
import logging
import numpy as np
from typing import Optional
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# 1. KEYWORD INTENT CLASSIFICATION
# ══════════════════════════════════════════════════════════════
# Search intent = the underlying goal behind a search query.
# Google's 4 main intents:
#   Informational  → "what is seo", "how to do keyword research"
#   Navigational   → "ahrefs login", "google search console"
#   Commercial     → "best seo tools", "ahrefs vs semrush"
#   Transactional  → "buy seo audit", "seo tool pricing"

# Heuristic word lists — expand these for better accuracy.
# For production: fine-tune a classifier on labelled data.
INTENT_SIGNALS = {
    "informational": [
        "what", "how", "why", "when", "where", "who", "which",
        "guide", "tutorial", "tips", "learn", "understand",
        "definition", "meaning", "example", "explain", "introduction",
    ],
    "navigational": [
        "login", "sign in", "account", "dashboard", "official",
        "website", "homepage", "download", "app",
    ],
    "commercial": [
        "best", "top", "review", "reviews", "compare", "comparison",
        "vs", "versus", "alternative", "alternatives", "recommend",
        "recommended", "ranking", "rated",
    ],
    "transactional": [
        "buy", "purchase", "price", "pricing", "cost", "cheap",
        "affordable", "deal", "discount", "trial", "free trial",
        "get", "hire", "order", "subscribe", "subscription",
    ],
}


def classify_keyword_intent(keyword: str) -> dict:
    """
    Classifies the search intent of a keyword using heuristics.

    Scores each intent category by counting signal word matches,
    then returns the highest-scoring intent and all scores.

    Args:
        keyword: Keyword string to classify.

    Returns:
        {
            "keyword"    : "best seo tools",
            "intent"     : "commercial",
            "confidence" : "high",
            "scores"     : {"commercial": 1, "informational": 0, ...}
        }
    """
    keyword_lower = keyword.lower()
    words = set(keyword_lower.split())

    scores = {}
    for intent, signals in INTENT_SIGNALS.items():
        # Count how many signal words appear in the keyword
        score = sum(1 for signal in signals if signal in keyword_lower or signal in words)
        scores[intent] = score

    max_score = max(scores.values())
    if max_score == 0:
        # No signals found — default to informational (most common)
        top_intent = "informational"
        confidence = "low"
    else:
        top_intent = max(scores, key=scores.get)
        confidence = "high" if max_score >= 2 else "medium"

    return {
        "keyword": keyword,
        "intent": top_intent,
        "confidence": confidence,
        "scores": scores,
    }


def classify_keywords_batch(keywords: list[str]) -> list[dict]:
    """Classify intent for a list of keywords."""
    return [classify_keyword_intent(kw) for kw in keywords]


# ══════════════════════════════════════════════════════════════
# 2. KEYWORD CLUSTERING
# ══════════════════════════════════════════════════════════════
# Groups semantically similar keywords together using KMeans
# on their sentence embeddings.
# Use case: organize large keyword lists into content themes.

def cluster_keywords(
    keywords: list[str],
    n_clusters: int = 5,
    model_name: str = "all-MiniLM-L6-v2",
) -> dict[int, list[str]]:
    """
    Groups keywords into semantic clusters using KMeans.

    Algorithm:
      1. Encode all keywords to embeddings
      2. L2-normalize embeddings
      3. Run KMeans clustering
      4. Group keywords by cluster label

    Args:
        keywords  : List of keyword strings.
        n_clusters: Number of clusters (try sqrt(N) as a heuristic).
        model_name: SentenceTransformer model to use.

    Returns:
        Dict mapping cluster_id → list of keywords in that cluster.

    Example:
        clusters = cluster_keywords(
            ["seo tools", "rank tracker", "backlink checker",
             "content ideas", "blog topics"],
            n_clusters=2
        )
        # {0: ["seo tools", "rank tracker", "backlink checker"],
        #  1: ["content ideas", "blog topics"]}
    """
    from sentence_transformers import SentenceTransformer

    if len(keywords) < n_clusters:
        raise ValueError(
            f"Need at least {n_clusters} keywords to form {n_clusters} clusters. "
            f"Got {len(keywords)}."
        )

    logger.info(f"Clustering {len(keywords)} keywords into {n_clusters} groups...")

    model = SentenceTransformer(model_name)
    embeddings = model.encode(keywords, convert_to_numpy=True, normalize_embeddings=True)

    # KMeans on normalized vectors approximates spherical k-means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    # Group keywords by cluster label
    clusters: dict[int, list[str]] = {i: [] for i in range(n_clusters)}
    for keyword, label in zip(keywords, labels):
        clusters[int(label)].append(keyword)

    return clusters


def cluster_keywords_with_labels(
    keywords: list[str],
    n_clusters: int = 5,
) -> list[dict]:
    """
    Clusters keywords and assigns human-readable labels.
    The label is derived from the most representative keyword
    in each cluster (closest to the cluster centroid).

    Returns:
        [
            {"cluster_id": 0, "label": "seo tools", "keywords": [...]},
            ...
        ]
    """
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(keywords, convert_to_numpy=True, normalize_embeddings=True)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    result = []
    for cluster_id in range(n_clusters):
        mask = labels == cluster_id
        cluster_keywords = [kw for kw, m in zip(keywords, mask) if m]
        cluster_embeddings = embeddings[mask]

        # Find keyword closest to centroid = cluster "label"
        centroid = kmeans.cluster_centers_[cluster_id]
        distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)
        label_keyword = cluster_keywords[np.argmin(distances)]

        result.append({
            "cluster_id": cluster_id,
            "label": label_keyword,
            "keywords": cluster_keywords,
            "size": len(cluster_keywords),
        })

    return sorted(result, key=lambda x: x["size"], reverse=True)


# ══════════════════════════════════════════════════════════════
# 3. LONG-TAIL KEYWORD GENERATION
# ══════════════════════════════════════════════════════════════
# Long-tail keywords = more specific, lower-competition queries.
# Strategy: combine seed keyword with modifier patterns.

LONG_TAIL_TEMPLATES = {
    "how_to": [
        "how to {seed}",
        "how to {seed} for beginners",
        "how to {seed} step by step",
        "how to {seed} fast",
        "how to {seed} free",
        "how to learn {seed}",
    ],
    "questions": [
        "what is {seed}",
        "why use {seed}",
        "when to use {seed}",
        "is {seed} worth it",
        "does {seed} work",
        "what are the best {seed}",
    ],
    "modifiers": [
        "best {seed}",
        "top {seed}",
        "free {seed}",
        "{seed} for beginners",
        "{seed} tutorial",
        "{seed} guide",
        "{seed} tips",
        "{seed} examples",
        "{seed} checklist",
        "{seed} 2024",
        "advanced {seed}",
        "beginner {seed}",
        "{seed} for small business",
        "{seed} for ecommerce",
    ],
    "commercial": [
        "best {seed} tools",
        "{seed} software",
        "{seed} pricing",
        "{seed} free trial",
        "{seed} vs",
        "affordable {seed}",
        "{seed} review",
        "{seed} comparison",
    ],
}


def generate_long_tail_keywords(
    seed: str,
    categories: Optional[list[str]] = None,
    max_per_category: int = 5,
) -> dict[str, list[str]]:
    """
    Generates long-tail keyword variations from a seed keyword.

    Args:
        seed            : Base seed keyword (e.g., "seo tools").
        categories      : Which template categories to use.
                          None = use all categories.
        max_per_category: Max variations per category.

    Returns:
        Dict mapping category name → list of long-tail keywords.

    Example:
        generate_long_tail_keywords("seo tools")
        # {
        #   "how_to"   : ["how to use seo tools", ...],
        #   "questions": ["what is seo tools", ...],
        #   "modifiers": ["best seo tools", ...],
        #   "commercial": ["seo tools pricing", ...],
        # }
    """
    seed = seed.strip().lower()
    active_categories = categories or list(LONG_TAIL_TEMPLATES.keys())
    result = {}

    for category in active_categories:
        if category not in LONG_TAIL_TEMPLATES:
            continue
        templates = LONG_TAIL_TEMPLATES[category][:max_per_category]
        keywords = [t.format(seed=seed) for t in templates]
        result[category] = keywords

    return result


def generate_long_tail_flat(seed: str, max_total: int = 20) -> list[str]:
    """
    Flattened version — returns a single list of long-tail variants.

    Args:
        seed     : Seed keyword.
        max_total: Maximum number of keywords to return.

    Returns:
        List of long-tail keyword strings.
    """
    by_category = generate_long_tail_keywords(seed)
    flat = []
    for keywords in by_category.values():
        flat.extend(keywords)
    return flat[:max_total]


# ══════════════════════════════════════════════════════════════
# 4. TOPIC EXPANSION
# ══════════════════════════════════════════════════════════════
# Finds related topics/themes based on embedding similarity.
# Uses the FAISS index to find diverse cluster representatives.

def expand_topic(
    seed_keyword: str,
    top_k: int = 30,
    n_topics: int = 5,
) -> list[dict]:
    """
    Finds semantically related keyword clusters that could form
    separate but related content topics.

    This is useful for:
      - Content strategy planning
      - Topic modelling for blogs
      - Finding content gaps

    Algorithm:
      1. Get top_k similar keywords via FAISS
      2. Cluster them into n_topics groups
      3. Return the most representative keyword per cluster as a topic

    Args:
        seed_keyword: Seed keyword to expand from.
        top_k       : Candidate pool size from FAISS search.
        n_topics    : Number of related topics to identify.

    Returns:
        [
            {
                "topic"   : "seo audit tools",
                "keywords": ["seo audit tools", "website audit", ...],
            },
            ...
        ]
    """
    from ml_models.keyword_engine import get_keyword_suggestions
    from sentence_transformers import SentenceTransformer

    # Get a large pool of related keywords
    candidates = get_keyword_suggestions(
        seed_keyword=seed_keyword,
        top_k=top_k,
        min_similarity=0.2,
    )

    if len(candidates) < n_topics:
        logger.warning(
            f"Only {len(candidates)} candidates found for '{seed_keyword}'. "
            f"Reducing n_topics to {len(candidates)}."
        )
        n_topics = max(1, len(candidates))

    keywords = [r["keyword"] for r in candidates]

    # Cluster the candidates
    clusters = cluster_keywords_with_labels(keywords, n_clusters=n_topics)

    return [
        {
            "topic": c["label"],
            "keywords": c["keywords"],
            "size": c["size"],
        }
        for c in clusters
    ]


# ══════════════════════════════════════════════════════════════
# CONVENIENCE: Full keyword analysis pipeline
# ══════════════════════════════════════════════════════════════

def full_keyword_analysis(seed_keyword: str) -> dict:
    """
    Runs the complete keyword analysis pipeline for a seed keyword.

    Returns:
        {
            "seed"         : "seo tools",
            "intent"       : {"intent": "commercial", ...},
            "suggestions"  : ["best seo tools", ...],
            "long_tail"    : {"how_to": [...], "commercial": [...]},
            "topics"       : [{"topic": "...", "keywords": [...]}, ...]
        }
    """
    from ml_models.keyword_engine import get_suggestions_simple

    return {
        "seed"        : seed_keyword,
        "intent"      : classify_keyword_intent(seed_keyword),
        "suggestions" : get_suggestions_simple(seed_keyword, top_k=10),
        "long_tail"   : generate_long_tail_keywords(seed_keyword),
        "topics"      : expand_topic(seed_keyword, top_k=20, n_topics=4),
    }