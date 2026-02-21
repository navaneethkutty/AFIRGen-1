"""
Circuit breaker pattern implementation for preventing cascading failures.

This module provides a circuit breaker that monitors failures and temporarily
blocks calls to failing services, allowing them to recover.

The circuit breaker has three states:
- CLOSED: Normal operation, requests pass through
- OPEN: Too many failures, requests are blocked
- HALF_OPEN: Testing if service has recovered

Validates: Requirements 6.3
"""

import time
import threading
from typing import Callable, TypeVar, Optional, Any, Dict
from enum import Enum
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime


T = TypeVar('T')


class CircuitState(Enum):
    """
    Circuit breaker states.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is failing, requests are blocked
    - HALF_OPEN: Testing if service has recovered
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, message: str, circuit_name: str, state: CircuitState):
        super().__init__(message)
        self.circuit_name = circuit_name
        self.state = state


@dataclass
class CircuitBreakerStats:
    """
    Statistics for circuit breaker monitoring.
    
    Attributes:
        state: Current circuit state
        failure_count: Number of consecutive failures
        success_count: Number of consecutive successes in half-open state
        last_failure_time: Timestamp of last failure
        last_state_change: Timestamp of last state change
        total_calls: Total number of calls attempted
        total_failures: Total number of failures
        total_successes: Total number of successes
    """
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_state_change: float = field(default_factory=time.time)
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary for serialization."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": datetime.fromtimestamp(self.last_failure_time).isoformat() if self.last_failure_time else None,
            "last_state_change": datetime.fromtimestamp(self.last_state_change).isoformat(),
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes
        }


class CircuitBreaker:
    """
    Circuit breaker for preventing cascading failures.
    
    The circuit breaker monitors failures and transitions between states:
    
    1. CLOSED (normal operation):
       - Requests pass through normally
       - Failures are counted
       - When failure_threshold is reached, transition to OPEN
    
    2. OPEN (service is failing):
       - Requests are immediately rejected with CircuitBreakerError
       - After recovery_timeout seconds, transition to HALF_OPEN
    
    3. HALF_OPEN (testing recovery):
       - Allow half_open_max_calls test requests
       - If all succeed, transition to CLOSED
       - If any fail, transition back to OPEN
    
    Thread-safe implementation using locks.
    
    Validates: Requirements 6.3
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
        expected_exception: type = Exception
    ):
        """
        Initialize CircuitBreaker.
        
        Args:
            name: Name of the circuit breaker (for logging/monitoring)
            failure_threshold: Number of consecutive failures before opening circuit (default: 5)
            recovery_timeout: Seconds to wait before attempting recovery (default: 60)
            half_open_max_calls: Number of test calls allowed in half-open state (default: 3)
            expected_exception: Exception type to catch (default: Exception)
        
        Raises:
            ValueError: If parameters are invalid
        """
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if recovery_timeout < 0:
            raise ValueError("recovery_timeout must be >= 0")
        if half_open_max_calls < 1:
            raise ValueError("half_open_max_calls must be >= 1")
        
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.expected_exception = expected_exception
        
        # Thread-safe state management
        self._lock = threading.RLock()
        self._stats = CircuitBreakerStats()
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function through the circuit breaker.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        
        Returns:
            Result of func execution
        
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception raised by func
        
        Example:
            >>> cb = CircuitBreaker("api", failure_threshold=3)
            >>> result = cb.call(requests.get, "https://api.example.com")
        
        Validates: Requirements 6.3
        """
        with self._lock:
            self._stats.total_calls += 1
            
            # Check current state and handle accordingly
            current_state = self._stats.state
            
            if current_state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    # Circuit is still open, reject the call
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is OPEN",
                        self.name,
                        CircuitState.OPEN
                    )
            
            elif current_state == CircuitState.HALF_OPEN:
                # Check if we've exceeded max test calls
                if self._stats.success_count >= self.half_open_max_calls:
                    # Should not happen, but handle gracefully
                    self._transition_to_closed()
        
        # Execute the function (outside the lock to avoid blocking)
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful call."""
        with self._lock:
            self._stats.total_successes += 1
            
            if self._stats.state == CircuitState.HALF_OPEN:
                # Increment success count in half-open state
                self._stats.success_count += 1
                
                # If we've reached the threshold, close the circuit
                if self._stats.success_count >= self.half_open_max_calls:
                    self._transition_to_closed()
            
            elif self._stats.state == CircuitState.CLOSED:
                # Reset failure count on success
                self._stats.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        with self._lock:
            self._stats.total_failures += 1
            self._stats.last_failure_time = time.time()
            
            if self._stats.state == CircuitState.HALF_OPEN:
                # Any failure in half-open state reopens the circuit
                self._transition_to_open()
            
            elif self._stats.state == CircuitState.CLOSED:
                # Increment failure count
                self._stats.failure_count += 1
                
                # Check if we've reached the threshold
                if self._stats.failure_count >= self.failure_threshold:
                    self._transition_to_open()
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._stats.last_failure_time is None:
            return True
        
        elapsed = time.time() - self._stats.last_failure_time
        return elapsed >= self.recovery_timeout
    
    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        self._stats.state = CircuitState.OPEN
        self._stats.last_state_change = time.time()
        self._stats.success_count = 0
    
    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        self._stats.state = CircuitState.HALF_OPEN
        self._stats.last_state_change = time.time()
        self._stats.failure_count = 0
        self._stats.success_count = 0
    
    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        self._stats.state = CircuitState.CLOSED
        self._stats.last_state_change = time.time()
        self._stats.failure_count = 0
        self._stats.success_count = 0
    
    def get_state(self) -> CircuitState:
        """
        Get current circuit state.
        
        Returns:
            Current CircuitState
        
        Example:
            >>> cb = CircuitBreaker("api")
            >>> cb.get_state()
            CircuitState.CLOSED
        """
        with self._lock:
            return self._stats.state
    
    def get_stats(self) -> CircuitBreakerStats:
        """
        Get circuit breaker statistics.
        
        Returns:
            Copy of current statistics
        
        Example:
            >>> cb = CircuitBreaker("api")
            >>> stats = cb.get_stats()
            >>> print(f"State: {stats.state}, Failures: {stats.failure_count}")
        """
        with self._lock:
            # Return a copy to prevent external modification
            return CircuitBreakerStats(
                state=self._stats.state,
                failure_count=self._stats.failure_count,
                success_count=self._stats.success_count,
                last_failure_time=self._stats.last_failure_time,
                last_state_change=self._stats.last_state_change,
                total_calls=self._stats.total_calls,
                total_failures=self._stats.total_failures,
                total_successes=self._stats.total_successes
            )
    
    def reset(self) -> None:
        """
        Manually reset the circuit breaker to CLOSED state.
        
        This should be used for administrative purposes or testing.
        
        Example:
            >>> cb = CircuitBreaker("api")
            >>> cb.reset()  # Force circuit to CLOSED state
        """
        with self._lock:
            self._transition_to_closed()
    
    def force_open(self) -> None:
        """
        Manually force the circuit breaker to OPEN state.
        
        Useful for maintenance or testing.
        
        Example:
            >>> cb = CircuitBreaker("api")
            >>> cb.force_open()  # Force circuit to OPEN state
        """
        with self._lock:
            self._stats.last_failure_time = time.time()
            self._transition_to_open()


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    half_open_max_calls: int = 3,
    expected_exception: type = Exception
):
    """
    Decorator for adding circuit breaker to functions.
    
    Creates a circuit breaker instance and wraps the function.
    
    Args:
        name: Name of the circuit breaker
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        half_open_max_calls: Number of test calls in half-open state
        expected_exception: Exception type to catch
    
    Returns:
        Decorated function with circuit breaker
    
    Example:
        >>> @circuit_breaker("api", failure_threshold=3)
        ... def call_external_api(url: str):
        ...     response = requests.get(url)
        ...     return response.json()
    
    Validates: Requirements 6.3
    """
    cb = CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        half_open_max_calls=half_open_max_calls,
        expected_exception=expected_exception
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return cb.call(func, *args, **kwargs)
        
        # Attach circuit breaker instance to wrapper for external access
        wrapper.circuit_breaker = cb
        
        return wrapper
    return decorator


