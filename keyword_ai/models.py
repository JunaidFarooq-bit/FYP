"""
Database models for Phase 1: Content Analysis & Keyword Suggestion System.
"""

from django.db import models
from pgvector.django import VectorField
import json


class ContentAnalysis(models.Model):
    """
    Stores detailed content analysis results.
    Tracks analyzed URLs with their content metrics.
    """
    url = models.URLField(max_length=2000, unique=True, db_index=True)
    content_hash = models.CharField(max_length=64, help_text="MD5 hash of content for change detection")
    
    # Content metrics
    title = models.CharField(max_length=300, blank=True)
    meta_description = models.TextField(blank=True)
    word_count = models.IntegerField(default=0)
    
    # Quality scores
    quality_score = models.FloatField(default=0.0, help_text="Overall content quality 0-100")
    readability_ease = models.FloatField(default=0.0)
    readability_grade = models.FloatField(default=0.0)
    
    # Structure analysis (stored as JSON)
    structure_data = models.JSONField(default=dict, help_text="Paragraphs, lists, headings count")
    
    # Entities (stored as JSON)
    entities_data = models.JSONField(default=dict, help_text="Organizations, people, locations, technologies")
    
    # TF-IDF keywords (stored as JSON)
    tfidf_keywords = models.JSONField(default=list, help_text="Top TF-IDF scored keywords")
    
    # Semantic embedding using pgvector for similarity search (384 dimensions for all-MiniLM-L6-v2)
    embedding = VectorField(dimensions=384, blank=True, null=True, help_text="Vector embedding for RAG similarity search")
    
    # Analysis metadata
    analyzed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Content Analysis"
        verbose_name_plural = "Content Analyses"
        ordering = ['-analyzed_at']
        indexes = [
            models.Index(fields=['quality_score', '-analyzed_at']),
            models.Index(fields=['url']),
        ]
    
    def __str__(self):
        return f"Analysis: {self.url[:60]}..."
    
    def get_embedding_list(self):
        """Get embedding as Python list for serialization."""
        if self.embedding is not None:
            return self.embedding.tolist()
        return None


class KeywordOpportunity(models.Model):
    """
    Identified keyword opportunities for a specific URL.
    Tracks potential keywords with their metrics.
    """
    
    INTENT_CHOICES = [
        ('informational', 'Informational'),
        ('navigational', 'Navigational'),
        ('transactional', 'Transactional'),
        ('commercial', 'Commercial'),
    ]
    
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    # Relations
    content_analysis = models.ForeignKey(
        ContentAnalysis, 
        on_delete=models.CASCADE,
        related_name='opportunities'
    )
    
    # Keyword data
    keyword = models.CharField(max_length=200, db_index=True)
    keyword_type = models.CharField(
        max_length=20,
        choices=[('tfidf', 'TF-IDF Extracted'), ('gap', 'Competitor Gap'), ('llm', 'AI Suggested'), ('longtail', 'Long-tail')],
        default='tfidf'
    )
    
    # Metrics
    relevance_score = models.FloatField(default=0.0, help_text="Relevance to content 0-100")
    search_volume_estimate = models.CharField(max_length=50, blank=True, help_text="e.g., '1K-10K'")
    difficulty_score = models.FloatField(default=0.0, help_text="SEO difficulty 0-100")
    competition_gap_score = models.FloatField(default=0.0, help_text="Gap vs competitors 0-100")
    
    # Classification
    search_intent = models.CharField(max_length=20, choices=INTENT_CHOICES, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # AI reasoning
    ai_reasoning = models.TextField(blank=True, help_text="Explanation for why this keyword is suggested")
    suggested_action = models.TextField(blank=True, help_text="Action to take (e.g., 'Add H2 section')")
    
    # Status
    is_accepted = models.BooleanField(null=True, blank=True, help_text="User accepted this suggestion")
    is_rejected = models.BooleanField(null=True, blank=True, help_text="User rejected this suggestion")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Keyword Opportunity"
        verbose_name_plural = "Keyword Opportunities"
        ordering = ['-relevance_score']
        unique_together = ['content_analysis', 'keyword']
    
    def __str__(self):
        return f"{self.keyword} ({self.relevance_score:.1f})"


class SuggestionFeedback(models.Model):
    """
    Tracks user feedback on keyword suggestions.
    Used for continuous model improvement.
    """
    
    ACTION_CHOICES = [
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('ignored', 'Ignored'),
        ('implemented', 'Implemented'),
    ]
    
    opportunity = models.ForeignKey(
        KeywordOpportunity,
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    
    user_action = models.CharField(max_length=15, choices=ACTION_CHOICES)
    
    # Optional feedback
    user_comment = models.TextField(blank=True)
    rating = models.IntegerField(null=True, blank=True, help_text="1-5 star rating")
    
    # Tracking
    timestamp = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=100, blank=True, help_text="For tracking user sessions")
    
    # Performance tracking (updated later via cron job)
    ranking_before = models.IntegerField(null=True, blank=True)
    ranking_after_30_days = models.IntegerField(null=True, blank=True)
    traffic_increase_estimate = models.FloatField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Suggestion Feedback"
        verbose_name_plural = "Suggestion Feedbacks"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.opportunity.keyword}: {self.user_action}"


