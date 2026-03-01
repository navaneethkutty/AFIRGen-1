"""
Circuit breaker pattern to prevent cascading failures.
Implements CLOSED, OPEN, and HALF_OPEN states.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Any
from functools import wraps


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerError(Exception):
    """Exception raised when circuit is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    Transitions between CLOSED, OPEN, and HALF_OPEN states.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            half_open_max_calls: Max successful calls in half-open before closing
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original exception from function
        """
        # Check if we should transition from OPEN to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker is OPEN. "
                    f"Will retry in {self._time_until_retry():.1f}s"
                )
        
        # Check if we've exceeded half-open calls
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerError(
                    "Circuit breaker HALF_OPEN call limit reached"
                )
            self.half_open_calls += 1
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"Circuit breaker HALF_OPEN success "
                f"({self.success_count}/{self.half_open_max_calls})"
            )
            
            if self.success_count >= self.half_open_max_calls:
                self._transition_to_closed()
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open transitions back to open
            logger.warning("Circuit breaker HALF_OPEN failed, transitioning to OPEN")
            self._transition_to_open()
        
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            logger.warning(
                f"Circuit breaker failure {self.failure_count}/{self.failure_threshold}"
            )
            
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()
    
    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        self.state = CircuitState.OPEN
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        logger.error(
            f"Circuit breaker transitioned to OPEN. "
            f"Will attempt recovery in {self.recovery_timeout}s"
        )
    
    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.half_open_calls = 0
        logger.info("Circuit breaker transitioned to HALF_OPEN")
    
    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        logger.info("Circuit breaker transitioned to CLOSED")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout
    
    def _time_until_retry(self) -> float:
        """Calculate time until next retry attempt."""
        if self.last_failure_time is None:
            return 0.0
        
        elapsed = time.time() - self.last_failure_time
        remaining = self.recovery_timeout - elapsed
        return max(0.0, remaining)
    
    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'time_until_retry': self._time_until_retry() if self.state == CircuitState.OPEN else None
        }


def with_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0
):
    """
    Decorator for adding circuit breaker to async functions.
    
    Args:
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before attempting recovery
    
    Returns:
        Decorated function
    """
    breaker = CircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout
    )
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
