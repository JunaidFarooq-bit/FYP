"""
pipeline/trend_collector.py
============================
Automatically discovers NEW trending keywords and feeds them into
the database so the next training run picks them up.

Data sources:
  1. Google Autocomplete  — scrape fresh suggestions for existing seeds
  2. Google Trends API    — find rising queries in your niche
  3. User search logging  — keywords your own users search for
  4. RSS/News feeds       — SEO news sites surface new terminology
  5. Reddit/Quora         — community questions reveal new keyword patterns

SCHEDULING:
  Run this with Django's management command `python manage.py collect_trends`
  Or schedule it with Celery Beat / APScheduler / OS cron.

  Recommended schedule:
    collect_trends     → every 6 hours
    run_training       → every 12 hours (or when > 100 new keywords)
    full_retrain       → weekly (Sunday 2 AM)
"""

import logging
import re
import time
import random
import requests
import feedparser
from datetime import datetime, timedelta
from typing import Optional
from django.utils import timezone
from django.db import transaction

from keyword_suggestion.models import KeywordEntry, KeywordPair, KeywordSource, TrendSnapshot

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
}
REQUEST_DELAY   = 1.0   # seconds between requests
REQUEST_TIMEOUT = 8

# Google Trends categories relevant to SEO (for trend score context)
SEO_RELATED_TERMS = [
    "seo", "keyword research", "backlinks", "search engine optimization",
    "content marketing", "technical seo", "link building", "google analytics",
    "google search console", "on page seo", "off page seo", "local seo",
    "seo audit", "rank tracking", "serp", "domain authority",
]

# SEO news RSS feeds — new articles = new keyword patterns
SEO_RSS_FEEDS = [
    "https://www.searchenginejournal.com/feed/",
    "https://searchengineland.com/feed",
    "https://moz.com/blog/feed",
    "https://ahrefs.com/blog/feed/",
]