class CompetitorAnalysis(models.Model):
    """
    Stores competitor page analysis data.
    """
    user_content = models.ForeignKey(
        ContentAnalysis,
        on_delete=models.CASCADE,
        related_name='competitor_analyses'
    )
    
    competitor_url = models.URLField(max_length=2000)
    competitor_title = models.CharField(max_length=300, blank=True)
    
    # Extracted data
    meta_keywords = models.TextField(blank=True)
    headings_data = models.JSONField(default=list)
    top_keywords = models.JSONField(default=list)
    
    # Analysis status
    status = models.CharField(max_length=20, default='success')
    error_message = models.TextField(blank=True)
    
    analyzed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Competitor Analysis"
        verbose_name_plural = "Competitor Analyses"
        unique_together = ['user_content', 'competitor_url']
    
    def __str__(self):
        return f"Competitor: {self.competitor_url[:60]}..."


class AnalysisTask(models.Model):
    """
    Tracks asynchronous batch analysis tasks.
    """
    TASK_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    TASK_TYPE_CHOICES = [
        ('single_url', 'Single URL Analysis'),
        ('batch_urls', 'Batch URL Analysis'),
        ('content_text', 'Content Text Analysis'),
        ('competitor_analysis', 'Competitor Gap Analysis'),
    ]
    
    # Task identification
    task_id = models.CharField(max_length=100, unique=True, db_index=True)
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES)
    
    # Task parameters (stored as JSON)
    parameters = models.JSONField(default=dict)
    
    # Progress tracking
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='pending')
    progress_percent = models.IntegerField(default=0, help_text="Progress 0-100")
    current_step = models.CharField(max_length=200, blank=True, help_text="Current processing step")
    
    # Results
    result_data = models.JSONField(default=dict, null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # URLs being processed (for batch tasks)
    total_urls = models.IntegerField(default=1)
    processed_urls = models.IntegerField(default=0)
    failed_urls = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # User tracking (optional)
    session_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = "Analysis Task"
        verbose_name_plural = "Analysis Tasks"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Task {self.task_id[:8]}: {self.task_type} ({self.status})"
    
    def update_progress(self, percent: int, step: str = ""):
        """Update task progress."""
        self.progress_percent = min(100, max(0, percent))
        if step:
            self.current_step = step
        self.save(update_fields=['progress_percent', 'current_step'])
    
    def mark_completed(self, result_data: dict = None):
        """Mark task as completed."""
        from django.utils import timezone
        self.status = 'completed'
        self.progress_percent = 100
        self.result_data = result_data or {}
        self.completed_at = timezone.now()
        self.save()
    
    def mark_failed(self, error: str):
        """Mark task as failed."""
        from django.utils import timezone
        self.status = 'failed'
        self.error_message = error
        self.completed_at = timezone.now()
        self.save()
    
    @property
    def duration_seconds(self):
        """Calculate task duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            from django.utils import timezone
            return (timezone.now() - self.started_at).total_seconds()
        return None


class GapAnalysis(models.Model):
    """
    Aggregated gap analysis for a content piece.
    """
    content_analysis = models.OneToOneField(
        ContentAnalysis,
        on_delete=models.CASCADE,
        related_name='gap_analysis'
    )
    
    total_gap_opportunities = models.IntegerField(default=0)
    high_priority_gaps = models.JSONField(default=list)
    all_gap_keywords = models.JSONField(default=list)
    
    recommendations = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Gap Analysis"
        verbose_name_plural = "Gap Analyses"
    
    def __str__(self):
        return f"Gaps for {self.content_analysis.url[:60]}..."


class ModelPerformance(models.Model):
    """
    Tracks ML model performance metrics over time.
    """
    model_name = models.CharField(max_length=100, db_index=True)
    model_version = models.CharField(max_length=50)
    
    # Performance metrics
    total_predictions = models.IntegerField(default=0)
    accepted_suggestions = models.IntegerField(default=0)
    rejected_suggestions = models.IntegerField(default=0)
    ignored_suggestions = models.IntegerField(default=0)
    
    # Quality metrics
    avg_relevance_score = models.FloatField(null=True, blank=True)
    avg_user_rating = models.FloatField(null=True, blank=True)
    
    # Accuracy metrics (if ground truth available)
    precision_at_k = models.JSONField(default=dict, help_text="Precision@K metrics")
    
    # Tracking
    recorded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        verbose_name = "Model Performance"
        verbose_name_plural = "Model Performances"
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['model_name', 'recorded_at']),
        ]
    
    def __str__(self):
        return f"{self.model_name} v{self.model_version} @ {self.recorded_at.strftime('%Y-%m-%d')}"
    
    @property
    def acceptance_rate(self) -> float:
        """Calculate acceptance rate."""
        total = self.accepted_suggestions + self.rejected_suggestions
        if total == 0:
            return 0.0
        return round(self.accepted_suggestions / total * 100, 2)
    
    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate (accepted + rejected)."""
        if self.total_predictions == 0:
            return 0.0
        engaged = self.accepted_suggestions + self.rejected_suggestions
        return round(engaged / self.total_predictions * 100, 2)


class ABTest(models.Model):
    """
    A/B testing for model improvements.
    """
    TEST_STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('stopped', 'Stopped'),
    ]
    
    test_name = models.CharField(max_length=200)
    test_description = models.TextField(blank=True)
    
    # Model variants
    control_model = models.CharField(max_length=100)
    treatment_model = models.CharField(max_length=100)
    
    # Traffic split (percentage to treatment)
    traffic_split_percent = models.IntegerField(default=50)
    
    # Metrics
    control_metrics = models.JSONField(default=dict)
    treatment_metrics = models.JSONField(default=dict)
    
    # Status
    status = models.CharField(max_length=20, choices=TEST_STATUS_CHOICES, default='running')
    
    # Winner
    winner = models.CharField(max_length=100, blank=True, help_text=" winning model variant")
    confidence_level = models.FloatField(null=True, blank=True, help_text="Statistical confidence 0-1")
    
    # Tracking
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "A/B Test"
        verbose_name_plural = "A/B Tests"
        ordering = ['-started_at']
    
    def __str__(self):
        return f"A/B Test: {self.test_name} ({self.status})"


