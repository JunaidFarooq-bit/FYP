"""
Circuit breaker pattern for external API resilience.

Prevents cascading failures when external services (Groq, Moz, etc.) are down.
Automatically fails fast after consecutive failures and periodically
attempts recovery.
"""

import logging
import time
from enum import Enum
from functools import wraps
from typing import Callable, Optional, Any
from datetime import datetime, timedelta

from django.core.cache import cache

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation - requests pass through
    OPEN = "open"          # Failure threshold reached - requests fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CircuitBreaker:
    """
    Circuit breaker for external API calls.
    
    Example:
        breaker = CircuitBreaker("groq_api", failure_threshold=5, recovery_timeout=60)
        
        @breaker
        def call_groq(prompt):
            return groq_client.chat.completions.create(...)
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        success_threshold: int = 3,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Unique name for this circuit breaker (used in cache keys)
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to count as failure
            success_threshold: Successes needed in HALF_OPEN to close circuit
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
    
    def _get_state_key(self) -> str:
        return f"circuit_breaker:{self.name}:state"
    
    def _get_failures_key(self) -> str:
        return f"circuit_breaker:{self.name}:failures"
    
    def _get_last_failure_key(self) -> str:
        return f"circuit_breaker:{self.name}:last_failure"
    
    def _get_state(self) -> CircuitState:
        """Get current circuit state."""
        state_value = cache.get(self._get_state_key(), CircuitState.CLOSED.value)
        return CircuitState(state_value)
    
    def _set_state(self, state: CircuitState):
        """Set circuit state."""
        cache.set(self._get_state_key(), state.value, timeout=None)
        logger.info(f"Circuit breaker '{self.name}' state changed to: {state.value}")
    
    def _get_failures(self) -> int:
        """Get current failure count."""
        return cache.get(self._get_failures_key(), 0)
    
    def _increment_failures(self):
        """Increment failure count."""
        try:
            cache.incr(self._get_failures_key())
        except ValueError:
            cache.set(self._get_failures_key(), 1, timeout=300)
    
    def _reset_failures(self):
        """Reset failure count."""
        cache.set(self._get_failures_key(), 0, timeout=300)
    
    def _get_last_failure_time(self) -> Optional[datetime]:
        """Get timestamp of last failure."""
        timestamp = cache.get(self._get_last_failure_key())
        if timestamp:
            return datetime.fromtimestamp(timestamp)
        return None
    
    def _set_last_failure(self):
        """Record last failure time."""
        cache.set(self._get_last_failure_key(), time.time(), timeout=300)
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try recovery."""
        last_failure = self._get_last_failure_time()
        if not last_failure:
            return True
        return datetime.now() - last_failure >= timedelta(seconds=self.recovery_timeout)
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Original exception if call fails
        """
        state = self._get_state()
        
        if state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")
                self._set_state(CircuitState.HALF_OPEN)
            else:
                raise CircuitBreakerOpen(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Service temporarily unavailable."
                )
        
        try:
            result = func(*args, **kwargs)
            
            # Success handling
            if state == CircuitState.HALF_OPEN:
                # In half-open, track successes
                successes = cache.get(f"circuit_breaker:{self.name}:successes", 0) + 1
                if successes >= self.success_threshold:
                    logger.info(f"Circuit breaker '{self.name}' CLOSED after recovery")
                    self._set_state(CircuitState.CLOSED)
                    self._reset_failures()
                else:
                    cache.set(f"circuit_breaker:{self.name}:successes", successes, timeout=300)
            else:
                # In closed state, reset failures on success
                self._reset_failures()
            
            return result
            
        except self.expected_exception as e:
            # Failure handling
            self._increment_failures()
            self._set_last_failure()
            
            failures = self._get_failures()
            
            if state == CircuitState.HALF_OPEN:
                # Failed in half-open, go back to open
                logger.warning(
                    f"Circuit breaker '{self.name}' returned to OPEN after failed recovery attempt"
                )
                self._set_state(CircuitState.OPEN)
            elif failures >= self.failure_threshold:
                # Threshold reached, open circuit
                logger.error(
                    f"Circuit breaker '{self.name}' OPEN after {failures} failures"
                )
                self._set_state(CircuitState.OPEN)
            
            raise
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator interface."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        
        # Attach circuit breaker to function for manual control
        wrapper._circuit_breaker = self
        return wrapper
    
    def force_open(self):
        """Manually open the circuit (for maintenance, etc.)."""
        self._set_state(CircuitState.OPEN)
        logger.warning(f"Circuit breaker '{self.name}' manually opened")
    
    def force_close(self):
        """Manually close the circuit (force recovery)."""
        self._set_state(CircuitState.CLOSED)
        self._reset_failures()
        logger.info(f"Circuit breaker '{self.name}' manually closed")
    
    def get_status(self) -> dict:
        """Get current circuit breaker status."""
        last_failure = self._get_last_failure_time()
        return {
            "name": self.name,
            "state": self._get_state().value,
            "failures": self._get_failures(),
            "threshold": self.failure_threshold,
            "last_failure": last_failure.isoformat() if last_failure else None,
            "recovery_timeout": self.recovery_timeout,
        }


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


# Pre-configured circuit breakers for common services

# Groq AI API - Fail fast after 5 failures, 2 minute recovery
groq_circuit_breaker = CircuitBreaker(
    name="groq_api",
    failure_threshold=5,
    recovery_timeout=120,
    expected_exception=Exception,  # Broad due to various API errors
)

# OpenAI API - More lenient due to rate limits
openai_circuit_breaker = CircuitBreaker(
    name="openai_api",
    failure_threshold=3,
    recovery_timeout=60,
    expected_exception=Exception,
)

# Moz API - Very conservative due to limited quota
moz_circuit_breaker = CircuitBreaker(
    name="moz_api",
    failure_threshold=3,
    recovery_timeout=300,  # 5 minutes
    expected_exception=Exception,
)

# PageSpeed Insights API
pagespeed_circuit_breaker = CircuitBreaker(
    name="pagespeed_api",
    failure_threshold=5,
    recovery_timeout=180,  # 3 minutes
    expected_exception=Exception,
)

# External HTTP requests (general)
http_circuit_breaker = CircuitBreaker(
    name="http_external",
    failure_threshold=10,
    recovery_timeout=60,
    expected_exception=Exception,
)


def get_all_circuit_status() -> list:
    """Get status of all circuit breakers."""
    breakers = [
        groq_circuit_breaker,
        openai_circuit_breaker,
        moz_circuit_breaker,
        pagespeed_circuit_breaker,
        http_circuit_breaker,
    ]
    return [breaker.get_status() for breaker in breakers]
