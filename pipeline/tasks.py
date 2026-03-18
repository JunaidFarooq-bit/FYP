"""
pipeline/tasks.py
==================
Celery tasks for automated, scheduled training and data collection.

SETUP:
  pip install celery celery[redis] django-celery-beat

  In settings.py:
    INSTALLED_APPS += ["django_celery_beat", "django_celery_results"]
    CELERY_BROKER_URL = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TASK_SERIALIZER = "json"

  Create celery.py in your project root (see bottom of this file).

SCHEDULE (defined in settings.py or via Django admin):
  ┌────────────────────────────────┬──────────────────┬─────────────────────┐
  │ Task                           │ Schedule         │ Why                 │
  ├────────────────────────────────┼──────────────────┼─────────────────────┤
  │ collect_trends_task            │ Every 6 hours    │ Fresh autocomplete  │
  │ run_incremental_training_task  │ Every 12 hours   │ Add new keywords    │
  │ run_full_retrain_task          │ Weekly (Sun 2AM) │ Full quality refresh│
  │ check_and_train_task           │ Every 1 hour     │ Smart trigger       │
  └────────────────────────────────┴──────────────────┴─────────────────────┘

START WORKERS:
  celery -A your_project worker --loglevel=info
  celery -A your_project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
"""

import logging
from Project.celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# DATA COLLECTION TASKS
# ══════════════════════════════════════════════════════════════

@shared_task(
    bind=True,
    name="pipeline.collect_trends",
    max_retries=2,
    default_retry_delay=300,    # retry after 5 min on failure
    soft_time_limit=1800,       # 30 min time limit
)
def collect_trends_task(self):
    """
    Runs the full trend collection pipeline.

    Schedule: Every 6 hours via Celery Beat.

    Collects from:
      - Google Autocomplete (for all top keywords in DB)
      - Google Trends (rising queries)
      - RSS feeds (SEO news sites)
    """
    logger.info(f"[Task: collect_trends] Starting at {timezone.now()}")
    try:
        from pipeline.trend_collector import TrendCollector
        collector = TrendCollector()
        stats = collector.collect_all()

        logger.info(f"[Task: collect_trends] Done. Stats: {stats}")
        return stats

    except Exception as exc:
        logger.error(f"[Task: collect_trends] Failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="pipeline.collect_autocomplete_only",
    soft_time_limit=900,        # 15 min
)
def collect_autocomplete_task(self, seeds: list[str] = None):
    """
    Runs autocomplete collection only (lighter than full collect_all).

    Can be triggered manually with specific seeds:
        collect_autocomplete_task.delay(seeds=["ai seo", "sge seo"])

    Schedule: Every 3 hours (alternates with full collection).
    """
    from pipeline.trend_collector import TrendCollector
    collector = TrendCollector()
    new_count = collector.collect_autocomplete(seeds=seeds)
    return {"new_keywords": new_count}


# ══════════════════════════════════════════════════════════════
# TRAINING TASKS
# ══════════════════════════════════════════════════════════════

@shared_task(
    bind=True,
    name="pipeline.incremental_training",
    max_retries=1,
    soft_time_limit=600,        # 10 min — incremental should be fast
)
def run_incremental_training_task(self):
    """
    Runs incremental training — adds new keywords to existing index.

    Schedule: Every 12 hours via Celery Beat.
    Also triggered automatically when new keyword count exceeds threshold.
    """
    logger.info(f"[Task: incremental_training] Starting at {timezone.now()}")
    try:
        from pipeline.incremental_trainer import IncrementalTrainer
        trainer = IncrementalTrainer()
        run = trainer.run_incremental()

        result = {
            "run_id"          : run.pk,
            "status"          : run.status,
            "keywords_count"  : run.keywords_count,
            "new_keywords"    : run.new_keywords_added,
            "duration_seconds": run.duration_seconds,
        }
        logger.info(f"[Task: incremental_training] Done: {result}")
        return result

    except Exception as exc:
        logger.error(f"[Task: incremental_training] Failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="pipeline.full_retrain",
    max_retries=1,
    soft_time_limit=3600,       # 1 hour for large keyword sets
)
def run_full_retrain_task(self):
    """
    Runs a complete rebuild of the FAISS index from all DB keywords.

    Schedule: Weekly (Sunday 2 AM) via Celery Beat.
    Also triggerable manually from the Django admin.

    This is heavier but ensures:
      - Dead/stale keywords are pruned
      - Re-encoding with latest model weights (if you ever swap models)
      - Clean index without fragmentation
    """
    logger.info(f"[Task: full_retrain] Starting full retrain at {timezone.now()}")
    try:
        from pipeline.incremental_trainer import IncrementalTrainer
        from keyword_suggestion.models import ModelTrainingRun
        trainer = IncrementalTrainer()
        run = trainer.run_full_retrain(
            trigger=ModelTrainingRun.TriggerType.SCHEDULED
        )

        result = {
            "run_id"          : run.pk,
            "status"          : run.status,
            "keywords_count"  : run.keywords_count,
            "duration_seconds": run.duration_seconds,
        }
        logger.info(f"[Task: full_retrain] Done: {result}")
        return result

    except Exception as exc:
        logger.error(f"[Task: full_retrain] Failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    name="pipeline.check_and_train",
    soft_time_limit=60,
)
def check_and_train_task():
    """
    Smart check: only trains if conditions warrant it.

    Runs every hour and decides:
      - Skip  → not enough new keywords, and not weekly retrain time
      - Incremental → enough new keywords
      - Full  → weekly schedule due

    This is the "set and forget" task — schedule it hourly and
    it handles all training decisions automatically.
    """
    from pipeline.incremental_trainer import IncrementalTrainer
    trainer = IncrementalTrainer()
    run = trainer.run_if_needed()

    if run is None:
        return {"action": "skipped", "reason": "insufficient new keywords"}

    return {
        "action"  : "trained",
        "run_id"  : run.pk,
        "status"  : run.status,
        "keywords": run.keywords_count,
    }


# ══════════════════════════════════════════════════════════════
# CELERY BEAT SCHEDULE (add to settings.py)
# ══════════════════════════════════════════════════════════════
"""
Add this to your settings.py:

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Collect fresh keyword trends every 6 hours
    "collect-trends-every-6h": {
        "task": "pipeline.collect_trends",
        "schedule": crontab(minute=0, hour="*/6"),
    },

    # Smart training check every hour
    "check-and-train-hourly": {
        "task": "pipeline.check_and_train",
        "schedule": crontab(minute=30),   # runs at :30 of every hour
    },

    # Guaranteed full retrain every Sunday at 2 AM
    "full-retrain-weekly": {
        "task": "pipeline.full_retrain",
        "schedule": crontab(minute=0, hour=2, day_of_week="sunday"),
    },
}
"""


# ══════════════════════════════════════════════════════════════
# celery.py — put this in your project root (e.g., myproject/celery.py)
# ══════════════════════════════════════════════════════════════
"""
# myproject/celery.py

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

app = Celery("myproject")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks in all installed apps
app.autodiscover_tasks()
"""

# ══════════════════════════════════════════════════════════════
# myproject/__init__.py — add this to load Celery at startup
# ══════════════════════════════════════════════════════════════
"""
# myproject/__init__.py

from .celery import app as celery_app
__all__ = ("celery_app",)
"""