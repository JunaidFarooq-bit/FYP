"""
Unit tests — keyword_ai models.

Covers: ContentAnalysis, KeywordOpportunity, SuggestionFeedback, AnalysisTask.
Edge cases: duplicate URLs, feedback states, task status transitions, embedding shape.
"""

import pytest
import numpy as np
from django.utils import timezone

from keyword_ai.models import ContentAnalysis, KeywordOpportunity, AnalysisTask, SuggestionFeedback


# ---------------------------------------------------------------------------
# ContentAnalysis
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.keyword
class TestContentAnalysis:

    def test_create_content_analysis(self, db, sample_embedding):
        ca = ContentAnalysis.objects.create(
            url='https://test.com/page',
            title='Test Page',
            meta_description='A test page',
            full_text='Some content about testing.',
            quality_score=75.0,
            word_count=500,
            embedding=sample_embedding.tolist(),
        )
        assert ca.pk is not None
        assert ca.url == 'https://test.com/page'

    def test_url_unique_constraint(self, db, sample_embedding):
        ContentAnalysis.objects.create(
            url='https://duplicate.com',
            title='First',
            embedding=sample_embedding.tolist(),
        )
        with pytest.raises(Exception):
            ContentAnalysis.objects.create(
                url='https://duplicate.com',
                title='Second',
                embedding=sample_embedding.tolist(),
            )

    def test_embedding_shape_stored(self, db, sample_embedding):
        ca = ContentAnalysis.objects.create(
            url='https://emb-test.com',
            title='Embedding Test',
            embedding=sample_embedding.tolist(),
        )
        ca.refresh_from_db()
        assert len(ca.embedding) == 384

    def test_quality_score_range(self, db, sample_embedding):
        ca = ContentAnalysis.objects.create(
            url='https://score-test.com',
            title='Score Test',
            quality_score=100.0,
            embedding=sample_embedding.tolist(),
        )
        assert 0 <= ca.quality_score <= 100

    def test_tfidf_keywords_json_field(self, db, sample_embedding):
        keywords = [{'term': 'python', 'score': 0.9}, {'term': 'tutorial', 'score': 0.7}]
        ca = ContentAnalysis.objects.create(
            url='https://tfidf-test.com',
            title='TF-IDF Test',
            tfidf_keywords=keywords,
            embedding=sample_embedding.tolist(),
        )
        ca.refresh_from_db()
        assert ca.tfidf_keywords == keywords

    def test_structure_data_json_field(self, db, sample_embedding):
        structure = {'paragraphs': 5, 'lists': 2, 'headings': 3}
        ca = ContentAnalysis.objects.create(
            url='https://struct-test.com',
            title='Structure Test',
            structure_data=structure,
            embedding=sample_embedding.tolist(),
        )
        ca.refresh_from_db()
        assert ca.structure_data == structure

    def test_str_representation(self, sample_content_analysis):
        result = str(sample_content_analysis)
        assert 'example.com' in result or 'python' in result.lower()

    def test_update_existing_analysis(self, sample_content_analysis):
        sample_content_analysis.quality_score = 99.0
        sample_content_analysis.save()
        sample_content_analysis.refresh_from_db()
        assert sample_content_analysis.quality_score == 99.0


# ---------------------------------------------------------------------------
# KeywordOpportunity
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.keyword
class TestKeywordOpportunity:

    def test_create_keyword_opportunity(self, db, sample_content_analysis):
        opp = KeywordOpportunity.objects.create(
            content_analysis=sample_content_analysis,
            keyword='machine learning',
            keyword_type='tfidf',
            relevance_score=88.0,
            difficulty_score=55.0,
            search_intent='informational',
            priority='high',
        )
        assert opp.pk is not None
        assert opp.keyword == 'machine learning'

    def test_default_flags_are_none(self, db, sample_content_analysis):
        opp = KeywordOpportunity.objects.create(
            content_analysis=sample_content_analysis,
            keyword='default test',
            relevance_score=70.0,
        )
        assert opp.is_accepted is None or opp.is_accepted is False
        assert opp.is_rejected is None or opp.is_rejected is False

    def test_accept_keyword(self, db, sample_content_analysis):
        opp = KeywordOpportunity.objects.create(
            content_analysis=sample_content_analysis,
            keyword='accept test',
            relevance_score=80.0,
        )
        opp.is_accepted = True
        opp.save()
        opp.refresh_from_db()
        assert opp.is_accepted is True

    def test_reject_keyword(self, db, sample_content_analysis):
        opp = KeywordOpportunity.objects.create(
            content_analysis=sample_content_analysis,
            keyword='reject test',
            relevance_score=50.0,
        )
        opp.is_rejected = True
        opp.save()
        opp.refresh_from_db()
        assert opp.is_rejected is True

    @pytest.mark.parametrize('ktype', ['tfidf', 'gap', 'llm', 'longtail'])
    def test_keyword_types_accepted(self, db, sample_content_analysis, ktype):
        opp = KeywordOpportunity.objects.create(
            content_analysis=sample_content_analysis,
            keyword=f'keyword_{ktype}',
            keyword_type=ktype,
            relevance_score=75.0,
        )
        assert opp.keyword_type == ktype

    @pytest.mark.parametrize('intent', ['informational', 'navigational', 'transactional', 'commercial'])
    def test_search_intent_types(self, db, sample_content_analysis, intent):
        opp = KeywordOpportunity.objects.create(
            content_analysis=sample_content_analysis,
            keyword=f'intent_{intent}',
            search_intent=intent,
            relevance_score=75.0,
        )
        assert opp.search_intent == intent

    def test_cascade_delete_with_content_analysis(self, db, sample_content_analysis):
        KeywordOpportunity.objects.create(
            content_analysis=sample_content_analysis,
            keyword='cascade test',
            relevance_score=75.0,
        )
        ca_id = sample_content_analysis.id
        sample_content_analysis.delete()
        assert not KeywordOpportunity.objects.filter(content_analysis_id=ca_id).exists()

    def test_update_or_create_deduplication(self, db, sample_content_analysis):
        KeywordOpportunity.objects.create(
            content_analysis=sample_content_analysis,
            keyword='dedup test',
            relevance_score=70.0,
        )
        opp, created = KeywordOpportunity.objects.update_or_create(
            content_analysis=sample_content_analysis,
            keyword='dedup test',
            defaults={'relevance_score': 95.0},
        )
        assert created is False
        assert opp.relevance_score == 95.0