class TrendCollector:
    """
    Discovers and saves new trending keywords to the database.

    Call `collect_all()` to run all collection strategies,
    or call individual methods for specific sources.
    """

    def __init__(self, dry_run: bool = False):
        """
        Args:
            dry_run: If True, collect and log keywords but don't save to DB.
        """
        self.dry_run = dry_run
        self.stats = {
            "autocomplete_new": 0,
            "trends_new": 0,
            "rss_new": 0,
            "total_new": 0,
        }

    # ──────────────────────────────────────────────────────────
    # 1. GOOGLE AUTOCOMPLETE REFRESH
    # ──────────────────────────────────────────────────────────

    def collect_autocomplete(
        self,
        seeds: Optional[list[str]] = None,
        use_db_seeds: bool = True,
    ) -> int:
        """
        Re-scrapes Google Autocomplete for all seed keywords.

        This is the primary source of fresh keyword data. Google's
        autocomplete reflects real-time search trends — new queries
        appear here within days of trending.

        Args:
            seeds       : Explicit seed list. If None, uses `use_db_seeds`.
            use_db_seeds: If True, seeds are pulled from the DB
                          (top keywords by trend_score).

        Returns:
            Number of new keyword pairs discovered.
        """
        if seeds is None and use_db_seeds:
            # Use top trending keywords as seeds to discover variations
            seeds = list(
                KeywordEntry.objects.filter(is_active=True)
                .order_by("-trend_score", "-times_searched")
                .values_list("keyword", flat=True)[:100]  # top 100 seeds
            )

        if not seeds:
            seeds = SEO_RELATED_TERMS
            logger.warning("No DB seeds found, using hardcoded SEO terms.")

        new_count = 0
        logger.info(f"Collecting autocomplete for {len(seeds)} seeds...")

        for i, seed in enumerate(seeds):
            try:
                pairs = self._fetch_autocomplete_pairs(seed)
                saved = self._save_keyword_pairs(pairs, source=KeywordSource.AUTOCOMPLETE)
                new_count += saved

                # Rate limiting with jitter
                time.sleep(REQUEST_DELAY + random.uniform(0, 0.5))

                if (i + 1) % 20 == 0:
                    logger.info(f"  Progress: {i+1}/{len(seeds)} seeds, {new_count} new pairs so far")

            except Exception as e:
                logger.warning(f"  Autocomplete failed for '{seed}': {e}")
                continue

        self.stats["autocomplete_new"] = new_count
        logger.info(f"Autocomplete collection done. New pairs: {new_count}")
        return new_count

    def _fetch_autocomplete_pairs(self, seed: str) -> list[tuple[str, str]]:
        """
        Fetches Google Autocomplete suggestions for a seed.

        Returns list of (seed, suggestion) tuples.
        Also queries "seed a" through "seed z" for more coverage.
        """
        pairs = []
        queries = [seed] + [f"{seed} {c}" for c in "abcdefghijklmnopqrstuvwxyz"]

        for query in queries:
            try:
                url = "https://suggestqueries.google.com/complete/search"
                resp = requests.get(
                    url,
                    params={"client": "firefox", "q": query, "hl": "en", "gl": "us"},
                    headers=REQUEST_HEADERS,
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                import json
                data = json.loads(resp.text)
                suggestions = data[1] if len(data) > 1 else []

                for s in suggestions:
                    s = s.strip().lower()
                    if s and s != seed:
                        pairs.append((seed, s))

                time.sleep(0.3)  # short delay between alphabet queries

            except Exception:
                continue

        return pairs

    # ──────────────────────────────────────────────────────────
    # 2. GOOGLE TRENDS (pytrends)
    # ──────────────────────────────────────────────────────────

    def collect_google_trends(
        self,
        keywords: Optional[list[str]] = None,
        timeframe: str = "now 7-d",
    ) -> int:
        """
        Fetches trend scores and rising queries from Google Trends.

        Uses the `pytrends` library (pip install pytrends).

        What this does:
          - Updates trend_score on existing KeywordEntry records
          - Discovers "related queries" which are new keyword opportunities
          - Saves trend snapshots for historical tracking

        Args:
            keywords : Keywords to check trends for.
                       Defaults to top DB keywords.
            timeframe: Google Trends timeframe string.
                       "now 7-d" = last 7 days
                       "today 3-m" = last 3 months
                       "today 12-m" = last year

        Returns:
            Number of new trending keywords discovered.
        """
        try:
            from pytrends.request import TrendReq
        except ImportError:
            logger.warning(
                "pytrends not installed. Run: pip install pytrends\n"
                "Skipping Google Trends collection."
            )
            return 0

        if keywords is None:
            keywords = list(
                KeywordEntry.objects.filter(is_active=True)
                .order_by("-times_searched")
                .values_list("keyword", flat=True)[:50]
            )

        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        new_count = 0

        # Google Trends API processes max 5 keywords per request
        for i in range(0, len(keywords), 5):
            batch = keywords[i:i+5]
            try:
                pytrends.build_payload(batch, timeframe=timeframe, geo="US")

                # Interest over time → update trend_score
                interest_df = pytrends.interest_over_time()
                if not interest_df.empty:
                    for kw in batch:
                        if kw in interest_df.columns:
                            avg_score = float(interest_df[kw].mean())
                            self._update_trend_score(kw, avg_score)

                # Related queries → new keyword opportunities
                related = pytrends.related_queries()
                for kw in batch:
                    if kw not in related:
                        continue

                    # "rising" queries = trending NOW (high value!)
                    rising_df = related[kw].get("rising")
                    if rising_df is not None and not rising_df.empty:
                        for _, row in rising_df.iterrows():
                            related_kw = str(row.get("query", "")).strip().lower()
                            if related_kw:
                                pairs = [(kw, related_kw)]
                                saved = self._save_keyword_pairs(
                                    pairs, source=KeywordSource.TREND_FEED
                                )
                                new_count += saved

                time.sleep(2)  # Google Trends rate limits aggressively

            except Exception as e:
                logger.warning(f"Trends batch failed ({batch}): {e}")
                time.sleep(5)
                continue

        self.stats["trends_new"] = new_count
        logger.info(f"Google Trends collection done. New keywords: {new_count}")
        return new_count

    def _update_trend_score(self, keyword: str, score: float) -> None:
        """Updates the trend score for an existing keyword in the DB."""
        if self.dry_run:
            return
        try:
            entry, created = KeywordEntry.objects.get_or_create(
                keyword=keyword,
                defaults={"source": KeywordSource.TREND_FEED, "trend_score": score}
            )
            if not created:
                entry.trend_score = score
                entry.last_trend_check = timezone.now()
                entry.save(update_fields=["trend_score", "last_trend_check"])

            # Save historical snapshot
            TrendSnapshot.objects.update_or_create(
                keyword=entry,
                snapshot_date=timezone.now().date(),
                source="google_trends",
                defaults={"trend_score": score},
            )
        except Exception as e:
            logger.warning(f"Failed to update trend score for '{keyword}': {e}")

    # ──────────────────────────────────────────────────────────
    # 3. RSS / NEWS FEED COLLECTION
    # ──────────────────────────────────────────────────────────

    def collect_from_rss(self, feeds: Optional[list[str]] = None) -> int:
        """
        Extracts keywords from SEO news article titles and descriptions.

        SEO news articles surface new terminology early — if "AI Overviews"
        starts appearing in Moz/SEJ titles, it'll trend as a keyword soon.

        Uses simple regex-based noun phrase extraction. For production,
        consider spaCy for proper NLP extraction.

        Args:
            feeds: RSS feed URLs. Defaults to SEO_RSS_FEEDS.

        Returns:
            Number of new keywords discovered.
        """
        if feeds is None:
            feeds = SEO_RSS_FEEDS

        new_count = 0
        seed = "seo"  # default seed for RSS-sourced keywords

        for feed_url in feeds:
            try:
                logger.info(f"  Parsing RSS: {feed_url}")
                feed = feedparser.parse(feed_url)

                for entry in feed.entries[:20]:  # newest 20 articles
                    # Combine title + summary for extraction
                    text = f"{entry.get('title', '')} {entry.get('summary', '')}"
                    keywords = self._extract_seo_phrases(text)

                    for kw in keywords:
                        pairs = [(seed, kw)]
                        saved = self._save_keyword_pairs(
                            pairs, source=KeywordSource.MANUAL
                        )
                        new_count += saved

                time.sleep(1)

            except Exception as e:
                logger.warning(f"  RSS feed failed ({feed_url}): {e}")
                continue

        self.stats["rss_new"] = new_count
        logger.info(f"RSS collection done. New keywords: {new_count}")
        return new_count

    def _extract_seo_phrases(self, text: str) -> list[str]:
        """
        Extracts SEO-relevant phrases from article text using regex patterns.

        For production quality, use spaCy:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(text)
            phrases = [chunk.text.lower() for chunk in doc.noun_chunks
                       if 2 <= len(chunk.text.split()) <= 5]

        Returns:
            List of extracted keyword phrases (2-5 words).
        """
        text = text.lower()
        # Remove HTML
        text = re.sub(r"<[^>]+>", " ", text)
        # Remove non-alpha chars (keep spaces)
        text = re.sub(r"[^a-z\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        words = text.split()
        phrases = []

        # Extract 2-4 word n-grams that contain SEO-related anchor words
        seo_anchors = {
            "seo", "search", "keyword", "rank", "backlink", "content",
            "google", "traffic", "organic", "serp", "optimization",
            "analytics", "crawl", "index", "link", "page", "site",
        }

        for n in (2, 3, 4):
            for i in range(len(words) - n + 1):
                phrase_words = words[i:i+n]
                phrase = " ".join(phrase_words)

                # At least one SEO anchor word in the phrase
                if any(anchor in phrase_words for anchor in seo_anchors):
                    # Basic quality filters
                    if 8 <= len(phrase) <= 60:
                        phrases.append(phrase)

        return list(set(phrases))[:20]  # deduplicate, limit to 20 per article

    # ──────────────────────────────────────────────────────────
    # 4. LOG USER SEARCHES
    # ──────────────────────────────────────────────────────────

    def log_user_search(self, keyword: str) -> None:
        """
        Records a keyword that a user searched for in your tool.

        Call this in your suggestion view every time a search is made.
        User searches are the HIGHEST QUALITY signal because they
        reflect exactly what your users care about right now.

        Example in views.py:
            from pipeline.trend_collector import TrendCollector
            collector = TrendCollector()
            collector.log_user_search(keyword)
        """
        keyword = keyword.strip().lower()
        if not keyword:
            return

        entry, created = KeywordEntry.objects.get_or_create(
            keyword=keyword,
            defaults={
                "source": KeywordSource.USER_SEARCH,
                "trend_score": 10.0,  # new user-searched keywords start with a boost
            }
        )
        entry.mark_searched()

        if created:
            logger.info(f"New user-searched keyword added to DB: '{keyword}'")

    # ──────────────────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ──────────────────────────────────────────────────────────

    def collect_all(self) -> dict:
        """
        Runs all collection strategies in sequence.

        Returns:
            Stats dict with counts per source.
        """
        logger.info("=" * 60)
        logger.info("Starting full trend collection run...")
        logger.info("=" * 60)

        self.collect_autocomplete()
        self.collect_google_trends()
        self.collect_from_rss()

        self.stats["total_new"] = sum([
            self.stats["autocomplete_new"],
            self.stats["trends_new"],
            self.stats["rss_new"],
        ])

        logger.info(f"Collection complete. Summary: {self.stats}")
        return self.stats

    # ──────────────────────────────────────────────────────────
    # DB HELPERS
    # ──────────────────────────────────────────────────────────

    def _save_keyword_pairs(
        self,
        pairs: list[tuple[str, str]],
        source: str = KeywordSource.AUTOCOMPLETE,
    ) -> int:
        """
        Saves keyword pairs to the database.

        Uses get_or_create to avoid duplicates.
        Updates co_occurrence_count if the pair already exists.

        Returns:
            Number of genuinely NEW pairs created.
        """
        if self.dry_run or not pairs:
            return 0

        new_count = 0

        with transaction.atomic():
            for seed_text, suggestion_text in pairs:
                seed_text       = seed_text.strip().lower()
                suggestion_text = suggestion_text.strip().lower()

                if not seed_text or not suggestion_text:
                    continue
                if seed_text == suggestion_text:
                    continue
                if len(seed_text) > 300 or len(suggestion_text) > 300:
                    continue

                # Upsert seed keyword
                seed_entry, _ = KeywordEntry.objects.get_or_create(
                    keyword=seed_text,
                    defaults={"source": source}
                )
                seed_entry.last_seen = timezone.now()
                seed_entry.save(update_fields=["last_seen"])

                # Upsert suggestion keyword
                sugg_entry, sugg_created = KeywordEntry.objects.get_or_create(
                    keyword=suggestion_text,
                    defaults={"source": source}
                )

                # Upsert keyword pair
                pair_obj, pair_created = KeywordPair.objects.get_or_create(
                    seed_keyword=seed_entry,
                    suggested_keyword=sugg_entry,
                )
                if not pair_created:
                    # Pair existed — increment co-occurrence count
                    pair_obj.co_occurrence_count += 1
                    pair_obj.save(update_fields=["co_occurrence_count"])
                else:
                    new_count += 1

        return new_count