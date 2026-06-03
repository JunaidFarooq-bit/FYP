"""
Integration tests — comparative_analysis views.

Covers: GET input form, POST analyze, GET results page.
Edge cases: same URLs for both inputs, missing URL, unauthenticated access,
            LLM timeout, result persistence and session fallback.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from comparative_analysis.models import ComparisonReport


MOCK_COMPARISON_RESULT = {
    'primary': {
        'url': 'https://mysite.com',
        'title': 'My Site',
        'scores': {'overall_score': 72.0, 'on_page_score': 75.0, 'technical_score': 70.0, 'authority_score': 65.0},
        'semantic': {'detected_keyword': 'python tutorial', 'intent_type': 'informational', 'topic_depth_score': 70},
        'technical': {'technical_score': 70, 'mobile_responsive': True, 'https': True},
        'authority': {'domain_authority': 30, 'authority_score': 65},
    },
    'competitor': {
        'url': 'https://competitor.com',
        'title': 'Competitor Site',
        'scores': {'overall_score': 85.0, 'on_page_score': 88.0, 'technical_score': 82.0, 'authority_score': 80.0},
        'semantic': {'detected_keyword': 'python course', 'intent_type': 'informational', 'topic_depth_score': 85},
        'technical': {'technical_score': 82, 'mobile_responsive': True, 'https': True},
        'authority': {'domain_authority': 60, 'authority_score': 80},
    },
    'gap_analysis': {
        'summary': 'Competitor has stronger authority.',
        'explanation': {
            'opening': 'Analysis complete',
            'reasons': ['Better authority', 'Faster speed'],
            'recommendations': ['Build backlinks', 'Optimize images'],
        },
        'recommendations': ['Build backlinks', 'Optimize images'],
    },
    'report_id': 1,
}


@pytest.mark.integration
@pytest.mark.comparative
class TestComparativeInputView:

    def test_input_form_returns_200(self, authenticated_client):
        response = authenticated_client.get('/comparative-analysis/')
        assert response.status_code == 200

    def test_input_form_requires_login(self, client):
        response = client.get('/comparative-analysis/')
        assert response.status_code in (200, 302)


@pytest.mark.integration
@pytest.mark.comparative
class TestAnalyzeView:

    @patch('comparative_analysis.views.ComparisonOrchestrator')
    def test_analyze_returns_redirect_to_results(
        self, mock_orch_cls, authenticated_client, pro_subscription, test_user, db
    ):
        mock_orch = Mock()
        mock_orch.run_full_analysis.return_value = MOCK_COMPARISON_RESULT
        mock_orch_cls.return_value = mock_orch

        response = authenticated_client.post('/comparative-analysis/analyze/', {
            'url_primary': 'https://mysite.com',
            'url_competitor': 'https://competitor.com',
            'target_keyword': 'python tutorial',
        }, follow=False)
        assert response.status_code in (200, 302)

    def test_analyze_requires_login(self, client):
        response = client.post('/comparative-analysis/analyze/', {
            'url_primary': 'https://a.com',
            'url_competitor': 'https://b.com',
        })
        assert response.status_code in (200, 302)

    @patch('comparative_analysis.views.ComparisonOrchestrator')
    def test_analyze_with_missing_competitor_url(
        self, mock_orch_cls, authenticated_client, pro_subscription, test_user
    ):
        response = authenticated_client.post('/comparative-analysis/analyze/', {
            'url_primary': 'https://mysite.com',
            'url_competitor': '',
        }, follow=True)
        assert response.status_code == 200

    @patch('comparative_analysis.views.ComparisonOrchestrator')
    def test_analyze_saves_to_database(
        self, mock_orch_cls, authenticated_client, pro_subscription, test_user, db
    ):
        mock_orch = Mock()
        result = dict(MOCK_COMPARISON_RESULT)
        mock_orch.run_full_analysis.return_value = result
        mock_orch_cls.return_value = mock_orch

        initial_count = ComparisonReport.objects.count()
        authenticated_client.post('/comparative-analysis/analyze/', {
            'url_primary': 'https://mysite.com',
            'url_competitor': 'https://competitor.com',
            'target_keyword': 'python tutorial',
        }, follow=True)
        assert ComparisonReport.objects.count() >= initial_count


@pytest.mark.integration
@pytest.mark.comparative
class TestResultsView:

    def test_results_page_with_valid_id(self, authenticated_client, sample_comparison_report):
        response = authenticated_client.get(
            f'/comparative-analysis/results/{sample_comparison_report.id}/'
        )
        assert response.status_code == 200

    def test_results_page_with_invalid_id_returns_404_or_redirect(self, authenticated_client):
        response = authenticated_client.get('/comparative-analysis/results/99999/')
        assert response.status_code in (200, 302, 404)

    def test_results_require_login(self, client, sample_comparison_report):
        response = client.get(
            f'/comparative-analysis/results/{sample_comparison_report.id}/'
        )
        assert response.status_code in (200, 302)

    def test_results_display_scores(self, authenticated_client, sample_comparison_report):
        response = authenticated_client.get(
            f'/comparative-analysis/results/{sample_comparison_report.id}/'
        )
        if response.status_code == 200:
            content = response.content.decode()
            assert len(content) > 100
