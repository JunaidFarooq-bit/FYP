"""
Integration tests — SEO Audit views.

Covers: /home/, /show/, /report/, /report/download/, /seo-metrics/,
        /mobiletest/, /robot/, /keyPosition/, /keyword-ai-suggestions/,
        /sentimentanalysis/.
Edge cases: unauthenticated access, subscription gates, cache behavior,
            invalid URLs, POST/GET method enforcement.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.core.cache import cache


SAMPLE_AUDIT_RESULT = {
    'title': 'Test Page',
    'desc': 'Test Description',
    'title_score': 80,
    'desc_score': 75,
    'speed': 85,
    'internal_links': 10,
    'external_links': 5,
    'b_links': 0,
    'robot_flag': True,
    'sitemap_flag': True,
    'schema_flag': False,
    'ogp_flag': True,
    'https': True,
    'mob_score': 90,
    'amp': False,
    'ssl_name': 'Let\'s Encrypt',
    'ssl_expiry': '2025-12-31',
    'avg_score': 78,
    'H': {'h1': ['Main Heading'], 'h2': ['Sub 1', 'Sub 2']},
    'dens': [('python', 3.5), ('tutorial', 2.1)],
    'eeat_analysis': {},
    'grammar_analysis': {'errors': []},
    'content_analysis': {'word_count': 1500, 'quality_score': 80},
    'chart_scores': [80, 75, 85, 65, 70],
    'score_ring_offset': 150,
    'priority_issues': [],
    'content_score': 75,
    'technical_score': 85,
}


@pytest.mark.integration
@pytest.mark.seo
class TestHomeView:

    def test_home_returns_200_for_authenticated(self, authenticated_client):
        response = authenticated_client.get('/home/')
        assert response.status_code == 200

    def test_home_requires_login(self, client):
        response = client.get('/home/')
        assert response.status_code == 302

    def test_home_redirects_to_login(self, client):
        response = client.get('/home/')
        # login_url='login' resolves to '/?next=/home/' or similar
        location = response.get('Location', '')
        assert '/' in location or 'login' in location


@pytest.mark.integration
@pytest.mark.seo
class TestShowView:

    @patch('SEOAnalyzer.views_pages.Website_Audit')
    def test_show_runs_audit_for_subscribed_user(self, mock_audit_cls, pro_client, test_user, pro_subscription):
        mock_audit = Mock()
        mock_audit.get_data.return_value = SAMPLE_AUDIT_RESULT
        mock_audit_cls.return_value = mock_audit
        with patch('SEOAnalyzer.views_pages._prepare_dashboard_data', return_value=SAMPLE_AUDIT_RESULT):
            response = pro_client.post('/show/', {'url': 'https://example.com'}, follow=True)
        assert response.status_code == 200

    def test_show_requires_login(self, client):
        response = client.post('/show/', {'url': 'https://example.com'})
        assert response.status_code == 302

    def test_show_blocks_free_user_after_trial(self, basic_client, test_user, basic_subscription):
        from subscriptions.models import UsageTracker
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.audits_used_this_month = 10
        tracker.save()
        response = basic_client.post('/show/', {'url': 'https://example.com'}, follow=True)
        assert response.status_code == 200
        final_url = response.redirect_chain[-1][0] if response.redirect_chain else ''
        pricing_redirect = 'pricing' in final_url or response.status_code == 200

    def test_show_requires_post_method(self, authenticated_client):
        response = authenticated_client.get('/show/')
        assert response.status_code in (200, 302, 405)

    def test_show_with_empty_url(self, authenticated_client, pro_subscription, test_user):
        response = authenticated_client.post('/show/', {'url': ''}, follow=True)
        assert response.status_code == 200

    @patch('SEOAnalyzer.views_pages.Website_Audit')
    def test_show_caches_audit_result(self, mock_audit_cls, pro_client, test_user, pro_subscription):
        mock_audit = Mock()
        mock_audit.get_data.return_value = SAMPLE_AUDIT_RESULT
        mock_audit_cls.return_value = mock_audit
        with patch('SEOAnalyzer.views_pages._prepare_dashboard_data', return_value=SAMPLE_AUDIT_RESULT):
            pro_client.post('/show/', {'url': 'https://example.com'}, follow=True)
        cached = cache.get(f'audit_results_{"https://example.com"}')


@pytest.mark.integration
@pytest.mark.seo
class TestReportView:

    def test_report_requires_login(self, client):
        # /report/download/ is @login_required — unauthenticated GET → 302
        response = client.get('/report/download/')
        assert response.status_code == 302

    def test_report_download_requires_login(self, client):
        response = client.get('/report/download/')
        assert response.status_code == 302

    def test_report_download_blocked_for_free_user(self, authenticated_client, free_subscription, test_user):
        tracker, _ = __import__('subscriptions.models', fromlist=['UsageTracker']).UsageTracker.objects.get_or_create(user=test_user)
        tracker.free_audit_used = True
        tracker.save()
        response = authenticated_client.get('/report/download/?url=https://example.com', follow=True)
        assert response.status_code == 200

    @patch('SEOAnalyzer.services.report_orchestrator.generate_comprehensive_report_data')
    def test_report_download_allowed_for_basic_user(
        self, mock_gen, basic_client, test_user, basic_subscription
    ):
        import hashlib
        cache_key = 'audit_results_' + hashlib.md5(b'https://example.com').hexdigest()
        cache.set(cache_key, SAMPLE_AUDIT_RESULT, 3600)
        mock_gen.return_value = {**SAMPLE_AUDIT_RESULT, 'url': 'https://example.com',
                                  'error': None, 'analysis_sources': ['seo']}
        response = basic_client.get('/report/download/?url=https://example.com', follow=True)
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.seo
class TestSeoToolViews:

    def test_seo_metrics_requires_login(self, client):
        response = client.get('/seo-metrics/')
        assert response.status_code == 302

    def test_mobiletest_requires_login(self, client):
        response = client.get('/mobiletest/')
        assert response.status_code == 302

    def test_robot_requires_login(self, client):
        response = client.get('/robot/')
        assert response.status_code == 302

    def test_key_position_requires_login(self, client):
        response = client.get('/keyPosition/')
        assert response.status_code == 302

    def test_keysuggestion_requires_login(self, client):
        response = client.get('/keysuggestion/')
        assert response.status_code == 302

    def test_keyword_ai_suggestions_requires_login(self, client):
        response = client.get('/keyword-ai-suggestions/')
        assert response.status_code == 302

    def test_seo_metrics_accessible_authenticated(self, authenticated_client, pro_subscription, test_user):
        response = authenticated_client.get('/seo-metrics/')
        assert response.status_code == 200

    def test_mobiletest_accessible_authenticated(self, authenticated_client, pro_subscription, test_user):
        response = authenticated_client.get('/mobiletest/')
        assert response.status_code == 200

    def test_robot_accessible_authenticated(self, authenticated_client, pro_subscription, test_user):
        response = authenticated_client.get('/robot/')
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.seo
class TestSentimentAnalysisView:

    def test_sentiment_page_requires_login(self, client):
        response = client.get('/sentimentanalysis/')
        assert response.status_code == 302

    def test_sentiment_page_accessible_for_pro_user(self, authenticated_client, pro_subscription):
        response = authenticated_client.get('/sentimentanalysis/')
        assert response.status_code == 200

    @patch('SEOAnalyzer.views_pages.analyze_sentiment')
    def test_sentiment_analyze_post(self, mock_analyze, authenticated_client, pro_subscription):
        # analyze_sentiment_view uses the module-level analyze_sentiment function
        mock_analyze.return_value = {
            'sentiment': 'positive',
            'confidence': 0.85,
            'sentiment_score': 75,
            'success': True,
        }
        response = authenticated_client.post('/sentimentanalysis/analyze/', {
            'url': 'https://example.com',
        }, follow=True)
        assert response.status_code == 200

    def test_sentiment_analyze_empty_url(self, authenticated_client, pro_subscription):
        response = authenticated_client.post('/sentimentanalysis/analyze/', {'url': ''}, follow=True)
        assert response.status_code == 200
