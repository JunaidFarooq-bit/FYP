# Generated manually for Phase 2: Database Optimization

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add database indexes for keyword AI query performance.
    Phase 2 of production readiness plan.
    """

    dependencies = [
        ('keyword_ai', '0007_contentanalysis_full_text'),
    ]

    operations = [
        # KeywordOpportunity indexes - frequently queried
        migrations.AddIndex(
            model_name='keywordopportunity',
            index=models.Index(
                fields=['content_analysis', '-relevance_score'],
                name='kwai_opp_content_relevance_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='keywordopportunity',
            index=models.Index(
                fields=['keyword', 'keyword_type'],
                name='kwai_opp_keyword_type_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='keywordopportunity',
            index=models.Index(
                fields=['search_intent', '-relevance_score'],
                name='kwai_opp_intent_score_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='keywordopportunity',
            index=models.Index(
                fields=['priority', '-relevance_score'],
                name='kwai_opp_priority_score_idx'
            ),
        ),
        
        # SuggestionFeedback indexes - analytics queries
        migrations.AddIndex(
            model_name='suggestionfeedback',
            index=models.Index(
                fields=['opportunity', '-timestamp'],
                name='kwai_fb_opp_time_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='suggestionfeedback',
            index=models.Index(
                fields=['user_action', '-timestamp'],
                name='kwai_fb_action_time_idx'
            ),
        ),
        
        # AnalysisTask indexes - task monitoring
        migrations.AddIndex(
            model_name='analysistask',
            index=models.Index(
                fields=['task_id'],
                name='kwai_task_taskid_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='analysistask',
            index=models.Index(
                fields=['status', '-created_at'],
                name='kwai_task_status_date_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='analysistask',
            index=models.Index(
                fields=['session_id', '-created_at'],
                name='kwai_task_session_date_idx'
            ),
        ),
        
        # ModelPerformance indexes - reporting queries
        migrations.AddIndex(
            model_name='modelperformance',
            index=models.Index(
                fields=['model_name', '-recorded_at'],
                name='kwai_perf_model_date_idx'
            ),
        ),
        
        # ContentAnalysis index for full-text search (if not already present)
        # Note: Already has url index, adding analyzed_at for range queries
        migrations.AddIndex(
            model_name='contentanalysis',
            index=models.Index(
                fields=['-analyzed_at', 'quality_score'],
                name='kwai_content_date_quality_idx'
            ),
        ),
    ]
