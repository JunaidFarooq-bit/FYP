"""
Subscription Models for WebLift.

Manages user subscriptions, usage tracking, and feature limits.
"""
import json
import logging
from datetime import timedelta

from django.db import models
from django.db.models import F
from django.contrib.auth.models import User
from django.utils import timezone

logger = logging.getLogger(__name__)


class SubscriptionTier(models.Model):
    """
    Defines subscription tiers and their features.
    """
    TIER_CHOICES = [
        ('free', 'Free Trial'),
        ('basic', 'Basic'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    
    name = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    display_name = models.CharField(max_length=50)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Feature flags
    has_ai_suggestions = models.BooleanField(default=False)
    has_competitor_analysis = models.BooleanField(default=False)
    has_pdf_export = models.BooleanField(default=False)
    has_api_access = models.BooleanField(default=False)
    has_priority_support = models.BooleanField(default=False)
    
    # Usage limits (None = unlimited)
    max_audits_per_month = models.IntegerField(null=True, blank=True, help_text="None = unlimited")
    max_keywords_per_analysis = models.IntegerField(default=20)
    max_competitors_per_analysis = models.IntegerField(default=0)
    
    description = models.TextField(blank=True)
    features_list = models.JSONField(default=list, help_text="List of feature descriptions for UI")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['price_monthly']
        verbose_name = 'Subscription Tier'
        verbose_name_plural = 'Subscription Tiers'
    
    def __str__(self):
        return f"{self.display_name} (${self.price_monthly:.2f}/mo)"
    
    def save(self, *args, **kwargs):
        # Auto-generate features list if not provided
        if not self.features_list:
            self.features_list = self._generate_features_list()
        super().save(*args, **kwargs)
    
    def _generate_features_list(self):
        """Generate feature list for UI display."""
        features = []
        
        if self.max_audits_per_month is not None:
            features.append(f"{self.max_audits_per_month} SEO audits per month")
        else:
            features.append("Unlimited SEO audits")
        
        features.append(f"Up to {self.max_keywords_per_analysis} keywords per analysis")
        
        if self.has_ai_suggestions:
            features.append("AI-powered keyword suggestions")
        if self.has_competitor_analysis:
            features.append(f"Competitor analysis ({self.max_competitors_per_analysis} competitors)")
        if self.has_pdf_export:
            features.append("PDF report export")
        if self.has_api_access:
            features.append("API access")
        if self.has_priority_support:
            features.append("Priority support")
        
        return features


class Subscription(models.Model):
    """
    User's active subscription.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('trialing', 'Trialing'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('unpaid', 'Unpaid'),
        ('incomplete', 'Incomplete'),
        ('free_trial_used', 'Free Trial Used'),
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='subscription'
    )
    tier = models.ForeignKey(
        SubscriptionTier, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='subscriptions'
    )
    
    # Status
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='free_trial_used'
    )
    billing_cycle = models.CharField(
        max_length=10,
        choices=BILLING_CYCLE_CHOICES,
        default='monthly'
    )
    
    # Dates
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    
    # Payment info (Stripe)
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        tier_name = self.tier.display_name if self.tier else 'No Tier'
        return f"{self.user.username} - {tier_name} ({self.status})"
    
    def is_active(self):
        """Check if subscription is currently active."""
        if self.status in ['active', 'trialing']:
            if self.current_period_end and timezone.now() > self.current_period_end:
                return False
            return True
        return False
    
    def can_use_feature(self, feature_name):
        """Check if user can use a specific feature."""
        if not self.is_active():
            return False

        if not self.tier:
            return False
        
        feature_map = {
            'ai_suggestions': self.tier.has_ai_suggestions,
            'competitor_analysis': self.tier.has_competitor_analysis,
            'pdf_export': self.tier.has_pdf_export,
            'api_access': self.tier.has_api_access,
        }
        
        return feature_map.get(feature_name, False)
    
    def get_max_audits(self):
        """Get max audits allowed (None = unlimited)."""
        if not self.tier:
            return 0
        return self.tier.max_audits_per_month
    
    def get_max_keywords(self):
        """Get max keywords per analysis."""
        if not self.tier:
            return 0
        return self.tier.max_keywords_per_analysis
    
    def has_free_trial_available(self):
        """Check if user hasn't used their free audit yet."""
        if self.status != 'free_trial_used':
            return False
        try:
            return not self.user.usage_tracker.has_used_free_audit()
        except UsageTracker.DoesNotExist:
            # No tracker yet means no audits used — trial is available
            return True


class UsageTracker(models.Model):
    """
    Tracks monthly usage for each user.
    Resets at the start of each billing period.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='usage_tracker'
    )
    
    # Usage counters
    audits_used_this_month = models.IntegerField(default=0)
    keywords_generated_this_month = models.IntegerField(default=0)
    competitor_analyses_this_month = models.IntegerField(default=0)
    pdf_exports_this_month = models.IntegerField(default=0)
    
    # Free trial tracking
    free_audit_used = models.BooleanField(default=False)
    free_audit_used_at = models.DateTimeField(null=True, blank=True)
    
    # Reset tracking
    last_reset_date = models.DateTimeField(default=timezone.now)
    
    # History (optional, for analytics)
    usage_history = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Usage Tracker'
        verbose_name_plural = 'Usage Trackers'
        indexes = [
            models.Index(fields=['user', 'last_reset_date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.audits_used_this_month} audits this month"
    
    def reset_if_needed(self):
        """Reset counters if billing period has passed."""
        now = timezone.now()
        
        # Get user's subscription to check billing cycle
        try:
            subscription = self.user.subscription
            if subscription and subscription.current_period_end:
                # Reset based on subscription billing period end
                if now >= subscription.current_period_end:
                    # Archive current period to history
                    if not self.usage_history:
                        self.usage_history = {}
                    
                    period_key = subscription.current_period_start.strftime('%Y-%m-%d')
                    self.usage_history[period_key] = {
                        'audits': self.audits_used_this_month,
                        'keywords': self.keywords_generated_this_month,
                        'competitors': self.competitor_analyses_this_month,
                        'pdf_exports': self.pdf_exports_this_month,
                    }
                    
                    # Reset counters
                    self.audits_used_this_month = 0
                    self.keywords_generated_this_month = 0
                    self.competitor_analyses_this_month = 0
                    self.pdf_exports_this_month = 0
                    self.last_reset_date = now
                    self.save()
                    return
        except (Subscription.DoesNotExist, AttributeError) as e:
            # Fallback to monthly reset if no subscription found
            logger.debug(f"Subscription lookup failed, using monthly reset: {e}")
            pass
        
        # Fallback: Check if we need to reset (monthly) - for free tier users
        if self.last_reset_date.month != now.month or self.last_reset_date.year != now.year:
            # Archive current month to history
            if not self.usage_history:
                self.usage_history = {}
            
            month_key = self.last_reset_date.strftime('%Y-%m')
            self.usage_history[month_key] = {
                'audits': self.audits_used_this_month,
                'keywords': self.keywords_generated_this_month,
                'competitors': self.competitor_analyses_this_month,
                'pdf_exports': self.pdf_exports_this_month,
            }
            
            # Reset counters
            self.audits_used_this_month = 0
            self.keywords_generated_this_month = 0
            self.competitor_analyses_this_month = 0
            self.pdf_exports_this_month = 0
            self.last_reset_date = now
            self.save()
    
    def has_used_free_audit(self):
        """Check if free audit has been used."""
        return self.free_audit_used
    
    def use_free_audit(self):
        """Mark free audit as used."""
        self.free_audit_used = True
        self.free_audit_used_at = timezone.now()
        self.save()
    
    def record_audit(self):
        """Increment audit counter atomically to prevent race conditions."""
        self.reset_if_needed()
        # Use F() expression for atomic increment
        UsageTracker.objects.filter(pk=self.pk).update(
            audits_used_this_month=F('audits_used_this_month') + 1
        )
        # Refresh from database
        self.refresh_from_db()
    
    def record_keywords(self, count):
        """Increment keyword counter atomically."""
        self.reset_if_needed()
        UsageTracker.objects.filter(pk=self.pk).update(
            keywords_generated_this_month=F('keywords_generated_this_month') + count
        )
        self.refresh_from_db()
    
    def record_competitor_analysis(self):
        """Increment competitor analysis counter atomically."""
        self.reset_if_needed()
        UsageTracker.objects.filter(pk=self.pk).update(
            competitor_analyses_this_month=F('competitor_analyses_this_month') + 1
        )
        self.refresh_from_db()
    
    def record_pdf_export(self):
        """Increment PDF export counter atomically."""
        self.reset_if_needed()
        UsageTracker.objects.filter(pk=self.pk).update(
            pdf_exports_this_month=F('pdf_exports_this_month') + 1
        )
        self.refresh_from_db()
    
    def get_usage_summary(self):
        """Get current usage summary."""
        self.reset_if_needed()
        
        try:
            subscription = self.user.subscription
            tier = subscription.tier if subscription else None
        except Subscription.DoesNotExist:
            subscription = None
            tier = None
        
        return {
            'audits_used': self.audits_used_this_month,
            'audits_limit': tier.max_audits_per_month if tier else 1,
            'audits_remaining': (
                (tier.max_audits_per_month - self.audits_used_this_month) 
                if tier and tier.max_audits_per_month 
                else 'Unlimited'
            ),
            'keywords_used': self.keywords_generated_this_month,
            'free_audit_used': self.free_audit_used,
            'billing_period_end': subscription.current_period_end if subscription else None,
        }


class PaymentRecord(models.Model):
    """
    Record of payments made by users.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payments'
    )
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Stripe details
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    stripe_invoice_id = models.CharField(max_length=100, blank=True)
    
    # Description
    description = models.CharField(max_length=200, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment Record'
        verbose_name_plural = 'Payment Records'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - ${self.amount} ({self.status})"


class FeatureAccessLog(models.Model):
    """
    Log of feature access attempts (for analytics and debugging).
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='feature_access_logs'
    )
    feature_name = models.CharField(max_length=50)
    access_granted = models.BooleanField()
    reason = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Feature Access Log'
        verbose_name_plural = 'Feature Access Logs'
        indexes = [
            models.Index(fields=['user', 'feature_name', '-timestamp']),
        ]
    
    def __str__(self):
        status = "Granted" if self.access_granted else "Denied"
        return f"{self.user.username} - {self.feature_name} {status}"


class ManualPaymentSubmission(models.Model):
    """
    For manual bank transfer payments.
    Users submit proof of payment, admin verifies and activates subscription.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified - Activated'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='manual_payments'
    )
    
    # Plan details
    tier = models.ForeignKey(
        SubscriptionTier,
        on_delete=models.CASCADE,
        related_name='manual_payments'
    )
    billing_cycle = models.CharField(
        max_length=10,
        choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')],
        default='monthly'
    )
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # User-submitted information
    sender_name = models.CharField(max_length=200, help_text="Name on bank account")
    sender_account_last4 = models.CharField(max_length=4, blank=True, help_text="Last 4 digits of account")
    transaction_reference = models.CharField(max_length=100, blank=True, help_text="Transaction ID or reference number")
    payment_date = models.DateField(help_text="Date payment was sent")
    
    # Proof of payment (optional file upload)
    proof_document = models.FileField(
        upload_to='payment_proofs/%Y/%m/',
        blank=True,
        null=True,
        help_text="Receipt, screenshot, or proof of transfer"
    )
    notes = models.TextField(blank=True, help_text="Any additional notes from user")
    
    # Admin verification
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments'
    )
    verification_notes = models.TextField(blank=True, help_text="Admin notes about verification")
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Manual Payment Submission'
        verbose_name_plural = 'Manual Payment Submissions'
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.tier.display_name} - {self.get_status_display()}"
    
    def get_payment_instructions(self):
        """Get bank transfer instructions for this payment."""
        from django.conf import settings
        
        return {
            'bank_name': getattr(settings, 'BANK_NAME', 'Your Bank Name'),
            'account_name': getattr(settings, 'BANK_ACCOUNT_NAME', 'WebLift Inc.'),
            'account_number': getattr(settings, 'BANK_ACCOUNT_NUMBER', 'XXXX-XXXX-XXXX-1234'),
            'iban': getattr(settings, 'BANK_IBAN', 'XX00 0000 0000 0000 0000 00'),
            'swift_code': getattr(settings, 'BANK_SWIFT', 'XXXXXXXX'),
            'reference': f"WEBLIFT-{self.user.id}-{self.id}",
            'amount': self.amount,
            'currency': self.currency,
        }
