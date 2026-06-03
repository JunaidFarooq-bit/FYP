"""
Template tags for subscription functionality.
"""
from django import template
from subscriptions.models import Subscription
from subscriptions.services.subscription_service import SubscriptionService

register = template.Library()


@register.filter
def has_active_subscription(user):
    """Check if user has active subscription."""
    try:
        return user.subscription.is_active()
    except (AttributeError, Subscription.DoesNotExist):
        return False


@register.filter
def can_use_feature(user, feature_name):
    """Check if user can use a specific feature."""
    try:
        return user.subscription.can_use_feature(feature_name)
    except (AttributeError, Subscription.DoesNotExist):
        return False


@register.simple_tag
def get_usage_summary(user):
    """Get usage summary for user."""
    return SubscriptionService.get_subscription_summary(user)


@register.filter
def subscription_tier(user):
    """Get user's subscription tier name."""
    try:
        tier = user.subscription.tier
        return tier.display_name if tier else 'Free Trial'
    except (AttributeError, Subscription.DoesNotExist):
        return 'Free Trial'
