"""
Property-based tests for circuit breaker implementation.

Tests universal properties of the circuit breaker pattern using Hypothesis.

Feature: backend-optimization
Property 27: Circuit breaker pattern
Validates: Requirements 6.3

The circuit breaker should:
1. Open after threshold failures
2. Reject subsequent requests without attempting them when open
3. Transition to half-open after recovery timeout
4. Close after successful test requests in half-open state
"""

import pytest
import time
from hypothesis import given, strategies as st, settings, assume
from infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerError
)


class ServiceCallTracker:
    """Helper class to track whether service calls are actually attempted."""
    
    def __init__(self):
        self.call_count = 0
        self.should_fail = True
    
    def call_service(self):
        """Simulate a service call."""
        self.call_count += 1
        if self.should_fail:
            raise Exception("Service unavailable")
        return "success"
    
    def reset(self):
        """Reset the tracker."""
        self.call_count = 0
        self.should_fail = True


# Feature: backend-optimization, Property 27: Circuit breaker pattern
@given(
    failure_threshold=st.integers(min_value=1, max_value=10),
    extra_attempts=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_circuit_opens_after_threshold_failures(failure_threshold, extra_attempts):
    """
    Property 27.1: Circuit breaker opens after threshold failures.
    
    For any failure_threshold, after exactly failure_threshold consecutive failures,
    the circuit breaker should transition to OPEN state.
    
    **Validates: Requirements 6.3**
    """
    cb = CircuitBreaker(
        name="test_property",
        failure_threshold=failure_threshold,
        recovery_timeout=60
    )
    
    tracker = ServiceCallTracker()
    
    # Make exactly failure_threshold failing calls
    for i in range(failure_threshold):
        with pytest.raises(Exception, match="Service unavailable"):
            cb.call(tracker.call_service)
        
        # Circuit should still be closed until we hit the threshold
        if i < failure_threshold - 1:
            assert cb.get_state() == CircuitState.CLOSED
    
    # After threshold failures, circuit should be OPEN
    assert cb.get_state() == CircuitState.OPEN
    
    # Verify the service was actually called failure_threshold times
    assert tracker.call_count == failure_threshold


# Feature: backend-optimization, Property 27: Circuit breaker pattern
@given(
    failure_threshold=st.integers(min_value=1, max_value=10),
    blocked_attempts=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_circuit_rejects_requests_when_open(failure_threshold, blocked_attempts):
    """
    Property 27.2: Circuit breaker rejects requests without attempting them when open.
    
    For any number of attempts after the circuit opens, the circuit breaker should
    reject all requests with CircuitBreakerError WITHOUT calling the underlying service.
    
    **Validates: Requirements 6.3**
    """
    cb = CircuitBreaker(
        name="test_property",
        failure_threshold=failure_threshold,
        recovery_timeout=60  # Long timeout to keep circuit open
    )
    
    tracker = ServiceCallTracker()
    
    # Open the circuit by triggering threshold failures
    for _ in range(failure_threshold):
        with pytest.raises(Exception):
            cb.call(tracker.call_service)
    
    assert cb.get_state() == CircuitState.OPEN
    initial_call_count = tracker.call_count
    
    # Try to make additional calls - they should all be rejected
    # WITHOUT calling the underlying service
    for _ in range(blocked_attempts):
        with pytest.raises(CircuitBreakerError) as exc_info:
            cb.call(tracker.call_service)
        
        # Verify it's a circuit breaker error
        assert exc_info.value.circuit_name == "test_property"
        assert exc_info.value.state == CircuitState.OPEN
    
    # CRITICAL: Service should NOT have been called for blocked attempts
    assert tracker.call_count == initial_call_count, \
        f"Service was called {tracker.call_count - initial_call_count} times when circuit was open"
    
    # Circuit should still be OPEN
    assert cb.get_state() == CircuitState.OPEN


# Feature: backend-optimization, Property 27: Circuit breaker pattern
@given(
    failure_threshold=st.integers(min_value=1, max_value=5),
    recovery_timeout=st.integers(min_value=1, max_value=3)
)
@settings(max_examples=50, deadline=None)
@pytest.mark.property_test
def test_circuit_transitions_to_half_open_after_timeout(failure_threshold, recovery_timeout):
    """
    Property 27.3: Circuit breaker transitions to half-open after recovery timeout.
    
    For any recovery_timeout, after the circuit opens and the timeout expires,
    the next call should transition the circuit to HALF_OPEN state and attempt
    the call (allowing the service to be tested).
    
    **Validates: Requirements 6.3**
    """
    cb = CircuitBreaker(
        name="test_property",
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout
    )
    
    tracker = ServiceCallTracker()
    
    # Open the circuit
    for _ in range(failure_threshold):
        with pytest.raises(Exception):
            cb.call(tracker.call_service)
    
    assert cb.get_state() == CircuitState.OPEN
    call_count_before_timeout = tracker.call_count
    
    # Wait for recovery timeout to expire
    time.sleep(recovery_timeout + 0.5)
    
    # Next call should transition to HALF_OPEN and attempt the call
    # (it will fail because tracker.should_fail is still True)
    with pytest.raises(Exception, match="Service unavailable"):
        cb.call(tracker.call_service)
    
    # Verify the service was actually called (proving we're in HALF_OPEN)
    assert tracker.call_count == call_count_before_timeout + 1, \
        "Service should have been called once in HALF_OPEN state"
    
    # After failure in HALF_OPEN, circuit should be back to OPEN
    assert cb.get_state() == CircuitState.OPEN


# Feature: backend-optimization, Property 27: Circuit breaker pattern
@given(
    failure_threshold=st.integers(min_value=1, max_value=5),
    recovery_timeout=st.integers(min_value=1, max_value=3),
    half_open_max_calls=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=50, deadline=None)
@pytest.mark.property_test
def test_circuit_closes_after_successful_half_open_calls(
    failure_threshold,
    recovery_timeout,
    half_open_max_calls
):
    """
    Property 27.4: Circuit breaker closes after successful test requests.
    
    For any half_open_max_calls, after the circuit transitions to HALF_OPEN,
    if exactly half_open_max_calls consecutive successful calls are made,
    the circuit should transition to CLOSED state.
    
    **Validates: Requirements 6.3**
    """
    cb = CircuitBreaker(
        name="test_property",
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        half_open_max_calls=half_open_max_calls
    )
    
    tracker = ServiceCallTracker()
    
    # Open the circuit
    for _ in range(failure_threshold):
        with pytest.raises(Exception):
            cb.call(tracker.call_service)
    
    assert cb.get_state() == CircuitState.OPEN
    
    # Wait for recovery timeout
    time.sleep(recovery_timeout + 0.5)
    
    # Make the service succeed now
    tracker.should_fail = False
    
    # Make half_open_max_calls successful calls
    for i in range(half_open_max_calls):
        result = cb.call(tracker.call_service)
        assert result == "success"
        
        # Circuit should be HALF_OPEN until we complete all test calls
        if i < half_open_max_calls - 1:
            assert cb.get_state() == CircuitState.HALF_OPEN
    
    # After all successful test calls, circuit should be CLOSED
    assert cb.get_state() == CircuitState.CLOSED
    
    # Verify we can make additional calls in CLOSED state
    result = cb.call(tracker.call_service)
    assert result == "success"
    assert cb.get_state() == CircuitState.CLOSED


# Feature: backend-optimization, Property 27: Circuit breaker pattern
@given(
    failure_threshold=st.integers(min_value=2, max_value=5),
    recovery_timeout=st.integers(min_value=1, max_value=3),
    half_open_max_calls=st.integers(min_value=2, max_value=5),
    failure_position=st.integers(min_value=0, max_value=4)
)
@settings(max_examples=50, deadline=None)
@pytest.mark.property_test
def test_circuit_reopens_on_half_open_failure(
    failure_threshold,
    recovery_timeout,
    half_open_max_calls,
    failure_position
):
    """
    Property 27.5: Circuit breaker reopens if any call fails in half-open state.
    
    For any position in the half-open test sequence, if a call fails,
    the circuit should immediately transition back to OPEN state.
    
    **Validates: Requirements 6.3**
    """
    # Ensure failure_position is within the half_open_max_calls range
    assume(failure_position < half_open_max_calls)
    
    cb = CircuitBreaker(
        name="test_property",
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        half_open_max_calls=half_open_max_calls
    )
    
    tracker = ServiceCallTracker()
    
    # Open the circuit
    for _ in range(failure_threshold):
        with pytest.raises(Exception):
            cb.call(tracker.call_service)
    
    assert cb.get_state() == CircuitState.OPEN
    
    # Wait for recovery timeout
    time.sleep(recovery_timeout + 0.5)
    
    # Make the service succeed initially
    tracker.should_fail = False
    
    # Make successful calls up to failure_position
    for i in range(failure_position):
        result = cb.call(tracker.call_service)
        assert result == "success"
        assert cb.get_state() == CircuitState.HALF_OPEN
    
    # Now make the service fail
    tracker.should_fail = True
    
    # The next call should fail and reopen the circuit
    with pytest.raises(Exception, match="Service unavailable"):
        cb.call(tracker.call_service)
    
    # Circuit should be back to OPEN
    assert cb.get_state() == CircuitState.OPEN


# Feature: backend-optimization, Property 27: Circuit breaker pattern
@given(
    failure_threshold=st.integers(min_value=1, max_value=10),
    success_count=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_circuit_stays_closed_with_successes(failure_threshold, success_count):
    """
    Property 27.6: Circuit breaker stays closed with successful calls.
    
    For any number of successful calls, the circuit should remain in CLOSED state
    and continue to allow calls through.
    
    **Validates: Requirements 6.3**
    """
    cb = CircuitBreaker(
        name="test_property",
        failure_threshold=failure_threshold,
        recovery_timeout=60
    )
    
    tracker = ServiceCallTracker()
    tracker.should_fail = False  # Make service succeed
    
    # Make multiple successful calls
    for _ in range(success_count):
        result = cb.call(tracker.call_service)
        assert result == "success"
        assert cb.get_state() == CircuitState.CLOSED
    
    # Verify all calls were actually made
    assert tracker.call_count == success_count


# Feature: backend-optimization, Property 27: Circuit breaker pattern
@given(
    failure_threshold=st.integers(min_value=3, max_value=10),
    failures_before_success=st.integers(min_value=1, max_value=9)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_success_resets_failure_count_in_closed_state(
    failure_threshold,
    failures_before_success
):
    """
    Property 27.7: Success resets failure count in closed state.
    
    For any number of failures less than the threshold, a successful call
    should reset the failure count, preventing the circuit from opening.
    
    **Validates: Requirements 6.3**
    """
    # Ensure we don't hit the threshold
    assume(failures_before_success < failure_threshold)
    
    cb = CircuitBreaker(
        name="test_property",
        failure_threshold=failure_threshold,
        recovery_timeout=60
    )
    
    tracker = ServiceCallTracker()
    
    # Make some failing calls (but not enough to open circuit)
    for _ in range(failures_before_success):
        with pytest.raises(Exception):
            cb.call(tracker.call_service)
    
    # Circuit should still be closed
    assert cb.get_state() == CircuitState.CLOSED
    
    # Make a successful call
    tracker.should_fail = False
    result = cb.call(tracker.call_service)
    assert result == "success"
    
    # Circuit should still be closed
    assert cb.get_state() == CircuitState.CLOSED
    
    # Now we should be able to make failure_threshold failures again
    # without opening the circuit immediately (because count was reset)
    tracker.should_fail = True
    for i in range(failures_before_success):
        with pytest.raises(Exception):
            cb.call(tracker.call_service)
        # Should still be closed since we reset the count
        assert cb.get_state() == CircuitState.CLOSED


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
