from django.db import models
from django.utils import timezone


class ComparisonReport(models.Model):
    """Store comparison analysis results for historical tracking"""
    
    url_primary = models.URLField(max_length=500)
    url_competitor = models.URLField(max_length=500)
    target_keyword = models.CharField(max_length=200, blank=True, null=True)
    
    # Detected metadata
    detected_keyword_primary = models.CharField(max_length=200, blank=True)
    detected_keyword_competitor = models.CharField(max_length=200, blank=True)
    intent_type_primary = models.CharField(max_length=50, blank=True)
    intent_type_competitor = models.CharField(max_length=50, blank=True)
    
    # Scores (stored as JSON for flexibility)
    scores_primary = models.JSONField(default=dict)
    scores_competitor = models.JSONField(default=dict)
    
    # Gap analysis
    gap_summary = models.TextField(blank=True)
    ranking_explanation = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    analysis_duration = models.FloatField(null=True, blank=True)  # seconds
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Comparison: {self.url_primary[:50]} vs {self.url_competitor[:50]}"