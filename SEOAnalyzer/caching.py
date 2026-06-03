"""
Caching utilities and decorators for WebLift.

Provides cache decorators, template fragment caching helpers, and query optimization utilities.
"""

import hashlib
import json
from functools import wraps
from typing import Any, Callable, Optional

from django.core.cache import cache
from django.db import connection
from django.conf import settings


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a deterministic cache key from prefix and arguments."""
    key_parts = [prefix]
    
    # Add args to key
    for arg in args:
        key_parts.append(str(arg))
    
    # Add sorted kwargs to key
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}={value}")
    
    # Create hash
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached_view(timeout: int = 300, key_prefix: str = "view"):
    """
    Decorator to cache view responses.
    
    Usage:
        @cached_view(timeout=600, key_prefix="dashboard")
        def dashboard(request):
            ...
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Don't cache authenticated user views by default
            if request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            # Generate cache key
            cache_key = generate_cache_key(
                key_prefix,
                request.path,
                request.META.get('QUERY_STRING', ''),
                *args,
                **kwargs
            )
            
            # Try to get cached response
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return cached_response
            
            # Execute view and cache result
            response = view_func(request, *args, **kwargs)
            
            # Only cache successful responses
            if hasattr(response, 'status_code') and response.status_code == 200:
                cache.set(cache_key, response, timeout)
            
            return response
        return wrapper
    return decorator


def cached_method(timeout: int = 300, key_prefix: str = "method"):
    """
    Decorator to cache method results based on instance and arguments.
    
    Usage:
        @cached_method(timeout=600, key_prefix="get_data")
        def get_data(self, param1, param2=None):
            ...
    """
    def decorator(method: Callable) -> Callable:
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            # Generate cache key including instance id
            instance_id = getattr(self, 'id', getattr(self, 'pk', id(self)))
            cache_key = generate_cache_key(
                key_prefix,
                str(self.__class__.__name__),
                str(instance_id),
                *args,
                **kwargs
            )
            
            # Try to get cached result
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute method and cache result
            result = method(self, *args, **kwargs)
            cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


def invalidate_cache(key_prefix: str, *args, **kwargs):
    """Invalidate a specific cache key."""
    cache_key = generate_cache_key(key_prefix, *args, **kwargs)
    cache.delete(cache_key)


def invalidate_pattern(pattern: str):
    """Invalidate all cache keys matching a pattern (Redis only)."""
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(pattern)
    else:
        # Fallback for non-Redis backends
        cache.clear()


class QueryCounter:
    """Context manager to count database queries during execution."""
    
    def __init__(self):
        self.query_count = 0
        self.queries = []
    
    def __enter__(self):
        self.query_count = len(connection.queries)
        return self
    
    def __exit__(self, *args):
        self.query_count = len(connection.queries) - self.query_count
        self.queries = connection.queries[-self.query_count:]
    
    def __str__(self):
        return f"QueryCounter: {self.query_count} queries executed"


def log_slow_queries(threshold: Optional[float] = None):
    """
    Decorator to log slow database queries.
    
    Usage:
        @log_slow_queries(threshold=1.0)
        def my_view(request):
            ...
    """
    threshold = threshold or getattr(settings, 'SLOW_QUERY_THRESHOLD', 0.5)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            import logging
            
            logger = logging.getLogger('SEOAnalyzer.performance')
            
            start_time = time.time()
            initial_query_count = len(connection.queries)
            
            result = func(*args, **kwargs)
            
            elapsed = time.time() - start_time
            query_count = len(connection.queries) - initial_query_count
            
            if elapsed > threshold:
                logger.warning(
                    f"Slow query detected: {func.__name__} took {elapsed:.2f}s "
                    f"with {query_count} queries"
                )
            
            return result
        return wrapper
    return decorator


def optimize_queryset(queryset, select_related: list = None, prefetch_related: list = None):
    """
    Apply query optimization techniques to a queryset.
    
    Args:
        queryset: Django QuerySet to optimize
        select_related: List of foreign key fields to join
        prefetch_related: List of many-to-many/reverse relation fields to prefetch
    
    Returns:
        Optimized QuerySet
    """
    if select_related:
        queryset = queryset.select_related(*select_related)
    
    if prefetch_related:
        queryset = queryset.prefetch_related(*prefetch_related)
    
    return queryset


# Cache timeout constants
CACHE_TIMEOUT_SHORT = 60       # 1 minute
CACHE_TIMEOUT_MEDIUM = 300     # 5 minutes
CACHE_TIMEOUT_LONG = 1800      # 30 minutes
CACHE_TIMEOUT_VERY_LONG = 3600 # 1 hour
