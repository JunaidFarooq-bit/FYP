"""
pipeline/incremental_trainer.py
================================
The core continuous training engine.

STRATEGY: Incremental (not from scratch every time)
----------------------------------------------------
Retraining from scratch on 100K+ keywords takes ~10 minutes.
Instead we use an INCREMENTAL approach:

  1. Load existing FAISS index from disk
  2. Query DB for keywords added/updated SINCE the last training run
  3. Encode ONLY the new keywords (fast — usually < 1000)
  4. ADD new vectors to the existing FAISS index
  5. Save updated index + keyword list
  6. Hot-reload the engine WITHOUT restarting Django

This means:
  - Most retrains complete in seconds, not minutes
  - New trending keywords appear in suggestions within minutes
  - The Django server never goes down for a retrain

FULL RETRAIN (weekly):
  For data quality, run a full rebuild once a week to:
  - Re-encode all keywords with latest weights
  - Prune dead/irrelevant keywords
  - Clean up index fragmentation

The pipeline automatically decides which strategy to use.
"""

import json
import logging
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
from django.utils import timezone
from sentence_transformers import SentenceTransformer

from keyword_suggestion.models import KeywordEntry, KeywordPair, ModelTrainingRun

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────
ML_DIR = Path(__file__).parent.parent / "ml_models"

# Versioned artifact paths — we keep last 3 versions for rollback
def _artifact_path(run_id: int, filename: str) -> Path:
    versioned_dir = ML_DIR / "versions" / f"run_{run_id}"
    versioned_dir.mkdir(parents=True, exist_ok=True)
    return versioned_dir / filename

# Symlinks that always point to the active version
ACTIVE_FAISS_PATH    = ML_DIR / "faiss_index.bin"
ACTIVE_KEYWORDS_PATH = ML_DIR / "keywords.json"

# Training config
MODEL_NAME  = "all-MiniLM-L6-v2"
BATCH_SIZE  = 256
MIN_NEW_KEYWORDS_FOR_INCREMENTAL = 10    # don't retrain for fewer than this
FULL_RETRAIN_INTERVAL_DAYS       = 7     # force full retrain weekly
MAX_VERSIONS_TO_KEEP             = 3     # older versions are deleted


