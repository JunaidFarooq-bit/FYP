"""
seo_tool/models.py
==================
Database models for the continuous training pipeline.

Three core tables:
  1. KeywordEntry     — stores every keyword with metadata (source, trend score, etc.)
  2. KeywordPair      — stores seed→suggestion relationships (the training data)
  3. ModelTrainingRun — audit log of every training job (when, how many keywords, etc.)

This is the "living database" that grows over time as new keywords arrive
from scrapers, user searches, trend feeds, and manual imports.
"""

from django.db import models
from django.utils import timezone


class KeywordSource(models.TextChoices):
    """Where a keyword was discovered."""
    AUTOCOMPLETE   = "autocomplete",   "Google Autocomplete"
    USER_SEARCH    = "user_search",    "User Search"
    TREND_FEED     = "trend_feed",     "Google Trends / Trend Feed"
    MANUAL         = "manual",         "Manually Added"
    KEYWORD_PLANNER= "keyword_planner","Google Keyword Planner"
    KAGGLE         = "kaggle",         "Kaggle Dataset"


class KeywordIntent(models.TextChoices):
    INFORMATIONAL  = "informational",  "Informational"
    COMMERCIAL     = "commercial",     "Commercial"
    TRANSACTIONAL  = "transactional",  "Transactional"
    NAVIGATIONAL   = "navigational",   "Navigational"
    UNKNOWN        = "unknown",        "Unknown"


class KeywordEntry(models.Model):
    """
    Represents a single unique keyword in the system.

    This is the master keyword table. Every keyword — whether it's a
    seed or a suggestion — lives here. The continuous pipeline adds
    new rows over time and updates trend scores regularly.
    """
    keyword        = models.CharField(max_length=300, unique=True, db_index=True)
    source         = models.CharField(
                         max_length=30,
                         choices=KeywordSource.choices,
                         default=KeywordSource.AUTOCOMPLETE
                     )
    intent         = models.CharField(
                         max_length=20,
                         choices=KeywordIntent.choices,
                         default=KeywordIntent.UNKNOWN
                     )

    # Trend & quality signals — updated periodically by the trend scraper
    trend_score    = models.FloatField(default=0.0,  help_text="0.0–100.0 trend score from Google Trends")
    search_volume  = models.IntegerField(default=0,  help_text="Estimated monthly search volume")
    times_suggested= models.IntegerField(default=0,  help_text="How many times this was returned as a suggestion")
    times_searched = models.IntegerField(default=0,  help_text="How many times a user searched FOR this keyword")

    # Lifecycle
    is_active      = models.BooleanField(default=True, help_text="Set False to exclude from training")
    first_seen     = models.DateTimeField(default=timezone.now)
    last_seen      = models.DateTimeField(default=timezone.now)
    last_trend_check = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-trend_score", "-times_searched"]
        indexes = [
            models.Index(fields=["source"]),
            models.Index(fields=["intent"]),
            models.Index(fields=["is_active", "last_seen"]),
            models.Index(fields=["trend_score"]),
        ]

    def __str__(self):
        return f"{self.keyword} (score={self.trend_score:.1f})"

    def mark_seen(self):
        """Call this every time the keyword appears in results."""
        self.last_seen = timezone.now()
        self.times_suggested += 1
        self.save(update_fields=["last_seen", "times_suggested"])

    def mark_searched(self):
        """Call this every time a user searches for this keyword."""
        self.last_seen = timezone.now()
        self.times_searched += 1
        self.save(update_fields=["last_seen", "times_searched"])