class KeywordRanking(models.Model):
    """
    Tracks keyword ranking changes over time for feedback loop.
    """
    opportunity = models.ForeignKey(
        KeywordOpportunity,
        on_delete=models.CASCADE,
        related_name='rankings'
    )
    
    keyword = models.CharField(max_length=200)
    url = models.URLField(max_length=2000)
    
    # Ranking data
    ranking_position = models.IntegerField(null=True, blank=True)
    search_volume = models.IntegerField(null=True, blank=True)
    
    # Tracking
    checked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Keyword Ranking"
        verbose_name_plural = "Keyword Rankings"
        ordering = ['-checked_at']
    
    def __str__(self):
        return f"{self.keyword}: Position {self.ranking_position}"


class UserSessionMetrics(models.Model):
    """
    Aggregated metrics per user session for analytics.
    """
    session_id = models.CharField(max_length=100, db_index=True)
    
    # Usage metrics
    total_analyses = models.IntegerField(default=0)
    total_keywords_generated = models.IntegerField(default=0)
    total_feedback_submitted = models.IntegerField(default=0)
    
    # Engagement metrics
    avg_time_on_page = models.IntegerField(null=True, blank=True, help_text="Seconds")
    features_used = models.JSONField(default=list)
    
    # Timestamps
    first_activity = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Session Metrics"
        verbose_name_plural = "User Session Metrics"
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"Session {self.session_id[:8]}: {self.total_analyses} analyses"
