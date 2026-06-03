"""
Shared pytest fixtures for the WebLift SEO Platform test suite.
Located in tests/ folder — covers all 4 apps.
"""

import os
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project.settings_test')

import django
django.setup()

from subscriptions.models import SubscriptionTier, Subscription, UsageTracker, ManualPaymentSubmission
from keyword_ai.models import ContentAnalysis, KeywordOpportunity, AnalysisTask, SuggestionFeedback
from comparative_analysis.models import ComparisonReport


# ---------------------------------------------------------------------------
# Django clients
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    return Client()


@pytest.fixture
def authenticated_client(client, test_user):
    client.force_login(test_user)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def pro_client(client, test_user, pro_subscription):
    client.force_login(test_user)
    return client


@pytest.fixture
def basic_client(client, test_user, basic_subscription):
    client.force_login(test_user)
    return client


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@pytest.fixture
def test_user(db):
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User',
    )
    return user


@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123',
    )
    return user


@pytest.fixture
def another_user(db):
    user = User.objects.create_user(
        username='anotheruser',
        email='another@example.com',
        password='anotherpass123',
    )
    return user


# ---------------------------------------------------------------------------
# Subscription tiers
# ---------------------------------------------------------------------------

@pytest.fixture
def subscription_tiers(db):
    tiers = {}
    tiers['free'], _ = SubscriptionTier.objects.get_or_create(
        name='free',
        defaults={
            'display_name': 'Free Trial',
            'price_monthly': 0,
            'price_yearly': 0,
            'max_audits_per_month': 1,
            'max_keywords_per_analysis': 20,
            'max_competitors_per_analysis': 0,
            'has_ai_suggestions': False,
            'has_competitor_analysis': False,
            'has_pdf_export': False,
            'has_api_access': False,
        },
    )
    tiers['basic'], _ = SubscriptionTier.objects.get_or_create(
        name='basic',
        defaults={
            'display_name': 'Basic',
            'price_monthly': 9,
            'price_yearly': 90,
            'max_audits_per_month': 10,
            'max_keywords_per_analysis': 50,
            'max_competitors_per_analysis': 0,
            'has_ai_suggestions': True,
            'has_competitor_analysis': False,
            'has_pdf_export': True,
            'has_api_access': False,
        },
    )
    tiers['pro'], _ = SubscriptionTier.objects.get_or_create(
        name='pro',
        defaults={
            'display_name': 'Pro',
            'price_monthly': 29,
            'price_yearly': 290,
            'max_audits_per_month': 50,
            'max_keywords_per_analysis': 200,
            'max_competitors_per_analysis': 3,
            'has_ai_suggestions': True,
            'has_competitor_analysis': True,
            'has_pdf_export': True,
            'has_api_access': True,
            'has_priority_support': True,
        },
    )
    tiers['enterprise'], _ = SubscriptionTier.objects.get_or_create(
        name='enterprise',
        defaults={
            'display_name': 'Enterprise',
            'price_monthly': 99,
            'price_yearly': 990,
            'max_audits_per_month': None,
            'max_keywords_per_analysis': 500,
            'max_competitors_per_analysis': 10,
            'has_ai_suggestions': True,
            'has_competitor_analysis': True,
            'has_pdf_export': True,
            'has_api_access': True,
            'has_priority_support': True,
        },
    )
    return tiers


@pytest.fixture
def free_subscription(db, test_user, subscription_tiers):
    Subscription.objects.filter(user=test_user).delete()
    sub = Subscription.objects.create(
        user=test_user,
        tier=subscription_tiers['free'],
        status='free_trial_used',
    )
    UsageTracker.objects.get_or_create(user=test_user)
    return sub


@pytest.fixture
def basic_subscription(db, test_user, subscription_tiers):
    Subscription.objects.filter(user=test_user).delete()
    sub = Subscription.objects.create(
        user=test_user,
        tier=subscription_tiers['basic'],
        status='active',
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )
    UsageTracker.objects.get_or_create(user=test_user)
    return sub


@pytest.fixture
def pro_subscription(db, test_user, subscription_tiers):
    Subscription.objects.filter(user=test_user).delete()
    sub = Subscription.objects.create(
        user=test_user,
        tier=subscription_tiers['pro'],
        status='active',
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )
    UsageTracker.objects.get_or_create(user=test_user)
    return sub


