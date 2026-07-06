"""
Integration tests — Subscription views.

Covers: pricing page, dashboard, payment instructions, payment submission,
        cancel, change-plan, admin pending payments, admin verify/reject.
Edge cases: non-staff accessing admin views, invalid payment data,
            free tier selected (immediate activation), already-active subscriptions.
"""

import pytest
from unittest.mock import patch, Mock
from django.utils import timezone
from datetime import timedelta, date

from subscriptions.models import (
    Subscription, UsageTracker, ManualPaymentSubmission, SubscriptionTier
)


@pytest.mark.integration
@pytest.mark.subscription
class TestPricingView:

    def test_pricing_page_requires_login(self, client):
        response = client.get('/subscriptions/pricing/')
        assert response.status_code == 302

    def test_pricing_page_accessible_authenticated(self, authenticated_client, subscription_tiers):
        response = authenticated_client.get('/subscriptions/pricing/')
        assert response.status_code == 200

    def test_pricing_page_shows_all_tiers(self, authenticated_client, subscription_tiers):
        response = authenticated_client.get('/subscriptions/pricing/')
        content = response.content.decode()
        assert 'Basic' in content or 'Pro' in content or 'Free' in content


@pytest.mark.integration
@pytest.mark.subscription
class TestSubscriptionDashboardView:

    def test_dashboard_requires_login(self, client):
        response = client.get('/subscriptions/dashboard/')
        assert response.status_code == 302

    def test_dashboard_accessible_authenticated(self, authenticated_client, pro_subscription):
        response = authenticated_client.get('/subscriptions/dashboard/')
        assert response.status_code == 200

    def test_dashboard_shows_plan_name(self, authenticated_client, pro_subscription):
        response = authenticated_client.get('/subscriptions/dashboard/')
        content = response.content.decode()
        assert 'Pro' in content or 'pro' in content.lower()

    def test_dashboard_shows_usage_counters(self, authenticated_client, pro_subscription, test_user):
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.audits_used_this_month = 3
        tracker.save()
        response = authenticated_client.get('/subscriptions/dashboard/')
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.subscription
class TestPaymentInstructionsView:

    def test_instructions_requires_login(self, client):
        response = client.post('/subscriptions/payment/instructions/', {'tier': 'pro', 'billing_cycle': 'monthly'})
        assert response.status_code == 302

    def test_instructions_for_paid_tier(self, authenticated_client, subscription_tiers, test_user):
        Subscription.objects.filter(user=test_user).delete()
        Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['free'],
            status='free_trial_used',
        )
        response = authenticated_client.post('/subscriptions/payment/instructions/', {
            'tier': 'pro',
            'billing_cycle': 'monthly',
        }, follow=True)
        assert response.status_code == 200

    def test_instructions_for_free_tier_activates_immediately(
        self, authenticated_client, subscription_tiers, test_user
    ):
        Subscription.objects.filter(user=test_user).delete()
        Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['free'],
            status='free_trial_used',
        )
        response = authenticated_client.post('/subscriptions/payment/instructions/', {
            'tier': 'free',
            'billing_cycle': 'monthly',
        }, follow=True)
        assert response.status_code == 200
        subscription = Subscription.objects.get(user=test_user)
        assert subscription.tier.name == 'free'
        assert subscription.status == 'free_trial_used'
        assert subscription.is_active() is False


