"""
==============================================================
STEP 5: KEYWORD SUGGESTION ENGINE
==============================================================
This is the core inference module.

Responsibilities:
  - Load trained FAISS index + keyword list (once, at startup)
  - Accept a user-supplied seed keyword
  - Encode it using the same Sentence Transformer used in training
  - Search FAISS for top-K nearest neighbours
  - Return the corresponding keyword strings

Thread Safety:
  The model and index are loaded once as module-level singletons.
  SentenceTransformer.encode() is thread-safe for read operations.
  FAISS IndexFlatIP.search() is also thread-safe for reads.
  This means the Django dev server (multi-threaded) is fine.
  For production (Gunicorn workers), each worker process loads its
  own copy — no shared memory issues.
"""

import json
import logging
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer
from typing import Optional

logger = logging.getLogger(__name__)

# ── Paths (relative to this file's location) ─────────────────
_BASE_DIR          = Path(__file__).parent
FAISS_INDEX_PATH   = _BASE_DIR / "faiss_index.bin"
KEYWORDS_JSON_PATH = _BASE_DIR / "keywords.json"
MODEL_NAME         = "all-MiniLM-L6-v2"

# ── Module-level singletons (loaded once per process) ─────────
# These are intentionally global so Django can reuse them across
# all HTTP requests without re-loading from disk each time.
_model: Optional[SentenceTransformer] = None
_index: Optional[faiss.Index] = None
_keywords: Optional[list[str]] = None


def _load_resources() -> None:
    """
    Loads model, FAISS index, and keyword list into module globals.

    This is called lazily on the first request, or eagerly via
    preload_model() at application startup (recommended).

    Using globals here is intentional — it's the standard Django
    pattern for expensive singleton resources (similar to database
    connection pooling).
    """
    global _model, _index, _keywords

    if _model is None:
        logger.info(f"Loading SentenceTransformer model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Model loaded successfully.")

    if _index is None:
        if not FAISS_INDEX_PATH.exists():
            raise FileNotFoundError(
                f"FAISS index not found at {FAISS_INDEX_PATH}. "
                "Run ml_models/train_model.py first."
            )

        # Guard against empty/corrupt file — prevents the cryptic
        # "read error: 0 != 1" crash from FAISS's internal reader.
        index_size = FAISS_INDEX_PATH.stat().st_size
        if index_size == 0:
            raise RuntimeError(
                f"FAISS index file is empty (0 bytes): {FAISS_INDEX_PATH}\n"
                "The training pipeline did not complete successfully.\n"
                "Delete the file and re-run train_model.py."
            )

        logger.info(f"Loading FAISS index from: {FAISS_INDEX_PATH} "
                    f"({index_size / (1024 * 1024):.2f} MB)")
        _index = faiss.read_index(str(FAISS_INDEX_PATH))
        logger.info(f"FAISS index loaded. Vectors: {_index.ntotal:,}")

    if _keywords is None:
        if not KEYWORDS_JSON_PATH.exists():
            raise FileNotFoundError(
                f"Keywords JSON not found at {KEYWORDS_JSON_PATH}. "
                "Run ml_models/train_model.py first."
            )
        logger.info(f"Loading keywords from: {KEYWORDS_JSON_PATH}")
        with open(KEYWORDS_JSON_PATH, "r", encoding="utf-8") as f:
            _keywords = json.load(f)
        logger.info(f"Keywords loaded: {len(_keywords):,}")


def preload_model() -> None:
    """
    Eagerly loads all ML resources.

    Call this in your Django AppConfig.ready() to warm up the model
    at server startup rather than on the first request.

    Example (seo_tool/apps.py):
        from django.apps import AppConfig

        class SeoToolConfig(AppConfig):
            name = "seo_tool"

            def ready(self):
                from ml_models.keyword_engine import preload_model
                preload_model()
    """
    logger.info("Preloading keyword suggestion model...")
    _load_resources()
    logger.info("Keyword suggestion model preloaded successfully.")