@pytest.fixture
def enterprise_subscription(db, test_user, subscription_tiers):
    Subscription.objects.filter(user=test_user).delete()
    sub = Subscription.objects.create(
        user=test_user,
        tier=subscription_tiers['enterprise'],
        status='active',
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )
    UsageTracker.objects.get_or_create(user=test_user)
    return sub


@pytest.fixture
def expired_subscription(db, test_user, subscription_tiers):
    Subscription.objects.filter(user=test_user).delete()
    sub = Subscription.objects.create(
        user=test_user,
        tier=subscription_tiers['pro'],
        status='active',
        current_period_start=timezone.now() - timedelta(days=60),
        current_period_end=timezone.now() - timedelta(days=1),
    )
    UsageTracker.objects.get_or_create(user=test_user)
    return sub


# ---------------------------------------------------------------------------
# HTML / content samples
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_html():
    return """<!DOCTYPE html>
<html>
<head>
    <title>Best Python Tutorial 2024 - Learn Fast</title>
    <meta name="description" content="Comprehensive Python tutorial for beginners and experts.">
    <meta property="og:title" content="Python Tutorial">
    <link rel="canonical" href="https://example.com/python-tutorial">
</head>
<body>
    <nav>Navigation links here</nav>
    <main>
        <h1>Learn Python Programming</h1>
        <p>Python is a versatile programming language perfect for beginners and experts alike.</p>
        <h2>Getting Started with Python</h2>
        <p>Installing Python is the first step in your programming journey.</p>
        <ul>
            <li>Download Python from python.org</li>
            <li>Install on your operating system</li>
            <li>Verify installation with python --version</li>
        </ul>
        <h2>Basic Syntax</h2>
        <p>Python uses indentation to define code blocks, making it clean and readable.</p>
        <a href="/internal-page">Internal Link</a>
        <a href="https://external.com">External Link</a>
    </main>
    <footer>Footer content</footer>
</body>
</html>"""


@pytest.fixture
def minimal_html():
    return "<html><head></head><body><p>Short.</p></body></html>"


@pytest.fixture
def html_no_title():
    return "<html><head></head><body><h1>Heading without title tag</h1><p>Content here.</p></body></html>"


@pytest.fixture
def sample_embedding():
    return np.random.rand(384).astype(np.float32)


# ---------------------------------------------------------------------------
# Keyword AI fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_content_analysis(db, sample_embedding):
    return ContentAnalysis.objects.create(
        url='https://example.com/python-tutorial',
        title='Best Python Tutorial 2024',
        meta_description='Learn Python programming with our comprehensive tutorial',
        full_text='Python is a versatile programming language used for web development, data science, and automation.',
        quality_score=85.5,
        word_count=1500,
        embedding=sample_embedding.tolist(),
    )


@pytest.fixture
def sample_keyword_opportunities(db, sample_content_analysis):
    data = [
        ('python tutorial', 95.0, 'tfidf', 'informational', 'high'),
        ('learn python', 88.5, 'llm', 'informational', 'high'),
        ('python programming', 92.0, 'tfidf', 'informational', 'high'),
        ('python basics', 85.0, 'longtail', 'informational', 'medium'),
        ('python for beginners', 90.0, 'llm', 'informational', 'high'),
        ('buy python course', 70.0, 'gap', 'transactional', 'low'),
    ]
    opps = []
    for kw, score, ktype, intent, priority in data:
        opps.append(KeywordOpportunity.objects.create(
            content_analysis=sample_content_analysis,
            keyword=kw,
            keyword_type=ktype,
            relevance_score=score,
            difficulty_score=45.0,
            competition_gap_score=60.0,
            search_intent=intent,
            priority=priority,
        ))
    return opps


@pytest.fixture
def sample_analysis_task(db):
    return AnalysisTask.objects.create(
        task_id='test-task-abc123',
        task_type='single_url',
        parameters={'url': 'https://example.com', 'use_llm': True},
        status='pending',
        progress_percent=0,
        total_urls=1,
        processed_urls=0,
        failed_urls=0,
    )