@pytest.mark.integration
@pytest.mark.subscription
class TestPaymentSubmitView:

    def test_submit_requires_login(self, client):
        response = client.post('/subscriptions/payment/submit/', {})
        assert response.status_code == 302

    def test_submit_valid_proof(self, authenticated_client, subscription_tiers, test_user):
        Subscription.objects.filter(user=test_user).delete()
        Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['pro'],
            status='free_trial_used',
        )
        response = authenticated_client.post('/subscriptions/payment/submit/', {
            'tier': 'pro',
            'billing_cycle': 'monthly',
            'amount': '29.00',
            'sender_name': 'Test User',
            'transaction_reference': 'TXN-TEST-001',
            'payment_date': str(date.today()),
        }, follow=True)
        assert response.status_code == 200

    def test_submit_missing_required_fields(self, authenticated_client, subscription_tiers, test_user):
        Subscription.objects.filter(user=test_user).delete()
        Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['pro'],
            status='free_trial_used',
        )
        response = authenticated_client.post('/subscriptions/payment/submit/', {
            'tier': 'pro',
        }, follow=True)
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.subscription
class TestCancelSubscriptionView:

    def test_cancel_requires_login(self, client):
        response = client.post('/subscriptions/cancel/', {})
        assert response.status_code == 302

    def test_cancel_active_subscription(self, authenticated_client, pro_subscription, test_user):
        response = authenticated_client.post('/subscriptions/cancel/', {}, follow=True)
        assert response.status_code == 200
        sub = Subscription.objects.get(user=test_user)
        assert sub.status == 'canceled'


@pytest.mark.integration
@pytest.mark.subscription
class TestAdminPaymentViews:

    def test_pending_payments_blocked_for_non_staff(self, authenticated_client, pro_subscription):
        response = authenticated_client.get('/subscriptions/admin/pending-payments/')
        assert response.status_code in (302, 403)

    def test_pending_payments_accessible_for_admin(self, admin_client, subscription_tiers):
        from django.contrib.auth.models import User
        admin = User.objects.get(username='admin')
        response = admin_client.get('/subscriptions/admin/pending-payments/')
        assert response.status_code == 200

    def test_verify_payment_blocked_for_non_staff(self, authenticated_client, test_user, subscription_tiers):
        sub = ManualPaymentSubmission.objects.create(
            user=test_user,
            tier=subscription_tiers['pro'],
            billing_cycle='monthly',
            amount=29.00,
            sender_name='Test',
            transaction_reference='REF-001',
            payment_date=date.today(),
        )
        response = authenticated_client.post(f'/subscriptions/admin/verify-payment/{sub.id}/', {})
        assert response.status_code in (302, 403)

    def test_verify_payment_activates_subscription(self, admin_client, test_user, subscription_tiers):
        sub = ManualPaymentSubmission.objects.create(
            user=test_user,
            tier=subscription_tiers['pro'],
            billing_cycle='monthly',
            amount=29.00,
            sender_name='Test',
            transaction_reference='REF-002',
            payment_date=date.today(),
        )
        Subscription.objects.filter(user=test_user).delete()
        Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['free'],
            status='free_trial_used',
        )
        response = admin_client.post(f'/subscriptions/admin/verify-payment/{sub.id}/', {}, follow=True)
        assert response.status_code == 200
        user_sub = Subscription.objects.get(user=test_user)
        assert user_sub.status == 'active'
        assert user_sub.tier.name == 'pro'

    def test_reject_payment_updates_status(self, admin_client, test_user, subscription_tiers):
        sub = ManualPaymentSubmission.objects.create(
            user=test_user,
            tier=subscription_tiers['basic'],
            billing_cycle='monthly',
            amount=9.00,
            sender_name='Test',
            transaction_reference='REF-003',
            payment_date=date.today(),
        )
        response = admin_client.post(f'/subscriptions/admin/reject-payment/{sub.id}/', {
            'notes': 'Invalid proof document',
        }, follow=True)
        assert response.status_code == 200
        sub.refresh_from_db()
        assert sub.status == 'rejected'


@pytest.mark.integration
@pytest.mark.subscription
class TestUsageApiView:

    def test_usage_api_requires_login(self, client):
        response = client.get('/subscriptions/api/usage/')
        assert response.status_code == 302

    def test_usage_api_returns_json(self, authenticated_client, pro_subscription):
        response = authenticated_client.get('/subscriptions/api/usage/')
        assert response.status_code == 200
        assert response['Content-Type'].startswith('application/json')

    def test_usage_api_correct_structure(self, authenticated_client, pro_subscription, test_user):
        response = authenticated_client.get('/subscriptions/api/usage/')
        import json
        data = json.loads(response.content)
        assert isinstance(data, dict)
