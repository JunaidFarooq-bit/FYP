from django.contrib import admin
from .models import (
    SubscriptionTier, 
    Subscription, 
    UsageTracker, 
    PaymentRecord,
    FeatureAccessLog,
    ManualPaymentSubmission,
)


@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    list_display = [
        'display_name', 'name', 'price_monthly', 'price_yearly',
        'max_audits_per_month', 'max_keywords_per_analysis',
        'is_active'
    ]
    list_filter = ['is_active', 'has_ai_suggestions', 'has_competitor_analysis']
    search_fields = ['name', 'display_name']
    ordering = ['price_monthly']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'tier', 'status', 'is_active_display',
        'current_period_end', 'created_at'
    ]
    list_filter = ['status', 'tier', 'billing_cycle']
    search_fields = ['user__username', 'user__email', 'stripe_customer_id']
    date_hierarchy = 'created_at'
    
    def is_active_display(self, obj):
        return obj.is_active()
    is_active_display.boolean = True
    is_active_display.short_description = 'Active'


@admin.register(UsageTracker)
class UsageTrackerAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'audits_used_this_month', 'free_audit_used',
        'last_reset_date'
    ]
    list_filter = ['free_audit_used']
    search_fields = ['user__username', 'user__email']


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'amount', 'currency', 'status', 'created_at'
    ]
    list_filter = ['status', 'currency']
    search_fields = ['user__username', 'stripe_payment_intent_id']
    date_hierarchy = 'created_at'


@admin.register(FeatureAccessLog)
class FeatureAccessLogAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'feature_name', 'access_granted', 'timestamp'
    ]
    list_filter = ['access_granted', 'feature_name']
    search_fields = ['user__username', 'feature_name']
    date_hierarchy = 'timestamp'


@admin.register(ManualPaymentSubmission)
class ManualPaymentSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'tier', 'amount', 'sender_name', 'status', 
        'created_at', 'verified_at'
    ]
    list_filter = ['status', 'tier', 'billing_cycle']
    search_fields = ['user__username', 'user__email', 'sender_name', 'transaction_reference']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at', 'verified_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'tier', 'billing_cycle', 'amount', 'currency')
        }),
        ('Payment Details', {
            'fields': ('sender_name', 'sender_account_last4', 'transaction_reference', 'payment_date')
        }),
        ('Proof & Notes', {
            'fields': ('proof_document', 'notes')
        }),
        ('Verification', {
            'fields': ('status', 'verified_by', 'verification_notes', 'verified_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['verify_payments', 'reject_payments']
    
    def verify_payments(self, request, queryset):
        """Bulk verify selected payments."""
        from django.utils import timezone
        from .services.subscription_service import SubscriptionService
        
        verified_count = 0
        for payment in queryset.filter(status='pending'):
            payment.status = 'verified'
            payment.verified_by = request.user
            payment.verified_at = timezone.now()
            payment.save()
            
            # Activate subscription
            SubscriptionService.upgrade_subscription(
                payment.user,
                payment.tier.name,
                payment.billing_cycle
            )
            verified_count += 1
        
        self.message_user(request, f'{verified_count} payments verified and subscriptions activated.')
    verify_payments.short_description = "Verify selected payments and activate subscriptions"
    
    def reject_payments(self, request, queryset):
        """Bulk reject selected payments."""
        from django.utils import timezone
        
        rejected_count = queryset.filter(status='pending').update(
            status='rejected',
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(request, f'{rejected_count} payments rejected.')
    reject_payments.short_description = "Reject selected payments"
