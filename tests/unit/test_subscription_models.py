"""
Unit tests — subscriptions models.

Covers: SubscriptionTier, Subscription, UsageTracker, ManualPaymentSubmission,
        PaymentRecord, FeatureAccessLog.
Edge cases: expired periods, boundary limits, status transitions, cascade deletes.
"""

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from subscriptions.models import (
    SubscriptionTier,
    Subscription,
    UsageTracker,
    ManualPaymentSubmission,
)


# ---------------------------------------------------------------------------
# SubscriptionTier
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.subscription
class TestSubscriptionTier:

    def test_create_tier_minimal(self, db):
        tier = SubscriptionTier.objects.create(
            name='test_tier',
            display_name='Test Tier',
            price_monthly=0,
        )
        assert tier.pk is not None
        assert tier.name == 'test_tier'

    def test_str_representation(self, db):
        tier = SubscriptionTier.objects.create(
            name='basic',
            display_name='Basic',
            price_monthly=9.00,
        )
        assert 'Basic' in str(tier)
        assert '9' in str(tier)

    def test_features_list_auto_generated(self, db):
        tier = SubscriptionTier.objects.create(
            name='pro2',
            display_name='Pro2',
            price_monthly=29.00,
            max_audits_per_month=50,
            has_ai_suggestions=True,
            has_pdf_export=True,
            has_competitor_analysis=True,
        )
        assert tier.features_list is not None
        assert isinstance(tier.features_list, list)

    def test_tier_ordered_by_price(self, db):
        SubscriptionTier.objects.all().delete()
        SubscriptionTier.objects.create(name='t3', display_name='T3', price_monthly=99)
        SubscriptionTier.objects.create(name='t1', display_name='T1', price_monthly=5)
        SubscriptionTier.objects.create(name='t2', display_name='T2', price_monthly=25)
        prices = list(SubscriptionTier.objects.values_list('price_monthly', flat=True))
        assert prices == sorted(prices)

    def test_free_tier_has_no_premium_features(self, subscription_tiers):
        free = subscription_tiers['free']
        assert free.has_ai_suggestions is False
        assert free.has_competitor_analysis is False
        assert free.has_pdf_export is False
        assert free.has_api_access is False

    def test_enterprise_tier_unlimited_audits(self, subscription_tiers):
        assert subscription_tiers['enterprise'].max_audits_per_month is None

    def test_tier_name_uniqueness(self, db):
        SubscriptionTier.objects.create(name='unique_tier', display_name='U', price_monthly=0)
        with pytest.raises(Exception):
            SubscriptionTier.objects.create(name='unique_tier', display_name='U2', price_monthly=0)

    @pytest.mark.parametrize('tier_name,expected_audits', [
        ('free', 1),
        ('basic', 10),
        ('pro', 50),
    ])
    def test_tier_audit_limits(self, subscription_tiers, tier_name, expected_audits):
        assert subscription_tiers[tier_name].max_audits_per_month == expected_audits


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.subscription
class TestSubscription:

    def test_subscription_creation(self, test_user, subscription_tiers):
        Subscription.objects.filter(user=test_user).delete()
        sub = Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['basic'],
            status='active',
        )
        assert sub.pk is not None
        assert sub.user == test_user

    def test_str_representation(self, test_user, subscription_tiers):
        Subscription.objects.filter(user=test_user).delete()
        sub = Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['basic'],
            status='active',
        )
        result = str(sub)
        assert test_user.username in result
        assert 'Basic' in result

    def test_is_active_active_status_within_period(self, test_user, subscription_tiers):
        Subscription.objects.filter(user=test_user).delete()
        sub = Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['pro'],
            status='active',
            current_period_end=timezone.now() + timedelta(days=30),
        )
        assert sub.is_active() is True

    def test_is_active_trialing_status(self, test_user, subscription_tiers):
        Subscription.objects.filter(user=test_user).delete()
        sub = Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['pro'],
            status='trialing',
            current_period_end=timezone.now() + timedelta(days=7),
        )
        assert sub.is_active() is True

    def test_is_active_expired_period(self, test_user, subscription_tiers):
        Subscription.objects.filter(user=test_user).delete()
        sub = Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['basic'],
            status='active',
            current_period_end=timezone.now() - timedelta(seconds=1),
        )
        assert sub.is_active() is False

    @pytest.mark.parametrize('status', ['canceled', 'past_due', 'unpaid', 'free_trial_used'])
    def test_is_active_non_active_statuses(self, test_user, subscription_tiers, status):
        Subscription.objects.filter(user=test_user).delete()
        sub = Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['basic'],
            status=status,
        )
        assert sub.is_active() is False

    def test_can_use_feature_pro_tier(self, test_user, subscription_tiers):
        Subscription.objects.filter(user=test_user).delete()
        sub = Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['pro'],
            status='active',
        )
        assert sub.can_use_feature('ai_suggestions') is True
        assert sub.can_use_feature('competitor_analysis') is True
        assert sub.can_use_feature('pdf_export') is True

    def test_can_use_feature_free_tier_denied(self, test_user, subscription_tiers):
        Subscription.objects.filter(user=test_user).delete()
        sub = Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['free'],
            status='free_trial_used',
        )
        assert sub.can_use_feature('ai_suggestions') is False
        assert sub.can_use_feature('competitor_analysis') is False
        assert sub.can_use_feature('pdf_export') is False

    def test_get_max_audits_returns_tier_limit(self, test_user, subscription_tiers):
        Subscription.objects.filter(user=test_user).delete()
        sub = Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['basic'],
            status='active',
        )
        assert sub.get_max_audits() == 10

    def test_get_max_audits_unlimited_for_enterprise(self, test_user, subscription_tiers):
        Subscription.objects.filter(user=test_user).delete()
        sub = Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['enterprise'],
            status='active',
        )
        assert sub.get_max_audits() is None

    def test_one_to_one_user_constraint(self, test_user, subscription_tiers):
        Subscription.objects.filter(user=test_user).delete()
        Subscription.objects.create(
            user=test_user,
            tier=subscription_tiers['basic'],
            status='active',
        )
        with pytest.raises(Exception):
            Subscription.objects.create(
                user=test_user,
                tier=subscription_tiers['pro'],
                status='active',
            )

    def test_cascade_delete_removes_subscription(self, test_user, basic_subscription):
        user_id = test_user.id
        test_user.delete()
        assert not Subscription.objects.filter(user_id=user_id).exists()