class IncrementalTrainer:
    """
    Manages continuous model updates.

    Usage:
        trainer = IncrementalTrainer()

        # Check if retraining is needed, then run appropriate strategy
        trainer.run_if_needed()

        # Or force a specific strategy:
        trainer.run_incremental()   # add only new keywords
        trainer.run_full_retrain()  # rebuild everything from scratch
    """

    def __init__(self):
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the embedding model (cached on self)."""
        if self._model is None:
            logger.info(f"Loading SentenceTransformer: {MODEL_NAME}")
            self._model = SentenceTransformer(MODEL_NAME)
        return self._model

    # ──────────────────────────────────────────────────────────
    # PUBLIC ENTRY POINTS
    # ──────────────────────────────────────────────────────────

    def run_if_needed(self) -> Optional[ModelTrainingRun]:
        """
        Checks conditions and runs the appropriate training strategy.

        Decision logic:
          1. If no model exists at all → full retrain
          2. If last full retrain was > 7 days ago → full retrain
          3. If >= MIN_NEW_KEYWORDS new keywords → incremental
          4. Otherwise → skip (nothing meaningful changed)

        Returns:
            The ModelTrainingRun record, or None if skipped.
        """
        last_run = ModelTrainingRun.objects.filter(
            status=ModelTrainingRun.Status.SUCCESS
        ).order_by("-completed_at").first()

        # No successful run ever → full retrain
        if last_run is None or not ACTIVE_FAISS_PATH.exists():
            logger.info("No existing model found. Running full retrain.")
            return self.run_full_retrain()

        # Time since last full retrain
        days_since_full = None
        last_full = ModelTrainingRun.objects.filter(
            status=ModelTrainingRun.Status.SUCCESS,
            trigger__in=[
                ModelTrainingRun.TriggerType.SCHEDULED,
                ModelTrainingRun.TriggerType.MANUAL,
            ]
        ).order_by("-completed_at").first()
        if last_full and last_full.completed_at:
            days_since_full = (timezone.now() - last_full.completed_at).days

        if days_since_full is not None and days_since_full >= FULL_RETRAIN_INTERVAL_DAYS:
            logger.info(f"Full retrain due — {days_since_full} days since last full run.")
            return self.run_full_retrain(trigger=ModelTrainingRun.TriggerType.SCHEDULED)

        # Count new keywords since last run
        since = last_run.completed_at or (timezone.now() - timedelta(hours=24))
        new_count = KeywordEntry.objects.filter(
            is_active=True,
            first_seen__gte=since
        ).count()

        if new_count < MIN_NEW_KEYWORDS_FOR_INCREMENTAL:
            logger.info(f"Only {new_count} new keywords since last run — skipping.")
            return None

        logger.info(f"{new_count} new keywords since last run — running incremental update.")
        return self.run_incremental(since=since)

    def run_full_retrain(
        self,
        trigger: str = ModelTrainingRun.TriggerType.MANUAL
    ) -> ModelTrainingRun:
        """
        Encodes ALL active keywords and builds a brand new FAISS index.

        Use this:
          - On first run
          - Weekly (scheduled)
          - After bulk importing a large new dataset
          - After pruning/cleaning the keyword database
        """
        run = ModelTrainingRun.objects.create(
            status=ModelTrainingRun.Status.RUNNING,
            trigger=trigger,
            started_at=timezone.now(),
            model_name=MODEL_NAME,
        )
        logger.info(f"[Run #{run.pk}] Starting FULL retrain...")

        try:
            # Load all active keywords from DB
            keywords = list(
                KeywordEntry.objects.filter(is_active=True)
                .order_by("-trend_score", "-times_searched")
                .values_list("keyword", flat=True)
            )

            if not keywords:
                raise ValueError("No active keywords in the database.")

            logger.info(f"[Run #{run.pk}] Encoding {len(keywords):,} keywords...")
            embeddings = self._encode(keywords)

            # Build fresh FAISS index
            index = self._build_index(embeddings)

            # Save versioned artifacts
            self._save_artifacts(run, index, keywords, embeddings)

            # Activate this run
            self._activate_run(run, keywords, embeddings)

            # Hot-reload the engine (no server restart needed!)
            self._hot_reload_engine()

            # Prune old versions
            self._prune_old_versions()

            logger.info(f"[Run #{run.pk}] Full retrain complete. {len(keywords):,} keywords.")
            return run

        except Exception as e:
            run.status = ModelTrainingRun.Status.FAILED
            run.error_message = str(e)
            run.completed_at = timezone.now()
            run.save()
            logger.error(f"[Run #{run.pk}] Full retrain FAILED: {e}", exc_info=True)
            raise

    def run_incremental(
        self,
        since: Optional[datetime] = None,
        trigger: str = ModelTrainingRun.TriggerType.THRESHOLD,
    ) -> ModelTrainingRun:
        """
        Adds ONLY new keywords to the existing FAISS index.

        Much faster than full retrain — typically completes in seconds.

        How it works:
          1. Load existing index + keyword list from disk
          2. Find keywords added to DB since 'since' datetime
          3. Encode only those new keywords
          4. Append new vectors to the index (faiss.add)
          5. Save updated index + extended keyword list

        Args:
            since: Only process keywords added after this datetime.
                   Defaults to 24 hours ago.
        """
        if since is None:
            since = timezone.now() - timedelta(hours=24)

        run = ModelTrainingRun.objects.create(
            status=ModelTrainingRun.Status.RUNNING,
            trigger=trigger,
            started_at=timezone.now(),
            model_name=MODEL_NAME,
        )
        logger.info(f"[Run #{run.pk}] Starting INCREMENTAL update since {since}...")

        try:
            # Load existing artifacts
            if not ACTIVE_FAISS_PATH.exists() or not ACTIVE_KEYWORDS_PATH.exists():
                logger.warning("No existing index found. Falling back to full retrain.")
                run.delete()
                return self.run_full_retrain(trigger=trigger)

            index = faiss.read_index(str(ACTIVE_FAISS_PATH))
            with open(ACTIVE_KEYWORDS_PATH, "r", encoding="utf-8") as f:
                existing_keywords = json.load(f)

            existing_set = set(existing_keywords)

            # Find new keywords not yet in the index
            new_keywords = list(
                KeywordEntry.objects.filter(
                    is_active=True,
                    first_seen__gte=since,
                )
                .exclude(keyword__in=existing_set)
                .values_list("keyword", flat=True)
            )

            if not new_keywords:
                logger.info(f"[Run #{run.pk}] No new keywords to add. Skipping.")
                run.status = ModelTrainingRun.Status.SUCCESS
                run.completed_at = timezone.now()
                run.notes = "Skipped — no new keywords."
                run.save()
                return run

            logger.info(f"[Run #{run.pk}] Encoding {len(new_keywords):,} new keywords...")
            new_embeddings = self._encode(new_keywords)

            # Append to existing index
            index.add(new_embeddings)

            # Extend keyword list
            updated_keywords = existing_keywords + new_keywords

            # Save updated artifacts
            self._save_artifacts(run, index, updated_keywords, new_embeddings)
            self._activate_run(run, updated_keywords, new_embeddings, is_incremental=True)

            # Hot-reload
            self._hot_reload_engine()

            logger.info(
                f"[Run #{run.pk}] Incremental update complete. "
                f"+{len(new_keywords)} new keywords. "
                f"Total: {len(updated_keywords):,}."
            )
            return run

        except Exception as e:
            run.status = ModelTrainingRun.Status.FAILED
            run.error_message = str(e)
            run.completed_at = timezone.now()
            run.save()
            logger.error(f"[Run #{run.pk}] Incremental update FAILED: {e}", exc_info=True)
            raise

    # ──────────────────────────────────────────────────────────
    # ROLLBACK
    # ──────────────────────────────────────────────────────────

    def rollback_to_previous(self) -> bool:
        """
        Rolls back to the last successful training run.

        Use this if a retrain introduced bad suggestions.

        Returns:
            True if rollback succeeded, False otherwise.
        """
        runs = ModelTrainingRun.objects.filter(
            status=ModelTrainingRun.Status.SUCCESS,
            is_active=False,
        ).order_by("-completed_at")[:2]

        if not runs:
            logger.error("No previous successful run to roll back to.")
            return False

        target_run = runs[0]

        if not Path(target_run.faiss_index_path).exists():
            logger.error(f"Artifact file missing for run #{target_run.pk}")
            return False

        logger.info(f"Rolling back to run #{target_run.pk}...")

        # Copy old artifacts to active paths
        shutil.copy2(target_run.faiss_index_path, ACTIVE_FAISS_PATH)
        shutil.copy2(target_run.keywords_json_path, ACTIVE_KEYWORDS_PATH)

        # Update DB state
        current_active = ModelTrainingRun.objects.filter(is_active=True).first()
        if current_active:
            current_active.status = ModelTrainingRun.Status.ROLLED_BACK
            current_active.is_active = False
            current_active.save()

        target_run.mark_active()

        # Hot-reload with rolled-back artifacts
        self._hot_reload_engine()

        logger.info(f"Rollback to run #{target_run.pk} successful.")
        return True

    # ──────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ──────────────────────────────────────────────────────────

    def _encode(self, keywords: list[str]) -> np.ndarray:
        """Encodes keywords to L2-normalized float32 embeddings."""
        embeddings = self.model.encode(
            keywords,
            batch_size=BATCH_SIZE,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,   # cosine sim = dot product
        )
        return embeddings.astype(np.float32)

    def _build_index(self, embeddings: np.ndarray) -> faiss.Index:
        """Builds a fresh FAISS inner-product index."""
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)
        return index

    def _save_artifacts(
        self,
        run: ModelTrainingRun,
        index: faiss.Index,
        keywords: list[str],
        embeddings: np.ndarray,
    ) -> None:
        """Saves versioned artifacts for this training run."""
        faiss_path      = _artifact_path(run.pk, "faiss_index.bin")
        keywords_path   = _artifact_path(run.pk, "keywords.json")
        embeddings_path = _artifact_path(run.pk, "keyword_embeddings.npy")

        faiss.write_index(index, str(faiss_path))
        with open(keywords_path, "w", encoding="utf-8") as f:
            json.dump(keywords, f, ensure_ascii=False)
        np.save(embeddings_path, embeddings)

        run.faiss_index_path   = str(faiss_path)
        run.keywords_json_path = str(keywords_path)
        run.embeddings_path    = str(embeddings_path)
        run.save(update_fields=["faiss_index_path", "keywords_json_path", "embeddings_path"])

    def _activate_run(
        self,
        run: ModelTrainingRun,
        keywords: list[str],
        embeddings: np.ndarray,
        is_incremental: bool = False,
    ) -> None:
        """Updates the active symlinks and DB state."""
        # Copy artifacts to the active paths (overwrites previous)
        shutil.copy2(run.faiss_index_path, ACTIVE_FAISS_PATH)
        shutil.copy2(run.keywords_json_path, ACTIVE_KEYWORDS_PATH)

        run.status         = ModelTrainingRun.Status.SUCCESS
        run.keywords_count = len(keywords)
        run.new_keywords_added = len(keywords) if not is_incremental else len(keywords)
        run.embedding_dim  = embeddings.shape[1]
        run.completed_at   = timezone.now()
        run.save()

        run.mark_active()   # deactivates all previous runs in one query

    def _hot_reload_engine(self) -> None:
        """
        Reloads the FAISS index and keyword list in the running engine
        WITHOUT restarting the Django server.

        This works because keyword_engine.py uses module-level globals.
        We simply replace them with the new data.
        """
        try:
            import ml_models.keyword_engine as engine

            logger.info("Hot-reloading keyword engine...")
            engine._index    = faiss.read_index(str(ACTIVE_FAISS_PATH))
            with open(ACTIVE_KEYWORDS_PATH, "r", encoding="utf-8") as f:
                engine._keywords = json.load(f)
            # Note: we don't reload the model itself — it hasn't changed

            logger.info(
                f"Engine hot-reloaded. "
                f"Vectors: {engine._index.ntotal:,}, "
                f"Keywords: {len(engine._keywords):,}"
            )
        except Exception as e:
            logger.error(f"Hot-reload failed: {e}. Server restart may be required.", exc_info=True)

    def _prune_old_versions(self) -> None:
        """Deletes artifact directories for old training runs."""
        versions_dir = ML_DIR / "versions"
        if not versions_dir.exists():
            return

        # Keep only the N most recent version directories
        version_dirs = sorted(
            [d for d in versions_dir.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )

        for old_dir in version_dirs[MAX_VERSIONS_TO_KEEP:]:
            shutil.rmtree(old_dir, ignore_errors=True)
            logger.info(f"Pruned old artifact version: {old_dir.name}")