def get_keyword_suggestions(
    seed_keyword: str,
    top_k: int = 10,
    min_similarity: float = 0.0,
    exclude_seed: bool = True,
) -> list[dict]:
    """
    Returns the top-K most semantically similar keywords.

    ALGORITHM:
      1. Normalize the seed keyword (lowercase, strip)
      2. Encode it using the SentenceTransformer → 384-dim vector
      3. L2-normalize the vector (matches training normalization)
      4. Search FAISS for top-(top_k + buffer) nearest neighbours
         using inner product (= cosine similarity for normalized vecs)
      5. Filter: remove the seed itself, apply min_similarity threshold
      6. Return top_k results with similarity scores

    Args:
        seed_keyword   : Input keyword from the user (e.g., "seo tools").
        top_k          : Number of suggestions to return (default: 10).
        min_similarity : Minimum cosine similarity score [0.0 – 1.0].
                         Use 0.3–0.5 for tighter relevance filtering.
        exclude_seed   : If True, exclude the exact seed from results.

    Returns:
        List of dicts: [{"keyword": "...", "similarity": 0.92}, ...]
        Sorted by similarity descending.

    Raises:
        FileNotFoundError: If model artifacts are missing.
        RuntimeError     : If FAISS index file is empty or corrupt.
        ValueError       : If seed_keyword is empty.
    """
    if not seed_keyword or not seed_keyword.strip():
        raise ValueError("seed_keyword must be a non-empty string.")

    # Lazy-load resources (no-op if already loaded)
    _load_resources()

    seed = seed_keyword.strip().lower()
    logger.debug(f"Generating suggestions for: '{seed}'")

    # ── Encode the query keyword ──────────────────────────────
    # We encode in a list because the model expects an iterable.
    # normalize_embeddings=True ensures L2-normalized output,
    # matching the normalization used during training.
    query_vec = _model.encode(
        [seed],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    # ── Search FAISS ──────────────────────────────────────────
    # We fetch top_k * 3 candidates to have buffer for filtering.
    search_k = min(top_k * 3 + 1, _index.ntotal)
    scores, indices = _index.search(query_vec, search_k)

    # scores and indices are 2D arrays (1, search_k) — flatten them
    scores  = scores[0]
    indices = indices[0]

    # ── Build results with filtering ─────────────────────────
    results = []
    for score, idx in zip(scores, indices):
        if idx == -1:           # FAISS returns -1 for invalid indices
            continue

        keyword = _keywords[idx]

        if exclude_seed and keyword == seed:
            continue

        if float(score) < min_similarity:
            continue

        results.append({
            "keyword": keyword,
            "similarity": round(float(score), 4)
        })

        if len(results) >= top_k:
            break

    logger.debug(f"Found {len(results)} suggestions for '{seed}'")
    return results


def get_suggestions_simple(seed_keyword: str, top_k: int = 10) -> list[str]:
    """
    Simplified wrapper that returns only keyword strings (no scores).

    This is the format used by the Django API response.

    Args:
        seed_keyword: Input keyword string.
        top_k       : Number of suggestions.

    Returns:
        List of keyword strings, e.g.:
        ["best seo tools", "free seo tools", "seo tools comparison"]
    """
    results = get_keyword_suggestions(seed_keyword, top_k=top_k)
    return [r["keyword"] for r in results]


# ── Optional: Batch suggestions ───────────────────────────────
def get_batch_suggestions(
    seed_keywords: list[str],
    top_k: int = 10,
) -> dict[str, list[str]]:
    """
    Generates suggestions for multiple keywords in a single model call.

    Encoding is done in one batch (much faster than calling
    get_suggestions_simple() in a loop).

    Args:
        seed_keywords: List of seed keyword strings.
        top_k        : Number of suggestions per seed.

    Returns:
        Dict mapping each seed → list of suggestions.
    """
    _load_resources()

    seeds = [kw.strip().lower() for kw in seed_keywords if kw.strip()]
    if not seeds:
        return {}

    # Batch encode all seeds at once
    query_vecs = _model.encode(
        seeds,
        normalize_embeddings=True,
        convert_to_numpy=True,
        batch_size=64,
    ).astype(np.float32)

    search_k = min(top_k * 3 + 1, _index.ntotal)
    all_scores, all_indices = _index.search(query_vecs, search_k)

    output = {}
    for i, seed in enumerate(seeds):
        suggestions = []
        for score, idx in zip(all_scores[i], all_indices[i]):
            if idx == -1:
                continue
            kw = _keywords[idx]
            if kw != seed:
                suggestions.append(kw)
            if len(suggestions) >= top_k:
                break
        output[seed] = suggestions

    return output