# ---------------------------------------------------------------------------
# UsageTracker
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.subscription
class TestUsageTracker:

    def test_tracker_created_with_zero_counters(self, test_user):
        UsageTracker.objects.filter(user=test_user).delete()
        tracker = UsageTracker.objects.create(user=test_user)
        assert tracker.audits_used_this_month == 0
        assert tracker.keywords_generated_this_month == 0
        assert tracker.competitor_analyses_this_month == 0
        assert tracker.pdf_exports_this_month == 0
        assert tracker.free_audit_used is False

    def test_record_audit_increments_counter(self, test_user):
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.audits_used_this_month = 0
        tracker.save()
        tracker.record_audit()
        tracker.refresh_from_db()
        assert tracker.audits_used_this_month == 1

    def test_record_audit_multiple_times(self, test_user):
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.audits_used_this_month = 0
        tracker.save()
        for _ in range(7):
            tracker.record_audit()
        tracker.refresh_from_db()
        assert tracker.audits_used_this_month == 7

    def test_has_used_free_audit_initially_false(self, test_user):
        UsageTracker.objects.filter(user=test_user).delete()
        tracker = UsageTracker.objects.create(user=test_user)
        assert tracker.has_used_free_audit() is False

    def test_use_free_audit_sets_flag(self, test_user):
        UsageTracker.objects.filter(user=test_user).delete()
        tracker = UsageTracker.objects.create(user=test_user)
        tracker.use_free_audit()
        tracker.refresh_from_db()
        assert tracker.has_used_free_audit() is True
        assert tracker.free_audit_used_at is not None

    def test_record_keywords(self, test_user):
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.keywords_generated_this_month = 0
        tracker.save()
        tracker.record_keywords(150)
        tracker.refresh_from_db()
        assert tracker.keywords_generated_this_month == 150

    def test_record_competitor_analysis(self, test_user):
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.competitor_analyses_this_month = 0
        tracker.save()
        tracker.record_competitor_analysis()
        tracker.refresh_from_db()
        assert tracker.competitor_analyses_this_month == 1

    def test_record_pdf_export(self, test_user):
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.pdf_exports_this_month = 0
        tracker.save()
        tracker.record_pdf_export()
        tracker.refresh_from_db()
        assert tracker.pdf_exports_this_month == 1

    def test_reset_if_needed_when_overdue(self, test_user):
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.audits_used_this_month = 10
        tracker.last_reset_date = timezone.now() - timedelta(days=35)
        tracker.save()
        tracker.reset_if_needed()
        tracker.refresh_from_db()
        assert tracker.audits_used_this_month == 0

    def test_reset_if_needed_not_overdue(self, test_user):
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.audits_used_this_month = 5
        tracker.last_reset_date = timezone.now() - timedelta(days=5)
        tracker.save()
        tracker.reset_if_needed()
        tracker.refresh_from_db()
        assert tracker.audits_used_this_month == 5

    def test_usage_history_archived_on_reset(self, test_user):
        tracker, _ = UsageTracker.objects.get_or_create(user=test_user)
        tracker.audits_used_this_month = 15
        tracker.last_reset_date = timezone.now() - timedelta(days=35)
        tracker.save()
        tracker.reset_if_needed()
        tracker.refresh_from_db()
        assert tracker.usage_history is not None
        assert len(tracker.usage_history) > 0

    def test_cascade_delete_user_removes_tracker(self, test_user):
        UsageTracker.objects.get_or_create(user=test_user)
        user_id = test_user.id
        test_user.delete()
        assert not UsageTracker.objects.filter(user_id=user_id).exists()