class KeywordPair(models.Model):
    """
    A seed → suggestion relationship. This is the training data.

    Every time a new keyword pair is discovered (from autocomplete,
    user behaviour, etc.) it's inserted here. The training pipeline
    reads from this table to rebuild the FAISS index.
    """
    seed_keyword      = models.ForeignKey(
                            KeywordEntry,
                            on_delete=models.CASCADE,
                            related_name="as_seed"
                        )
    suggested_keyword = models.ForeignKey(
                            KeywordEntry,
                            on_delete=models.CASCADE,
                            related_name="as_suggestion"
                        )

    # Quality signals for this specific pair
    co_occurrence_count = models.IntegerField(default=1,
        help_text="How many times this pair has been seen together")
    relevance_score    = models.FloatField(default=0.5,
        help_text="Manual or computed relevance: 0.0 (low) to 1.0 (high)")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active  = models.BooleanField(default=True)

    class Meta:
        unique_together = ("seed_keyword", "suggested_keyword")
        ordering = ["-co_occurrence_count", "-relevance_score"]
        indexes = [
            models.Index(fields=["seed_keyword", "is_active"]),
            models.Index(fields=["co_occurrence_count"]),
        ]

    def __str__(self):
        return f"{self.seed_keyword.keyword} → {self.suggested_keyword.keyword}"


class ModelTrainingRun(models.Model):
    """
    Audit log for every training job.

    Tracks what changed, how long it took, and whether it succeeded.
    The 'is_active' flag marks which run's artifacts are currently
    being served by the keyword engine.
    """
    class Status(models.TextChoices):
        PENDING   = "pending",   "Pending"
        RUNNING   = "running",   "Running"
        SUCCESS   = "success",   "Success"
        FAILED    = "failed",    "Failed"
        ROLLED_BACK = "rolled_back", "Rolled Back"

    class TriggerType(models.TextChoices):
        SCHEDULED  = "scheduled",  "Scheduled (cron)"
        MANUAL     = "manual",     "Manually Triggered"
        THRESHOLD  = "threshold",  "New Keywords Threshold"
        API        = "api",        "API Trigger"

    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    trigger        = models.CharField(max_length=20, choices=TriggerType.choices, default=TriggerType.SCHEDULED)

    # Stats
    keywords_count     = models.IntegerField(default=0)
    new_keywords_added = models.IntegerField(default=0)
    pairs_count        = models.IntegerField(default=0)
    embedding_dim      = models.IntegerField(default=384)
    model_name         = models.CharField(max_length=100, default="all-MiniLM-L6-v2")

    # Timing
    started_at    = models.DateTimeField(null=True, blank=True)
    completed_at  = models.DateTimeField(null=True, blank=True)

    @property
    def duration_seconds(self):
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    # File paths for the artifacts produced by this run
    faiss_index_path   = models.CharField(max_length=500, blank=True)
    keywords_json_path = models.CharField(max_length=500, blank=True)
    embeddings_path    = models.CharField(max_length=500, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True)
    notes         = models.TextField(blank=True)

    # Which run is currently live
    is_active = models.BooleanField(default=False,
        help_text="True = this run's artifacts are currently loaded")

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"TrainingRun #{self.pk} [{self.status}] {self.keywords_count} keywords"

    def mark_active(self):
        """
        Marks this run as the active one and deactivates all others.
        Uses a queryset update to do it in a single DB query.
        """
        ModelTrainingRun.objects.filter(is_active=True).update(is_active=False)
        self.is_active = True
        self.save(update_fields=["is_active"])


class TrendSnapshot(models.Model):
    """
    Periodic snapshot of trend scores for keywords.

    Lets you query "what was the trend score of 'seo tools' 3 months ago?"
    and plot trend graphs in your UI.
    """
    keyword      = models.ForeignKey(KeywordEntry, on_delete=models.CASCADE, related_name="snapshots")
    trend_score  = models.FloatField()
    search_volume= models.IntegerField(default=0)
    snapshot_date= models.DateField(default=timezone.now)
    source       = models.CharField(max_length=50, default="google_trends")

    class Meta:
        unique_together = ("keyword", "snapshot_date", "source")
        ordering = ["-snapshot_date"]
        indexes = [
            models.Index(fields=["keyword", "snapshot_date"]),
        ]

    def __str__(self):
        return f"{self.keyword.keyword} on {self.snapshot_date}: {self.trend_score}"