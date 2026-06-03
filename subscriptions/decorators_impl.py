"""
Subscription Decorators for WebLift.

These decorators handle subscription checks and usage tracking.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import Subscription, UsageTracker
from .services.subscription_service import SubscriptionService


def require_subscription(view_func):
    """
    Decorator that checks if user has an active subscription or available free trial.
    Redirects to subscription page if not eligible.
    
    Usage:
        @login_required
        @require_subscription
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        
        # Check if user has subscription
        try:
            subscription = user.subscription
        except Subscription.DoesNotExist:
            # Create default subscription if missing
            subscription = SubscriptionService.create_default_subscription(user)
        
        # Check if subscription is active OR free trial available
        if subscription.is_active():
            return view_func(request, *args, **kwargs)
        
        # Check for free trial
        if subscription.has_free_trial_available():
            return view_func(request, *args, **kwargs)
        
        # No active subscription and no free trial
        request.session['upgrade_required'] = True
        request.session['upgrade_reason'] = "You've used your free audit. Subscribe to continue."
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return redirect('Home')
    
    return _wrapped_view


def track_usage(feature_type, count=1):
    """
    Decorator to track usage of a feature.
    
    Args:
        feature_type: 'audit', 'keywords', 'competitor', 'pdf_export'
        count: Number of units used (e.g., number of keywords)
    
    Usage:
        @track_usage('audit')
        def run_seo_audit(request):
            ...
            
        @track_usage('keywords', count=50)
        def generate_keywords(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            # Only enforce limits on POST requests (actual feature usage).
            # GET requests just render the form/page — never consume quota.
            if request.method != 'POST':
                return view_func(request, *args, **kwargs)
            
            # Get or create usage tracker
            try:
                tracker = user.usage_tracker
            except UsageTracker.DoesNotExist:
                tracker = UsageTracker.objects.create(user=user)
            
            # Get subscription
            try:
                subscription = user.subscription
            except Subscription.DoesNotExist:
                subscription = SubscriptionService.create_default_subscription(user)
            
            # Check limits before executing
            can_use, reason = SubscriptionService.can_use_feature(
                user, feature_type, count
            )
            
            if not can_use:
                # Return appropriate response based on request type
                if request.headers.get('Content-Type') == 'application/json' or \
                   request.path.startswith('/api/'):
                    return JsonResponse({
                        'error': reason,
                        'subscription_required': True,
                        'redirect_url': '/subscriptions/pricing/'
                    }, status=403)

                request.session['upgrade_required'] = True
                request.session['upgrade_reason'] = reason
                referer = request.META.get('HTTP_REFERER')
                if referer:
                    return redirect(referer)
                return redirect('Home')
            
            # Execute the view
            response = view_func(request, *args, **kwargs)
            
            # Track usage after successful execution.
            # Only count when the view signals a real operation was performed
            # via the 'audit_performed' attribute, OR the response renders
            # a results page (not the input form rendered back on error).
            actually_performed = getattr(request, '_audit_performed', False)
            
            if response.status_code < 400 and actually_performed:
                if feature_type == 'audit':
                    tracker.record_audit()
                    # Consume free trial on first audit
                    if not tracker.has_used_free_audit():
                        tracker.use_free_audit()
                    # Invalidate cached subscription summary
                    SubscriptionService.invalidate_user_cache(user.id)
                elif feature_type == 'keywords':
                    tracker.record_keywords(count)
                elif feature_type == 'competitor':
                    tracker.record_competitor_analysis()
                elif feature_type == 'pdf_export':
                    tracker.record_pdf_export()
            
            return response
        
        return _wrapped_view
    return decorator


def enforce_free_trial_limit(view_func):
    """
    Special decorator for the first free audit.
    Allows one free use, then requires subscription.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        
        # GET requests just render the form — never consume quota
        if request.method != 'POST':
            return view_func(request, *args, **kwargs)
        
        try:
            tracker = user.usage_tracker
        except UsageTracker.DoesNotExist:
            tracker = UsageTracker.objects.create(user=user)
        
        # Check if free audit already used
        if tracker.has_used_free_audit():
            # Check if has active subscription
            try:
                subscription = user.subscription
                if subscription.is_active():
                    return view_func(request, *args, **kwargs)
            except Subscription.DoesNotExist:
                pass
            
            request.session['upgrade_required'] = True
            request.session['upgrade_reason'] = "You've used your free SEO audit. Subscribe to run more audits!"
            referer = request.META.get('HTTP_REFERER')
            if referer:
                return redirect(referer)
            return redirect('Home')
        
        # First use - allow and mark as used
        response = view_func(request, *args, **kwargs)
        
        # Mark free audit as used only if the view signals a real audit ran
        actually_performed = getattr(request, '_audit_performed', False)
        if response.status_code < 400 and actually_performed:
            tracker.use_free_audit()
            SubscriptionService.invalidate_user_cache(user.id)
            messages.success(
                request,
                "Great! You've used your free SEO audit. Subscribe to run unlimited audits and access advanced features!"
            )
        
        return response
    
    return _wrapped_view


def require_feature(feature_name):
    """
    Decorator to check if user has access to a specific feature.
    
    Usage:
        @require_feature('competitor_analysis')
        def competitor_analysis_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            try:
                subscription = user.subscription
            except Subscription.DoesNotExist:
                subscription = SubscriptionService.create_default_subscription(user)
            
            if not subscription.can_use_feature(feature_name):
                feature_display = feature_name.replace('_', ' ').title()
                request.session['upgrade_required'] = True
                request.session['upgrade_reason'] = f"{feature_display} is not available on your plan. Upgrade to access this feature!"
                referer = request.META.get('HTTP_REFERER')
                if referer:
                    return redirect(referer)
                return redirect('Home')
            
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    return decorator


def api_subscription_check(view_func):
    """
    Decorator for API endpoints that checks subscription and returns JSON response.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user if request.user.is_authenticated else None
        
        if not user:
            return JsonResponse({
                'error': 'Authentication required',
                'authenticated': False
            }, status=401)
        
        try:
            subscription = user.subscription
        except (Subscription.DoesNotExist, AttributeError):
            subscription = SubscriptionService.create_default_subscription(user)
        
        if not subscription.is_active() and not subscription.has_free_trial_available():
            return JsonResponse({
                'error': 'Active subscription required',
                'subscription_required': True,
                'redirect_url': '/subscriptions/pricing/'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