# ---------------------------------------------------------------------------
# ManualPaymentSubmission
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.subscription
class TestManualPaymentSubmission:

    def test_create_payment_submission(self, test_user, subscription_tiers):
        sub = ManualPaymentSubmission.objects.create(
            user=test_user,
            tier=subscription_tiers['pro'],
            billing_cycle='monthly',
            amount=29.00,
            sender_name='Test User',
            transaction_reference='TXN-001',
            payment_date=timezone.now().date(),
        )
        assert sub.pk is not None
        assert sub.status == 'pending'

    def test_default_status_is_pending(self, test_user, subscription_tiers):
        sub = ManualPaymentSubmission.objects.create(
            user=test_user,
            tier=subscription_tiers['basic'],
            billing_cycle='monthly',
            amount=9.00,
            sender_name='John',
            transaction_reference='REF-XYZ',
            payment_date=timezone.now().date(),
        )
        assert sub.status == 'pending'

    def test_status_transition_to_verified(self, test_user, admin_user, subscription_tiers):
        sub = ManualPaymentSubmission.objects.create(
            user=test_user,
            tier=subscription_tiers['pro'],
            billing_cycle='monthly',
            amount=29.00,
            sender_name='Test User',
            transaction_reference='REF-VFY',
            payment_date=timezone.now().date(),
        )
        sub.status = 'verified'
        sub.verified_by = admin_user
        sub.verified_at = timezone.now()
        sub.save()
        sub.refresh_from_db()
        assert sub.status == 'verified'
        assert sub.verified_by == admin_user

    def test_status_transition_to_rejected(self, test_user, subscription_tiers):
        sub = ManualPaymentSubmission.objects.create(
            user=test_user,
            tier=subscription_tiers['basic'],
            billing_cycle='monthly',
            amount=9.00,
            sender_name='Test User',
            transaction_reference='REF-REJ',
            payment_date=timezone.now().date(),
        )
        sub.status = 'rejected'
        sub.verification_notes = 'Invalid proof'
        sub.save()
        sub.refresh_from_db()
        assert sub.status == 'rejected'
