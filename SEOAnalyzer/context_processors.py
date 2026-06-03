from subscriptions.services.subscription_service import SubscriptionService


def user_subscription(request):
    """Inject subscription/usage summary into every template context."""
    if not request.user.is_authenticated:
        return {}
    try:
        summary = SubscriptionService.get_subscription_summary(request.user)
    except Exception:
        summary = None
    return {'nav_subscription': summary}
