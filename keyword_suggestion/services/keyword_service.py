"""
seo_tool/services/keyword_service.py
=====================================
Service layer between the Django view and the ML engine.

Why a service layer?
  - Keeps views thin (no business logic in views)
  - Makes the ML engine swappable / testable in isolation
  - Centralises input validation and error handling
  - Easy to add caching, logging, or DB persistence here
"""

import logging
from django.core.cache import cache
from ml_models.keyword_engine import get_keyword_suggestions, get_batch_suggestions

logger = logging.getLogger(__name__)

# ── Cache Configuration ───────────────────────────────────────
# Django's cache.get/set uses your CACHES backend (default: LocMemCache).
# For production, use Redis: pip install django-redis
# Then in settings.py:
#   CACHES = {
#       "default": {
#           "BACKEND": "django_redis.cache.RedisCache",
#           "LOCATION": "redis://127.0.0.1:6379/1",
#       }
#   }
CACHE_TIMEOUT_SECONDS = 60 * 60 * 24   # 24 hours — keywords don't change often
CACHE_PREFIX = "kw_suggest:"


class KeywordSuggestionService:
    """
    High-level service for keyword suggestions.

    Usage:
        service = KeywordSuggestionService()
        result  = service.suggest("seo tools")
        # → {"suggestions": [...], "count": 10, "cached": False}
    """

    def __init__(self, top_k: int = 10, use_cache: bool = True):
        """
        Args:
            top_k     : Number of suggestions to return.
            use_cache : Whether to use Django cache for results.
        """
        self.top_k = top_k
        self.use_cache = use_cache

    def _cache_key(self, keyword: str) -> str:
        """Generates a normalised cache key for a keyword."""
        normalised = keyword.strip().lower().replace(" ", "_")
        return f"{CACHE_PREFIX}{normalised}:{self.top_k}"

    def suggest(self, keyword: str) -> dict:
        """
        Returns keyword suggestions for a single seed keyword.

        Response format:
            {
                "suggestions": ["best seo tools", "free seo tools", ...],
                "count": 10,
                "cached": False
            }

        Args:
            keyword: Seed keyword string from the user.

        Returns:
            Dict with suggestions list and metadata.

        Raises:
            ValueError : If keyword is empty or too long.
            RuntimeError: If the ML engine fails unexpectedly.
        """
        # ── Input validation ──────────────────────────────────
        keyword = keyword.strip()
        if not keyword:
            raise ValueError("Keyword cannot be empty.")
        if len(keyword) > 200:
            raise ValueError("Keyword must be 200 characters or fewer.")

        # ── Cache check ───────────────────────────────────────
        cache_key = self._cache_key(keyword)
        if self.use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache HIT for keyword: '{keyword}'")
                return {**cached, "cached": True}

        # ── ML engine call ────────────────────────────────────
        logger.info(f"Generating suggestions for keyword: '{keyword}'")
        try:
            results = get_keyword_suggestions(
                seed_keyword=keyword,
                top_k=self.top_k,
                min_similarity=0.2,   # filter out very weak matches
                exclude_seed=True,
            )
        except FileNotFoundError as e:
            logger.error(f"ML model not found: {e}")
            raise RuntimeError(
                "Keyword suggestion model is not available. "
                "Please contact support."
            ) from e
        except Exception as e:
            logger.error(f"ML engine error for '{keyword}': {e}", exc_info=True)
            raise RuntimeError("Failed to generate suggestions.") from e

        suggestions = [r["keyword"] for r in results]

        # ── Build response ────────────────────────────────────
        response = {
            "suggestions": suggestions,
            "count": len(suggestions),
            "keyword": keyword,
        }

        # ── Cache the result ──────────────────────────────────
        if self.use_cache:
            cache.set(cache_key, response, timeout=CACHE_TIMEOUT_SECONDS)
            logger.debug(f"Cached suggestions for '{keyword}'")

        return {**response, "cached": False}

    def suggest_with_scores(self, keyword: str) -> dict:
        """
        Like suggest(), but also includes similarity scores in the response.

        Useful for debugging or advanced UI display.

        Response format:
            {
                "suggestions": [
                    {"keyword": "best seo tools", "similarity": 0.92},
                    ...
                ],
                "keyword": "seo tools",
                "count": 10
            }
        """
        keyword = keyword.strip()
        if not keyword:
            raise ValueError("Keyword cannot be empty.")

        results = get_keyword_suggestions(
            seed_keyword=keyword,
            top_k=self.top_k,
            min_similarity=0.2,
            exclude_seed=True,
        )

        return {
            "keyword": keyword,
            "suggestions": results,
            "count": len(results),
        }

    def suggest_batch(self, keywords: list[str]) -> dict:
        """
        Generates suggestions for multiple keywords at once.

        More efficient than calling suggest() in a loop because
        the model encodes all keywords in a single batch.

        Args:
            keywords: List of seed keyword strings.

        Returns:
            Dict mapping each keyword to its suggestions list.
        """
        keywords = [kw.strip() for kw in keywords if kw.strip()]
        if not keywords:
            raise ValueError("No valid keywords provided.")
        if len(keywords) > 50:
            raise ValueError("Batch size cannot exceed 50 keywords.")

        results = get_batch_suggestions(keywords, top_k=self.top_k)
        return {"results": results, "count": len(results)}


# ── Module-level convenience instance ────────────────────────
# Import this directly in views for simplicity:
#   from seo_tool.services.keyword_service import keyword_service
#   result = keyword_service.suggest("seo tools")
keyword_service = KeywordSuggestionService(top_k=10, use_cache=True)