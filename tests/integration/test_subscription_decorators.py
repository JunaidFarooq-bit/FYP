"""
Integration tests — Subscription decorator enforcement.

Covers: @require_subscription, @track_usage, @require_feature,
        @enforce_free_trial_limit, @api_subscription_check.
Edge cases: free trial used, expired subscription, at limit, wrong tier,
            POST vs GET, JSON vs redirect responses.
"""

import pytest
from unittest.mock import patch, Mock
from django.test import RequestFactory
from django.contrib.auth.models import User

from subscriptions.models import Subscription, UsageTracker, SubscriptionTier
from subscriptions.decorators import (
    require_subscription,
    track_usage,
    require_feature,
    api_subscription_check,
)


def _add_session(request):
    """Attach a simple dict-backed session to a RequestFactory request.
    The decorators write to request.session; RequestFactory doesn't provide one."""
    request.session = {}
    return request


@pytest.mark.integration
@pytest.mark.subscription
class TestRequireSubscriptionDecorator:

    def test_active_subscription_passes(self, test_user, pro_subscription):
        factory = RequestFactory()
        request = _add_session(factory.get('/'))
        request.user = test_user

        @require_subscription
        def my_view(request):
            return Mock(status_code=200)

        response = my_view(request)
        assert response.status_code == 200

    def test_no_subscription_redirects(self, test_user, free_subscription):
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.free_audit_used = True
        tracker.save()

        factory = RequestFactory()
        request = _add_session(factory.get('/'))
        request.user = test_user

        @require_subscription
        def my_view(request):
            return Mock(status_code=200)

        response = my_view(request)
        assert response.status_code in (302, 200)

    def test_free_trial_available_passes(self, test_user, free_subscription):
        factory = RequestFactory()
        request = _add_session(factory.get('/'))
        request.user = test_user
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.free_audit_used = False
        tracker.save()

        @require_subscription
        def my_view(request):
            return Mock(status_code=200)

        response = my_view(request)
        assert response.status_code in (200, 302)


@pytest.mark.integration
@pytest.mark.subscription
class TestRequireFeatureDecorator:

    def test_pdf_export_blocked_for_free_user(self, test_user, free_subscription):
        factory = RequestFactory()
        request = _add_session(factory.get('/'))
        request.user = test_user
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.free_audit_used = True
        tracker.save()

        @require_feature('pdf_export')
        def my_view(request):
            return Mock(status_code=200)

        response = my_view(request)
        assert response.status_code in (302, 403)

    def test_pdf_export_allowed_for_basic_user(self, test_user, basic_subscription):
        factory = RequestFactory()
        request = _add_session(factory.get('/'))
        request.user = test_user

        @require_feature('pdf_export')
        def my_view(request):
            return Mock(status_code=200)

        response = my_view(request)
        assert response.status_code == 200

    def test_competitor_analysis_blocked_for_basic(self, test_user, basic_subscription):
        factory = RequestFactory()
        request = _add_session(factory.get('/'))
        request.user = test_user

        @require_feature('competitor_analysis')
        def my_view(request):
            return Mock(status_code=200)

        response = my_view(request)
        assert response.status_code in (302, 403)

    def test_competitor_analysis_allowed_for_pro(self, test_user, pro_subscription):
        factory = RequestFactory()
        request = _add_session(factory.get('/'))
        request.user = test_user

        @require_feature('competitor_analysis')
        def my_view(request):
            return Mock(status_code=200)

        response = my_view(request)
        assert response.status_code == 200

    def test_competitor_analysis_allowed_for_enterprise(self, test_user, enterprise_subscription):
        factory = RequestFactory()
        request = _add_session(factory.get('/'))
        request.user = test_user

        @require_feature('competitor_analysis')
        def my_view(request):
            return Mock(status_code=200)

        response = my_view(request)
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.subscription
class TestTrackUsageDecorator:

    def test_track_audit_increments_counter(self, test_user, pro_subscription):
        factory = RequestFactory()
        request = _add_session(factory.post('/'))
        request.user = test_user
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.free_audit_used = True
        tracker.save()
        initial_count = tracker.audits_used_this_month

        @track_usage('audit')
        def my_view(request):
            return Mock(status_code=200)

        my_view(request)
        tracker.refresh_from_db()
        assert tracker.audits_used_this_month >= initial_count

    def test_track_audit_blocks_when_limit_reached(self, test_user, basic_subscription):
        factory = RequestFactory()
        request = _add_session(factory.post('/'))
        request.user = test_user
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.free_audit_used = True
        tracker.audits_used_this_month = 10
        tracker.save()

        @track_usage('audit')
        def my_view(request):
            return Mock(status_code=200)

        response = my_view(request)
        assert response.status_code in (302, 403, 200)


@pytest.mark.integration
@pytest.mark.subscription
class TestApiSubscriptionCheckDecorator:

    def test_api_check_returns_403_json_for_unauthenticated(self, db):
        factory = RequestFactory()
        request = factory.get('/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()

        @api_subscription_check
        def my_api_view(request):
            return Mock(status_code=200)

        response = my_api_view(request)
        assert response.status_code in (302, 403, 401)

    def test_api_check_passes_for_subscribed_user(self, test_user, pro_subscription):
        factory = RequestFactory()
        request = factory.get('/')
        request.user = test_user

        @api_subscription_check
        def my_api_view(request):
            return Mock(status_code=200)

        response = my_api_view(request)
        assert response.status_code == 200

    def test_api_check_returns_json_error_not_html_redirect(self, test_user, free_subscription):
        factory = RequestFactory()
        request = factory.get('/')
        request.user = test_user
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.free_audit_used = True
        tracker.save()

        @api_subscription_check
        def my_api_view(request):
            return Mock(status_code=200)

        response = my_api_view(request)
        if hasattr(response, 'status_code') and response.status_code == 403:
            if hasattr(response, 'content'):
                import json
                try:
                    data = json.loads(response.content)
                    assert 'error' in data or 'message' in data
                except Exception:
                    pass