# ---------------------------------------------------------------------------
# SuggestionFeedback
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.keyword
class TestSuggestionFeedback:

    def test_create_feedback(self, db, sample_keyword_opportunities):
        opp = sample_keyword_opportunities[0]
        feedback = SuggestionFeedback.objects.create(
            opportunity=opp,
            user_action='accepted',
            rating=5,
        )
        assert feedback.pk is not None
        assert feedback.user_action == 'accepted'

    @pytest.mark.parametrize('action', ['accepted', 'rejected', 'ignored', 'implemented'])
    def test_all_feedback_actions_accepted(self, db, sample_keyword_opportunities, action):
        opp = sample_keyword_opportunities[0]
        feedback = SuggestionFeedback.objects.create(
            opportunity=opp,
            user_action=action,
            rating=3,
        )
        assert feedback.user_action == action

    def test_rating_range_1_to_5(self, db, sample_keyword_opportunities):
        opp = sample_keyword_opportunities[0]
        for rating in [1, 2, 3, 4, 5]:
            SuggestionFeedback.objects.create(
                opportunity=opp,
                user_action='accepted',
                rating=rating,
            )
        feedbacks = SuggestionFeedback.objects.filter(opportunity=opp)
        for fb in feedbacks:
            assert 1 <= fb.rating <= 5

    def test_feedback_with_comment(self, db, sample_keyword_opportunities):
        opp = sample_keyword_opportunities[0]
        comment = 'Great keyword suggestion, very relevant!'
        feedback = SuggestionFeedback.objects.create(
            opportunity=opp,
            user_action='accepted',
            rating=5,
            user_comment=comment,
        )
        feedback.refresh_from_db()
        assert feedback.user_comment == comment


# ---------------------------------------------------------------------------
# AnalysisTask
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.keyword
class TestAnalysisTask:

    def test_create_task(self, db):
        task = AnalysisTask.objects.create(
            task_id='task-001',
            task_type='single_url',
            parameters={'url': 'https://example.com'},
            status='pending',
        )
        assert task.pk is not None
        assert task.status == 'pending'

    @pytest.mark.parametrize('status', ['pending', 'processing', 'completed', 'failed'])
    def test_task_status_transitions(self, db, status):
        task = AnalysisTask.objects.create(
            task_id=f'task-{status}',
            task_type='single_url',
            parameters={},
            status=status,
        )
        assert task.status == status

    def test_task_progress_update(self, sample_analysis_task):
        sample_analysis_task.progress_percent = 50
        sample_analysis_task.processed_urls = 1
        sample_analysis_task.save()
        sample_analysis_task.refresh_from_db()
        assert sample_analysis_task.progress_percent == 50

    def test_task_completed_with_result(self, sample_analysis_task):
        result_data = {'keywords': ['python', 'tutorial'], 'count': 2}
        sample_analysis_task.status = 'completed'
        sample_analysis_task.progress_percent = 100
        sample_analysis_task.result_data = result_data  # field is result_data
        sample_analysis_task.save()
        sample_analysis_task.refresh_from_db()
        assert sample_analysis_task.status == 'completed'
        assert sample_analysis_task.result_data == result_data

    def test_task_failed_with_error_message(self, sample_analysis_task):
        sample_analysis_task.status = 'failed'
        sample_analysis_task.error_message = 'Connection timeout'
        sample_analysis_task.save()
        sample_analysis_task.refresh_from_db()
        assert sample_analysis_task.status == 'failed'
        assert sample_analysis_task.error_message == 'Connection timeout'

    def test_batch_task_tracking(self, db):
        task = AnalysisTask.objects.create(
            task_id='batch-001',
            task_type='batch',
            parameters={'urls': ['https://a.com', 'https://b.com', 'https://c.com']},
            status='processing',
            total_urls=3,
            processed_urls=1,
            failed_urls=0,
        )
        assert task.total_urls == 3
        assert task.processed_urls == 1
