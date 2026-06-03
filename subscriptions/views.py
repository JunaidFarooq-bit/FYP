"""
Subscription Views for WebLift.

Handles subscription management with MANUAL BANK TRANSFER payments.
Users pay via bank transfer, admin verifies, subscription activates.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_page
import html
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.conf import settings
from .models import Subscription, SubscriptionTier, PaymentRecord, ManualPaymentSubmission
from .services.subscription_service import SubscriptionService


def get_sanitized_bank_details():
    """Get sanitized bank details for safe display."""
    return {
        'name': escape(getattr(settings, 'BANK_NAME', 'Your Bank Name')),
        'account_name': escape(getattr(settings, 'BANK_ACCOUNT_NAME', 'WebLift Inc.')),
        'account_number': escape(getattr(settings, 'BANK_ACCOUNT_NUMBER', 'XXXX-XXXX-XXXX-1234')),
        'iban': escape(getattr(settings, 'BANK_IBAN', 'XX00 0000 0000 0000 0000 00')),
        'swift_code': escape(getattr(settings, 'BANK_SWIFT', 'XXXXXXXX')),
        'branch': escape(getattr(settings, 'BANK_BRANCH', 'Main Branch')),
        'country': escape(getattr(settings, 'BANK_COUNTRY', 'Your Country')),
    }


# Bank transfer settings from environment (kept for compatibility)
BANK_DETAILS = get_sanitized_bank_details()


@login_required
def pricing(request):
    """Display pricing page with all subscription tiers."""
    # Ensure tiers exist
    SubscriptionService.create_default_tiers()
    
    tiers = SubscriptionTier.objects.filter(is_active=True).order_by('price_monthly')
    
    # Get user's current subscription
    try:
        subscription = request.user.subscription
        current_tier = subscription.tier
    except Subscription.DoesNotExist:
        subscription = None
        current_tier = None
    
    # Get usage summary
    usage_summary = SubscriptionService.get_subscription_summary(request.user)
    
    # Check for pending manual payments
    pending_payments = ManualPaymentSubmission.objects.filter(
        user=request.user,
        status='pending'
    )
    
    context = {
        'tiers': tiers,
        'current_tier': current_tier,
        'subscription': subscription,
        'usage': usage_summary,
        'bank_details': BANK_DETAILS,
        'pending_payments': pending_payments,
    }
    
    return render(request, 'subscriptions/pricing.html', context)


@login_required
def subscription_dashboard(request):
    """User's subscription management dashboard."""
    # Get or create subscription with tier info (optimized query)
    try:
        subscription = Subscription.objects.select_related('tier').get(user=request.user)
    except Subscription.DoesNotExist:
        subscription = SubscriptionService.create_default_subscription(request.user)
    
    # Get usage summary
    usage_summary = SubscriptionService.get_subscription_summary(request.user)
    
    # Get payment history (manual payments)
    manual_payments = ManualPaymentSubmission.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    context = {
        'subscription': subscription,
        'usage': usage_summary,
        'manual_payments': manual_payments,
        'bank_details': BANK_DETAILS,
    }
    
    return render(request, 'subscriptions/dashboard.html', context)


@login_required
def payment_instructions(request):
    """Show bank transfer instructions and payment submission form."""
    if request.method != 'POST':
        return redirect('subscriptions:pricing')
    
    tier_name = request.POST.get('tier')
    billing_cycle = request.POST.get('billing', 'monthly')
    
    try:
        tier = SubscriptionTier.objects.get(name=tier_name, is_active=True)
    except SubscriptionTier.DoesNotExist:
        messages.error(request, "Invalid subscription tier.")
        return redirect('subscriptions:pricing')
    
    # Get price
    price = tier.price_yearly if billing_cycle == 'yearly' else tier.price_monthly
    
    if price == 0:
        # Free tier - just activate
        SubscriptionService.upgrade_subscription(request.user, tier_name, billing_cycle)
        messages.success(request, f"You're now on the {tier.display_name} plan!")
        return redirect('subscriptions:dashboard')
    
    # Generate unique reference code
    reference = f"WEBLIFT-{request.user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    
    context = {
        'tier': tier,
        'billing_cycle': billing_cycle,
        'amount': price,
        'bank_details': get_sanitized_bank_details(),  # Use sanitized function
        'reference': reference,
    }
    
    return render(request, 'subscriptions/payment_instructions.html', context)