# Global registry for circuit breakers
_circuit_breaker_registry: Dict[str, CircuitBreaker] = {}
_registry_lock = threading.Lock()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    half_open_max_calls: int = 3,
    expected_exception: type = Exception
) -> CircuitBreaker:
    """
    Get or create a circuit breaker from the global registry.
    
    This allows sharing circuit breakers across different parts of the application.
    
    Args:
        name: Name of the circuit breaker
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        half_open_max_calls: Number of test calls in half-open state
        expected_exception: Exception type to catch
    
    Returns:
        CircuitBreaker instance
    
    Example:
        >>> cb = get_circuit_breaker("model_server", failure_threshold=5)
        >>> result = cb.call(call_model_server, data)
    """
    with _registry_lock:
        if name not in _circuit_breaker_registry:
            _circuit_breaker_registry[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                half_open_max_calls=half_open_max_calls,
                expected_exception=expected_exception
            )
        return _circuit_breaker_registry[name]


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """
    Get all registered circuit breakers.
    
    Returns:
        Dictionary mapping circuit breaker names to instances
    
    Example:
        >>> breakers = get_all_circuit_breakers()
        >>> for name, cb in breakers.items():
        ...     print(f"{name}: {cb.get_state()}")
    """
    with _registry_lock:
        return _circuit_breaker_registry.copy()


def reset_all_circuit_breakers() -> None:
    """
    Reset all registered circuit breakers to CLOSED state.
    
    Useful for testing or administrative purposes.
    """
    with _registry_lock:
        for cb in _circuit_breaker_registry.values():
            cb.reset()
