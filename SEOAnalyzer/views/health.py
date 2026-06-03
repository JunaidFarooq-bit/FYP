"""
Health Check Endpoint for Production Monitoring.

Provides endpoints for load balancers and monitoring systems
to verify application health and dependencies.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from django.http import JsonResponse
from django.db import connections, DatabaseError
from django.core.cache import cache
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@require_GET
def health_check(request) -> JsonResponse:
    """
    Health check endpoint for load balancers and monitoring.
    
    Checks:
    - Database connectivity
    - Cache (Redis) connectivity
    - Basic application status
    
    Returns:
        200 OK if healthy
        503 Service Unavailable if any check fails
    """
    status: Dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {},
    }
    
    healthy = True
    
    # Database check
    try:
        connections["default"].cursor().execute("SELECT 1")
        status["checks"]["database"] = "ok"
    except DatabaseError as e:
        logger.error(f"Health check: Database error - {e}")
        status["checks"]["database"] = f"error: {str(e)}"
        healthy = False
    except Exception as e:
        logger.error(f"Health check: Unexpected database error - {e}")
        status["checks"]["database"] = f"error: {str(e)}"
        healthy = False
    
    # Cache check
    try:
        cache.set("health_check", "ok", 10)
        cache_value = cache.get("health_check")
        if cache_value == "ok":
            status["checks"]["cache"] = "ok"
        else:
            status["checks"]["cache"] = "error: unexpected cache value"
            healthy = False
    except Exception as e:
        logger.error(f"Health check: Cache error - {e}")
        status["checks"]["cache"] = f"error: {str(e)}"
        healthy = False
    
    # Application status (always ok if we got here)
    status["checks"]["application"] = "ok"
    
    if not healthy:
        status["status"] = "unhealthy"
        return JsonResponse(status, status=503)
    
    return JsonResponse(status, status=200)


@require_GET
def readiness_check(request) -> JsonResponse:
    """
    Readiness check for Kubernetes-style deployments.
    
    Indicates if the application is ready to serve traffic.
    More comprehensive than basic health check.
    """
    status = {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {},
    }
    
    # Check all critical dependencies
    healthy = True
    
    # Database with query test
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM django_migrations")
            count = cursor.fetchone()[0]
            status["checks"]["database"] = f"ok ({count} migrations)"
    except Exception as e:
        logger.error(f"Readiness check: Database error - {e}")
        status["checks"]["database"] = f"error: {str(e)}"
        healthy = False
    
    # Static files accessibility
    try:
        from django.conf import settings
        import os
        if os.path.exists(settings.STATIC_ROOT):
            status["checks"]["static_files"] = "ok"
        else:
            status["checks"]["static_files"] = "warning: STATIC_ROOT not found"
    except Exception as e:
        status["checks"]["static_files"] = f"error: {str(e)}"
    
    if not healthy:
        status["status"] = "not_ready"
        return JsonResponse(status, status=503)
    
    return JsonResponse(status, status=200)


@require_GET
def liveness_check(request) -> JsonResponse:
    """
    Liveness check for Kubernetes-style deployments.
    
    Simple check to verify the application process is alive.
    Should return quickly without heavy operations.
    """
    return JsonResponse(
        {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
        },
        status=200,
    )