@login_required
def submit_payment_proof(request):
    """Handle payment proof submission from users."""
    if request.method != 'POST':
        return redirect('subscriptions:pricing')
    
    tier_name = request.POST.get('tier')
    billing_cycle = request.POST.get('billing_cycle')
    amount = request.POST.get('amount')
    
    # Input validation
    if not tier_name or not billing_cycle or not amount:
        messages.error(request, "Missing required payment information.")
        return redirect('subscriptions:pricing')
    
    # Validate billing cycle
    if billing_cycle not in ['monthly', 'yearly']:
        messages.error(request, "Invalid billing cycle selected.")
        return redirect('subscriptions:pricing')
    
    # Validate amount format
    try:
        amount_float = float(amount)
        if amount_float <= 0:
            messages.error(request, "Invalid payment amount.")
            return redirect('subscriptions:pricing')
    except ValueError:
        messages.error(request, "Invalid payment amount format.")
        return redirect('subscriptions:pricing')
    
    # Validate sender name (required)
    sender_name = request.POST.get('sender_name', '').strip()
    if not sender_name or len(sender_name) < 2:
        messages.error(request, "Sender name is required and must be at least 2 characters.")
        return redirect('subscriptions:pricing')
    
    # Validate account last 4 digits (optional but if provided must be 4 digits)
    sender_account_last4 = request.POST.get('sender_account_last4', '').strip()
    if sender_account_last4 and (not sender_account_last4.isdigit() or len(sender_account_last4) != 4):
        messages.error(request, "Account last 4 digits must be exactly 4 numbers.")
        return redirect('subscriptions:pricing')
    
    # Validate transaction reference (required)
    transaction_reference = request.POST.get('transaction_reference', '').strip()
    if not transaction_reference or len(transaction_reference) < 3:
        messages.error(request, "Transaction reference is required and must be at least 3 characters.")
        return redirect('subscriptions:pricing')
    
    # Validate payment date (required)
    payment_date = request.POST.get('payment_date')
    if not payment_date:
        messages.error(request, "Payment date is required.")
        return redirect('subscriptions:pricing')
    
    try:
        tier = get_object_or_404(SubscriptionTier, name=tier_name, is_active=True)
    except Exception:
        messages.error(request, "Invalid plan selected.")
        return redirect('subscriptions:pricing')
    
    # Create payment submission record
    payment_submission = ManualPaymentSubmission.objects.create(
        user=request.user,
        tier=tier,
        billing_cycle=billing_cycle,
        amount=amount_float,  # Use validated float
        sender_name=sender_name,
        sender_account_last4=sender_account_last4,
        transaction_reference=transaction_reference,
        payment_date=payment_date,
        notes=request.POST.get('notes', '').strip()[:500],  # Limit notes length
    )
    
    # Handle file upload if provided
    if request.FILES.get('proof_document'):
        payment_submission.proof_document = request.FILES['proof_document']
        payment_submission.save()
    
    messages.success(
        request,
        "Payment proof submitted successfully! We'll verify your payment and activate your subscription within 24 hours. "
        "Reference: " + payment_submission.get_payment_instructions()['reference']
    )
    
    return redirect('subscriptions:dashboard')


@login_required
def cancel_subscription(request):
    """Cancel user's subscription."""
    if request.method != 'POST':
        return redirect('subscriptions:dashboard')
    
    try:
        subscription = request.user.subscription
        
        # Cancel in our system
        SubscriptionService.cancel_subscription(request.user)
        
        messages.success(
            request,
            "Your subscription has been canceled. You'll have access until the end of your billing period."
        )
        
    except Exception as e:
        messages.error(request, f"Error canceling subscription: {str(e)}")
    
    return redirect('subscriptions:dashboard')