# ---------------------------------------------------------------------------
# Comparative analysis fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_comparison_report(db):
    return ComparisonReport.objects.create(
        url_primary='https://mysite.com',
        url_competitor='https://competitor.com',
        target_keyword='python tutorial',
        detected_keyword_primary='python programming',
        detected_keyword_competitor='python course',
        intent_type_primary='informational',
        intent_type_competitor='informational',
        scores_primary={'overall': 75.5, 'on_page': 80.0, 'technical': 70.0, 'authority': 65.0},
        scores_competitor={'overall': 82.0, 'on_page': 85.0, 'technical': 80.0, 'authority': 78.0},
        gap_summary='Competitor has stronger authority and better technical SEO.',
        ranking_explanation='{"opening": "Analysis complete", "reasons": ["Authority gap"], "recommendations": ["Build backlinks"]}',
        analysis_duration=15.5,
    )


# ---------------------------------------------------------------------------
# HTTP / external service mocks
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_http_response():
    response = Mock()
    response.status_code = 200
    response.text = '<html><head><title>Mock Page</title></head><body><p>Content</p></body></html>'
    response.elapsed = Mock()
    response.elapsed.total_seconds.return_value = 0.5
    response.headers = {'Content-Type': 'text/html; charset=utf-8'}
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def mock_requests(mock_http_response):
    with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
        mock_get.return_value = mock_http_response
        mock_post.return_value = mock_http_response
        yield {'get': mock_get, 'post': mock_post}


@pytest.fixture
def mock_groq():
    with patch('keyword_ai.services.llm_refiner.get_groq_client') as mock_client:
        completion = Mock()
        completion.choices = [Mock(message=Mock(content='''{
            "grouped_keywords": {
                "Informational": ["python tutorial", "learn python"],
                "Transactional": ["buy python course"],
                "Commercial": ["best python IDE"],
                "Navigational": ["python.org"]
            },
            "focus_keywords": ["python tutorial", "learn python fast", "python programming"]
        }'''))]
        mock_client.return_value.chat.completions.create.return_value = completion
        yield mock_client


@pytest.fixture
def mock_moz_api():
    with patch('comparative_analysis.services.authority_analysis.requests.get') as mock_get:
        response = Mock()
        response.status_code = 200
        response.json.return_value = {'Mozscape': {'pda': 50, 'upa': 40, 'uid': 100}}
        response.raise_for_status = Mock()
        mock_get.return_value = response
        yield mock_get


@pytest.fixture
def mock_sentence_transformer():
    with patch('sentence_transformers.SentenceTransformer') as mock_model:
        mock_model.return_value.encode.return_value = np.random.rand(384).astype(np.float32)
        yield mock_model


@pytest.fixture
def mock_celery_task():
    with patch('keyword_ai.tasks.analyze_single_url_task') as mock_task:
        mock_task.delay.return_value = Mock(id='test-task-abc123')
        mock_task.apply_async.return_value = Mock(id='test-task-abc123')
        yield mock_task


# ---------------------------------------------------------------------------
# Utility fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_urls():
    return [
        'https://example1.com',
        'https://example2.com',
        'https://example3.com',
    ]


@pytest.fixture
def temp_media_root(tmp_path):
    media_path = tmp_path / 'media'
    media_path.mkdir()
    with patch('django.conf.settings.MEDIA_ROOT', str(media_path)):
        yield str(media_path)


@pytest.fixture
def disable_celery(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    yield


# ---------------------------------------------------------------------------
# Autouse
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass


@pytest.fixture(autouse=True)
def clear_cache():
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


# ---------------------------------------------------------------------------
# Pytest hooks
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line('markers', 'unit: Pure unit tests with no DB or network')
    config.addinivalue_line('markers', 'integration: Tests that use DB or mock services')
    config.addinivalue_line('markers', 'api: REST API endpoint tests')
    config.addinivalue_line('markers', 'e2e: End-to-end user journey tests')
    config.addinivalue_line('markers', 'slow: Tests that take > 5 seconds')
    config.addinivalue_line('markers', 'seo: SEOAnalyzer app tests')
    config.addinivalue_line('markers', 'keyword: keyword_ai app tests')
    config.addinivalue_line('markers', 'comparative: comparative_analysis app tests')
    config.addinivalue_line('markers', 'subscription: subscriptions app tests')
    config.addinivalue_line('markers', 'auth: Authentication / authorisation tests')
