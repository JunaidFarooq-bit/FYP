"""
Subscription Service for WebLift.

Handles subscription logic, usage tracking, and tier management.
"""
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from ..models import Subscription, SubscriptionTier, UsageTracker


class SubscriptionService:
    """Service class for subscription management."""
    
    CACHE_TIMEOUT = 300  # 5 minutes
    
    @staticmethod
    def create_default_tiers():
        """Create default subscription tiers if they don't exist."""
        tiers = [
            {
                'name': 'free',
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
                'description': 'One-time free SEO audit to try WebLift',
            },
            {
                'name': 'basic',
                'display_name': 'Basic',
                'price_monthly': 9,
                'price_yearly': 90,  # 2 months free
                'max_audits_per_month': 10,
                'max_keywords_per_analysis': 50,
                'max_competitors_per_analysis': 0,
                'has_ai_suggestions': True,
                'has_competitor_analysis': False,
                'has_pdf_export': True,
                'has_api_access': False,
                'description': 'Perfect for small websites and bloggers',
            },
            {
                'name': 'pro',
                'display_name': 'Pro',
                'price_monthly': 29,
                'price_yearly': 290,  # 2 months free
                'max_audits_per_month': 50,
                'max_keywords_per_analysis': 200,
                'max_competitors_per_analysis': 3,
                'has_ai_suggestions': True,
                'has_competitor_analysis': True,
                'has_pdf_export': True,
                'has_api_access': True,
                'has_priority_support': True,
                'description': 'For professionals and growing businesses',
            },
            {
                'name': 'enterprise',
                'display_name': 'Enterprise',
                'price_monthly': 99,
                'price_yearly': 990,  # 2 months free
                'max_audits_per_month': None,  # Unlimited
                'max_keywords_per_analysis': 500,
                'max_competitors_per_analysis': 10,
                'has_ai_suggestions': True,
                'has_competitor_analysis': True,
                'has_pdf_export': True,
                'has_api_access': True,
                'has_priority_support': True,
                'description': 'Unlimited power for agencies and large teams',
            },
        ]
        
        created_tiers = []
        for tier_data in tiers:
            tier, created = SubscriptionTier.objects.get_or_create(
                name=tier_data['name'],
                defaults=tier_data
            )
            if created:
                created_tiers.append(tier.name)
        
        return created_tiers
    
    @staticmethod
    def create_default_subscription(user):
        """Create a default subscription for a new user (free trial status)."""
        # Ensure free tier exists
        free_tier, _ = SubscriptionTier.objects.get_or_create(
            name='free',
            defaults={
                'display_name': 'Free Trial',
                'max_audits_per_month': 1,
                'max_keywords_per_analysis': 20,
            }
        )
        
        subscription, created = Subscription.objects.get_or_create(
            user=user,
            defaults={
                'tier': free_tier,
                'status': 'free_trial_used',
            }
        )
        
        # Create usage tracker
        UsageTracker.objects.get_or_create(user=user)
        
        return subscription
    
    @staticmethod
    def can_use_feature(user, feature_type, count=1):
        """
        Check if user can use a feature.
        
        Returns:
            tuple: (can_use: bool, reason: str)
        """
        try:
            subscription = user.subscription
        except Subscription.DoesNotExist:
            subscription = SubscriptionService.create_default_subscription(user)

        try:
            tracker = user.usage_tracker
        except UsageTracker.DoesNotExist:
            tracker = UsageTracker.objects.create(user=user)
        
        # Reset usage counters if needed
        tracker.reset_if_needed()
        
        # Check free trial for audits
        if feature_type == 'audit':
            if not tracker.has_used_free_audit():
                return True, "Free trial available"
        
        # Check active subscription
        if not subscription.is_active():
            return False, "Active subscription required. Please subscribe to continue."
        
        tier = subscription.tier
        if not tier:
            return False, "No subscription tier found."
        
        # Check specific limits
        if feature_type == 'audit':
            if tier.max_audits_per_month is not None:
                if tracker.audits_used_this_month + count > tier.max_audits_per_month:
                    remaining = tier.max_audits_per_month - tracker.audits_used_this_month
                    return False, f"Audit limit reached. {remaining} audits remaining this month. Upgrade your plan!"
        
        elif feature_type == 'keywords':
            # This is per-analysis limit, checked at analysis time
            pass
        
        elif feature_type == 'competitor':
            if not tier.has_competitor_analysis:
                return False, "Competitor analysis not available on your plan. Upgrade to Pro or Enterprise!"
        
        elif feature_type == 'pdf_export':
            if not tier.has_pdf_export:
                return False, "PDF export not available on your plan. Upgrade to Basic or higher!"
        
        return True, "Access granted"
    
    @staticmethod
    def upgrade_subscription(user, tier_name, billing_cycle='monthly'):
        """Upgrade user's subscription to a new tier."""
        try:
            subscription = user.subscription
        except Subscription.DoesNotExist:
            subscription = SubscriptionService.create_default_subscription(user)
        
        try:
            new_tier = SubscriptionTier.objects.get(name=tier_name, is_active=True)
        except SubscriptionTier.DoesNotExist:
            raise ValueError(f"Tier '{tier_name}' not found")
        
        subscription.tier = new_tier
        subscription.billing_cycle = billing_cycle
        subscription.status = 'active'
        subscription.current_period_start = timezone.now()
        
        if billing_cycle == 'yearly':
            subscription.current_period_end = timezone.now() + timedelta(days=365)
        else:
            subscription.current_period_end = timezone.now() + timedelta(days=30)
        
        subscription.save()
        
        # Invalidate cached summary so UI reflects the upgrade immediately
        SubscriptionService.invalidate_user_cache(user.id)
        
        return subscription
    
    @staticmethod
    def cancel_subscription(user):
        """Cancel user's subscription at period end."""
        try:
            subscription = user.subscription
            subscription.status = 'canceled'
            subscription.canceled_at = timezone.now()
            subscription.save()
            # Invalidate cached summary so UI reflects cancellation immediately
            SubscriptionService.invalidate_user_cache(user.id)
            return subscription
        except Subscription.DoesNotExist:
            return None
    
    @staticmethod
    def get_subscription_summary(user):
        """Get full subscription summary for user with query optimization."""
        cache_key = f"subscription_summary:{user.id}"
        
        # Try cache first
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Optimized query with select_related to avoid N+1
        try:
            subscription = Subscription.objects.select_related('tier').get(user=user)
        except Subscription.DoesNotExist:
            subscription = SubscriptionService.create_default_subscription(user)
            subscription = Subscription.objects.select_related('tier').get(user=user)
        
        try:
            tracker = UsageTracker.objects.get(user=user)
        except UsageTracker.DoesNotExist:
            tracker = UsageTracker.objects.create(user=user)
        
        tracker.reset_if_needed()
        
        tier = subscription.tier
        
        result = {
            'tier': {
                'name': tier.name if tier else 'free',
                'display_name': tier.display_name if tier else 'Free Trial',
                'price': tier.price_monthly if tier else 0,
            },
            'status': subscription.status,
            'is_active': subscription.is_active(),
            'current_period_end': subscription.current_period_end,
            'days_remaining': (
                (subscription.current_period_end - timezone.now()).days
                if subscription.current_period_end else 0
            ),
            'usage': {
                'audits_used': (
                    (1 if tracker.free_audit_used else 0)
                    if (tier and tier.name == 'free')
                    else tracker.audits_used_this_month
                ),
                'audits_limit': tier.max_audits_per_month if tier else 1,
                'audits_remaining': (
                    (0 if tracker.free_audit_used else 1)
                    if (tier and tier.name == 'free')
                    else (
                        (tier.max_audits_per_month - tracker.audits_used_this_month)
                        if tier and tier.max_audits_per_month is not None
                        else 'Unlimited'
                    )
                ),
                'free_audit_used': tracker.free_audit_used,
            },
            'features': {
                'ai_suggestions': tier.has_ai_suggestions if tier else False,
                'competitor_analysis': tier.has_competitor_analysis if tier else False,
                'pdf_export': tier.has_pdf_export if tier else False,
                'api_access': tier.has_api_access if tier else False,
            }
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, result, SubscriptionService.CACHE_TIMEOUT)
        
        return result
    
    @staticmethod
    def invalidate_user_cache(user_id):
        """Invalidate subscription cache for user."""
        cache.delete(f"subscription_summary:{user_id}")
