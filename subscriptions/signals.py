"""
Subscription Signals for WebLift.

Automatically creates subscription and usage tracker for new users.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Subscription, SubscriptionTier, UsageTracker
from .services.subscription_service import SubscriptionService


@receiver(post_save, sender=User)
def create_user_subscription(sender, instance, created, **kwargs):
    """
    Create default subscription and usage tracker when a new user registers.
    """
    if created:
        # Ensure default tiers exist
        SubscriptionService.create_default_tiers()
        
        # Create subscription
        SubscriptionService.create_default_subscription(instance)
        
        # Usage tracker is created by the above call, but ensure it exists
        UsageTracker.objects.get_or_create(user=instance)