@login_required
def change_plan(request):
    """Change subscription plan."""
    if request.method != 'POST':
        return redirect('subscriptions:pricing')
    
    new_tier_name = request.POST.get('tier')
    
    try:
        new_tier = SubscriptionTier.objects.get(name=new_tier_name, is_active=True)
    except SubscriptionTier.DoesNotExist:
        messages.error(request, "Invalid plan selected.")
        return redirect('subscriptions:pricing')
    
    try:
        subscription = request.user.subscription
        
        # If upgrading to paid plan, show payment instructions
        if new_tier.price_monthly > 0:
            return payment_instructions(request)
        
        # If downgrading to free, cancel current subscription
        if new_tier.price_monthly == 0:
            SubscriptionService.cancel_subscription(request.user)
            messages.success(request, f"Your plan has been changed to {new_tier.display_name}.")
        
    except Exception as e:
        messages.error(request, f"Error changing plan: {str(e)}")
    
    return redirect('subscriptions:dashboard')


@login_required
def usage_api(request):
    """API endpoint for current usage (for AJAX updates)."""
    summary = SubscriptionService.get_subscription_summary(request.user)
    return JsonResponse(summary)


@login_required
@require_POST
def clear_upgrade_flag(request):
    """Clear the upgrade_required session flag after modal is dismissed."""
    request.session.pop('upgrade_required', None)
    request.session.pop('upgrade_reason', None)
    return JsonResponse({'ok': True})


# ============================================
# ADMIN VIEWS FOR MANUAL PAYMENT VERIFICATION
# ============================================

@staff_member_required
def pending_payments_admin(request):
    """Admin view to see all pending manual payments."""
    pending = ManualPaymentSubmission.objects.filter(
        status='pending'
    ).select_related('user', 'tier').order_by('-created_at')
    
    verified = ManualPaymentSubmission.objects.filter(
        status='verified'
    ).select_related('user', 'tier').order_by('-verified_at')[:20]
    
    context = {
        'pending_payments': pending,
        'verified_payments': verified,
    }
    
    return render(request, 'admin/subscriptions/pending_payments.html', context)


@staff_member_required
@require_POST
def verify_payment_admin(request, payment_id):
    """Admin action to verify a manual payment and activate subscription."""
    payment = get_object_or_404(ManualPaymentSubmission, id=payment_id)
    
    if payment.status != 'pending':
        messages.error(request, "This payment has already been processed.")
        return redirect('subscriptions:pending_payments_admin')
    
    try:
        # Update payment status
        payment.status = 'verified'
        payment.verified_by = request.user
        payment.verified_at = timezone.now()
        payment.verification_notes = request.POST.get('verification_notes', '')
        payment.save()
        
        # Activate subscription for user
        subscription = SubscriptionService.upgrade_subscription(
            payment.user,
            payment.tier.name,
            payment.billing_cycle
        )
        
        # Record in payment history
        PaymentRecord.objects.create(
            user=payment.user,
            subscription=subscription,
            amount=payment.amount,
            currency=payment.currency,
            status='completed',
            description=f'Manual bank transfer - {payment.tier.display_name} ({payment.billing_cycle})',
            completed_at=timezone.now(),
        )
        
        messages.success(
            request,
            f"Payment verified and subscription activated for {payment.user.username}!"
        )
        
    except Exception as e:
        messages.error(request, f"Error verifying payment: {str(e)}")
    
    return redirect('subscriptions:pending_payments_admin')


@staff_member_required
@require_POST
def reject_payment_admin(request, payment_id):
    """Admin action to reject a manual payment."""
    payment = get_object_or_404(ManualPaymentSubmission, id=payment_id)
    
    if payment.status != 'pending':
        messages.error(request, "This payment has already been processed.")
        return redirect('subscriptions:pending_payments_admin')
    
    payment.status = 'rejected'
    payment.verified_by = request.user
    payment.verified_at = timezone.now()
    payment.verification_notes = request.POST.get('rejection_reason', '')
    payment.save()
    
    messages.success(request, f"Payment rejected for {payment.user.username}.")
    
    return redirect('subscriptions:pending_payments_admin')
