"""
Rate limiting utilities with subscription tier awareness.

Provides rate limiting decorators that respect user subscription tiers,
with different limits for free, basic, pro, and enterprise users.
"""

import logging
import time
from functools import wraps
from typing import Optional, Callable

from django.http import JsonResponse
from django.core.cache import cache
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)


# Rate limits per tier (requests per minute)
DEFAULT_RATE_LIMITS = {
    "free": 5,
    "basic": 30,
    "pro": 100,
    "enterprise": 500,
}


def get_user_tier(user) -> str:
    """Get user's subscription tier name."""
    try:
        subscription = user.subscription
        if subscription and subscription.tier:
            return subscription.tier.name
    except AttributeError:
        pass
    return "free"


def get_rate_limit_for_user(user, custom_limits: Optional[dict] = None) -> int:
    """
    Get rate limit for a user based on their subscription tier.
    
    Args:
        user: Django user instance
        custom_limits: Optional dict overriding default limits
        
    Returns:
        Maximum requests per minute allowed
    """
    limits = custom_limits or DEFAULT_RATE_LIMITS
    tier = get_user_tier(user)
    return limits.get(tier, limits.get("free", 5))


def make_cache_key(user, key_prefix: str = "ratelimit") -> str:
    """Create cache key for rate limiting."""
    return f"{key_prefix}:{user.id}:{int(time.time()) // 60}"



def rate_limit_by_tier(
    key: str = "user",
    custom_limits: Optional[dict] = None,
    block: bool = True,
    response_message: str = "Rate limit exceeded. Please upgrade your plan or try again later."
) -> Callable:
    """
    Decorator to rate limit views based on subscription tier.
    
    Args:
        key: Rate limit key type ('user', 'ip', or callable)
        custom_limits: Optional dict of {tier_name: requests_per_minute}
        block: If True, return 429 response; if False, just log
        response_message: Message for rate limit exceeded response
        
    Usage:
        @rate_limit_by_tier()
        def my_api_view(request):
            ...
            
        @rate_limit_by_tier(custom_limits={"free": 2, "pro": 50})
        def expensive_endpoint(request):
            ...
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Skip rate limiting for superusers
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Get rate limit for user
            limit = get_rate_limit_for_user(request.user, custom_limits)
            
            # Create cache key
            if key == "user":
                cache_key = make_cache_key(request.user, f"ratelimit:{view_func.__name__}")
            elif key == "ip":
                ip = request.META.get("REMOTE_ADDR", "unknown")
                cache_key = f"ratelimit:ip:{ip}:{int(time.time()) // 60}"
            elif callable(key):
                cache_key = key(request)
            else:
                cache_key = f"ratelimit:{key}:{int(time.time()) // 60}"
            
            # Check current count
            current_count = cache.get(cache_key, 0)
            
            if current_count >= limit:
                logger.warning(
                    f"Rate limit exceeded for user {request.user.username} "
                    f"(tier: {get_user_tier(request.user)}, limit: {limit})"
                )
                
                if block:
                    return JsonResponse(
                        {
                            "error": "Rate limit exceeded",
                            "message": response_message,
                            "limit": limit,
                            "retry_after": 60 - (int(time.time()) % 60),
                        },
                        status=429,
                    )
            
            # Increment counter
            # Use add first for atomic creation with TTL
            if current_count == 0:
                cache.add(cache_key, 1, timeout=60)
            else:
                cache.incr(cache_key)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def rate_limit_for_anon(
    requests_per_minute: int = 10,
    key: str = "ip",
    block: bool = True,
) -> Callable:
    """
    Rate limit decorator for anonymous (unauthenticated) endpoints.
    
    Args:
        requests_per_minute: Max requests allowed per minute
        key: Key type ('ip' or 'session')
        block: Whether to block or just log
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            # Get identifier
            if key == "ip":
                identifier = request.META.get("REMOTE_ADDR", "unknown")
            elif key == "session":
                identifier = request.session.session_key or "unknown"
            else:
                identifier = "unknown"
            
            cache_key = f"ratelimit:anon:{identifier}:{int(time.time()) // 60}"
            
            current_count = cache.get(cache_key, 0)
            
            if current_count >= requests_per_minute:
                logger.warning(f"Anonymous rate limit exceeded for {identifier}")
                
                if block:
                    return JsonResponse(
                        {
                            "error": "Rate limit exceeded",
                            "message": "Too many requests. Please log in for higher limits.",
                            "retry_after": 60 - (int(time.time()) % 60),
                        },
                        status=429,
                    )
            
            # Increment counter
            if current_count == 0:
                cache.add(cache_key, 1, timeout=60)
            else:
                cache.incr(cache_key)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


# Convenience decorators for common use cases
def rate_limit_free(requests_per_minute: int = 5):
    """Strict rate limiting for free tier actions."""
    return rate_limit_by_tier(custom_limits={
        "free": requests_per_minute,
        "basic": requests_per_minute * 3,
        "pro": requests_per_minute * 10,
        "enterprise": requests_per_minute * 50,
    })


def rate_limit_api(requests_per_minute: int = 30):
    """Standard API rate limiting."""
    return rate_limit_by_tier(custom_limits={
        "free": max(5, requests_per_minute // 6),
        "basic": requests_per_minute // 2,
        "pro": requests_per_minute,
        "enterprise": requests_per_minute * 5,
    })


def rate_limit_ai(requests_per_minute: int = 10):
    """Rate limiting for AI/LLM endpoints (expensive operations)."""
    return rate_limit_by_tier(custom_limits={
        "free": 0,  # No AI for free tier
        "basic": max(2, requests_per_minute // 5),
        "pro": requests_per_minute,
        "enterprise": requests_per_minute * 3,
    }, response_message="AI feature not available on your plan. Please upgrade to access AI suggestions.")
