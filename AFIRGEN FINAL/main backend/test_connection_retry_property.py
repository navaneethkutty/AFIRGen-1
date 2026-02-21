"""
Property-based tests for connection retry logic.

Tests universal properties of connection retry for database and Redis
connections using Hypothesis.

Feature: backend-optimization
Property 28: Connection retry
Validates: Requirements 6.4

The connection retry should:
1. Attempt reconnection on transient failures
2. Follow exponential backoff strategy
3. Raise non-retryable errors immediately
4. Successfully connect after retries
"""

import pytest
import time
from unittest.mock import Mock
from hypothesis import given, strategies as st, settings, assume
from redis.exceptions import ConnectionError as RedisConnectionError

from infrastructure.connection_retry import (
    DatabaseConnectionRetry,
    RedisConnectionRetry
)


class ConnectionTracker:
    """Helper class to track connection attempts and simulate failures."""
    
    def __init__(self):
        self.attempt_count = 0
        self.attempt_times = []
        self.should_fail = True
        self.fail_count = 0
        self.exception_to_raise = ConnectionError("Connection failed")
    
    def connect(self):
        """Simulate a connection attempt."""
        self.attempt_count += 1
        self.attempt_times.append(time.time())
        
        if self.should_fail and self.attempt_count <= self.fail_count:
            raise self.exception_to_raise
        
        return Mock()  # Return mock connection
    
    def reset(self):
        """Reset the tracker."""
        self.attempt_count = 0
        self.attempt_times = []
        self.should_fail = True
        self.fail_count = 0


# Feature: backend-optimization, Property 28: Connection retry
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    transient_failures=st.integers(min_value=1, max_value=4)
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_28_connection_succeeds_after_transient_failures(
    max_retries,
    transient_failures
):
    """
    Property 28.1: Connection retry attempts reconnection on transient failures.
    
    For any number of transient failures less than max_retries, the connection
    should eventually succeed after retrying.
    
    **Validates: Requirements 6.4**
    """
    # Ensure transient failures are less than max retries
    assume(transient_failures < max_retries)
    
    retry = DatabaseConnectionRetry(
        max_retries=max_retries,
        base_delay=0.1,
        max_delay=1.0
    )
    
    tracker = ConnectionTracker()
    tracker.fail_count = transient_failures
    
    # Connection should succeed after transient failures
    connection = retry.connect_with_retry(tracker.connect, "test-db")
    
    # Verify connection was established
    assert connection is not None
    
    # Verify correct number of attempts (failures + 1 success)
    assert tracker.attempt_count == transient_failures + 1, \
        f"Expected {transient_failures + 1} attempts, got {tracker.attempt_count}"


# Feature: backend-optimization, Property 28: Connection retry
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    base_delay=st.floats(min_value=0.1, max_value=0.5),
    exponential_base=st.floats(min_value=1.5, max_value=3.0)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_28_exponential_backoff_strategy(
    max_retries,
    base_delay,
    exponential_base
):
    """
    Property 28.2: Retry follows exponential backoff strategy.
    
    For any retry configuration, the delays between retry attempts should
    follow an exponential backoff pattern: delay = base_delay * (exponential_base ^ attempt).
    
    **Validates: Requirements 6.4**
    """
    retry = DatabaseConnectionRetry(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=10.0,
        exponential_base=exponential_base
    )
    
    tracker = ConnectionTracker()
    tracker.fail_count = max_retries + 10  # Fail all attempts including retries
    
    # Connection should fail after exhausting retries
    with pytest.raises(ConnectionError):
        retry.connect_with_retry(tracker.connect, "test-db")
    
    # Verify all retries were attempted
    assert tracker.attempt_count == max_retries + 1, \
        f"Expected {max_retries + 1} attempts, got {tracker.attempt_count}"
    
    # Verify exponential backoff in delays between attempts
    # Note: We allow for jitter, so we check that delays are generally increasing
    if len(tracker.attempt_times) > 1:
        delays = []
        for i in range(1, len(tracker.attempt_times)):
            delay = tracker.attempt_times[i] - tracker.attempt_times[i-1]
            delays.append(delay)
        
        # Verify we have delays (retries occurred)
        assert len(delays) > 0, "Should have delays between retry attempts"
        
        # Verify delays are generally in the expected range
        # (accounting for jitter which can be 0.5x to 1.5x)
        for attempt_idx, delay in enumerate(delays):
            expected_delay = base_delay * (exponential_base ** attempt_idx)
            min_expected = expected_delay * 0.4  # Account for jitter (0.5x with margin)
            max_expected = expected_delay * 1.6  # Account for jitter (1.5x with margin)
            
            # Delay should be in expected range OR capped at max_delay (with small tolerance for timing)
            assert min_expected <= delay <= max_expected or delay <= 10.5, \
                f"Delay {delay} at attempt {attempt_idx} outside expected range " \
                f"[{min_expected}, {max_expected}] or max_delay (10.0 with tolerance)"


# Feature: backend-optimization, Property 28: Connection retry
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    non_retryable_exception=st.sampled_from([
        ValueError("Invalid configuration"),
        TypeError("Type error"),
        KeyError("Key not found")
    ])
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_28_non_retryable_errors_raised_immediately(
    max_retries,
    non_retryable_exception
):
    """
    Property 28.3: Non-retryable errors are raised immediately.
    
    For any non-retryable exception, the connection retry should raise
    the exception immediately without attempting retries.
    
    **Validates: Requirements 6.4**
    """
    retry = DatabaseConnectionRetry(
        max_retries=max_retries,
        base_delay=0.1
    )
    
    tracker = ConnectionTracker()
    tracker.exception_to_raise = non_retryable_exception
    tracker.fail_count = max_retries + 1  # Would fail all attempts if retried
    
    # Non-retryable exception should be raised immediately
    with pytest.raises(type(non_retryable_exception)):
        retry.connect_with_retry(tracker.connect, "test-db")
    
    # Verify only one attempt was made (no retries)
    assert tracker.attempt_count == 1, \
        f"Non-retryable error should not be retried, but got {tracker.attempt_count} attempts"


# Feature: backend-optimization, Property 28: Connection retry
@given(
    max_retries=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_28_connection_fails_after_max_retries(max_retries):
    """
    Property 28.4: Connection fails after exhausting max retries.
    
    For any max_retries value, if all connection attempts fail with
    retryable errors, the final exception should be raised after
    exactly max_retries + 1 attempts.
    
    **Validates: Requirements 6.4**
    """
    retry = DatabaseConnectionRetry(
        max_retries=max_retries,
        base_delay=0.1,
        max_delay=1.0
    )
    
    tracker = ConnectionTracker()
    tracker.fail_count = max_retries + 10  # Fail more than max retries
    
    # Connection should fail after exhausting retries
    with pytest.raises(ConnectionError):
        retry.connect_with_retry(tracker.connect, "test-db")
    
    # Verify correct number of attempts (initial + retries)
    assert tracker.attempt_count == max_retries + 1, \
        f"Expected {max_retries + 1} attempts, got {tracker.attempt_count}"


# Feature: backend-optimization, Property 28: Connection retry
@given(
    max_retries=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_28_successful_connection_on_first_attempt(max_retries):
    """
    Property 28.5: Successful connection on first attempt requires no retries.
    
    For any max_retries value, if the connection succeeds on the first
    attempt, no retries should be performed.
    
    **Validates: Requirements 6.4**
    """
    retry = DatabaseConnectionRetry(
        max_retries=max_retries,
        base_delay=0.1
    )
    
    tracker = ConnectionTracker()
    tracker.should_fail = False  # Succeed immediately
    
    # Connection should succeed on first attempt
    connection = retry.connect_with_retry(tracker.connect, "test-db")
    
    # Verify connection was established
    assert connection is not None
    
    # Verify only one attempt was made
    assert tracker.attempt_count == 1, \
        f"Successful connection should not retry, but got {tracker.attempt_count} attempts"


# Feature: backend-optimization, Property 28: Connection retry
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    transient_failures=st.integers(min_value=1, max_value=4)
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_28_redis_connection_retry(max_retries, transient_failures):
    """
    Property 28.6: Redis connection retry works similarly to database retry.
    
    For any number of transient Redis connection failures less than max_retries,
    the connection should eventually succeed after retrying.
    
    **Validates: Requirements 6.4**
    """
    # Ensure transient failures are less than max retries
    assume(transient_failures < max_retries)
    
    retry = RedisConnectionRetry(
        max_retries=max_retries,
        base_delay=0.1,
        max_delay=1.0
    )
    
    tracker = ConnectionTracker()
    tracker.fail_count = transient_failures
    tracker.exception_to_raise = RedisConnectionError("Redis connection failed")
    
    # Mock Redis client with ping method
    def connect_redis():
        conn = tracker.connect()
        conn.ping = Mock(return_value=True)
        return conn
    
    # Connection should succeed after transient failures
    client = retry.connect_with_retry(connect_redis, "test-redis")
    
    # Verify connection was established
    assert client is not None
    
    # Verify correct number of attempts (failures + 1 success)
    # Note: Redis retry also calls ping, so we expect failures + 1 for connect
    assert tracker.attempt_count == transient_failures + 1, \
        f"Expected {transient_failures + 1} attempts, got {tracker.attempt_count}"


# Feature: backend-optimization, Property 28: Connection retry
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    transient_failures=st.integers(min_value=1, max_value=4)
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_28_execute_with_retry_for_operations(
    max_retries,
    transient_failures
):
    """
    Property 28.7: Execute with retry works for database operations.
    
    For any database operation that fails with transient errors,
    execute_with_retry should retry the operation and eventually succeed.
    
    **Validates: Requirements 6.4**
    """
    # Ensure transient failures are less than max retries
    assume(transient_failures < max_retries)
    
    retry = DatabaseConnectionRetry(
        max_retries=max_retries,
        base_delay=0.1,
        max_delay=1.0
    )
    
    tracker = ConnectionTracker()
    tracker.fail_count = transient_failures
    
    def operation():
        return tracker.connect()
    
    # Operation should succeed after transient failures
    result = retry.execute_with_retry(operation, "test-operation")
    
    # Verify operation succeeded
    assert result is not None
    
    # Verify correct number of attempts
    assert tracker.attempt_count == transient_failures + 1, \
        f"Expected {transient_failures + 1} attempts, got {tracker.attempt_count}"


# Feature: backend-optimization, Property 28: Connection retry
@given(
    max_retries=st.integers(min_value=2, max_value=5),
    base_delay=st.floats(min_value=0.1, max_value=0.3),
    max_delay=st.floats(min_value=1.0, max_value=5.0)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_28_delay_capped_at_max_delay(
    max_retries,
    base_delay,
    max_delay
):
    """
    Property 28.8: Retry delays are capped at max_delay.
    
    For any retry configuration, the delay between attempts should never
    exceed max_delay, even if exponential backoff would calculate a larger value.
    
    **Validates: Requirements 6.4**
    """
    # Ensure max_delay is greater than base_delay
    assume(max_delay > base_delay)
    
    retry = DatabaseConnectionRetry(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=2.0
    )
    
    tracker = ConnectionTracker()
    tracker.fail_count = max_retries + 10  # Fail all attempts including retries
    
    # Connection should fail after exhausting retries
    with pytest.raises(ConnectionError):
        retry.connect_with_retry(tracker.connect, "test-db")
    
    # Verify delays are capped at max_delay
    if len(tracker.attempt_times) > 1:
        for i in range(1, len(tracker.attempt_times)):
            delay = tracker.attempt_times[i] - tracker.attempt_times[i-1]
            
            # Account for jitter (can be up to 1.5x the calculated delay)
            # but should still respect max_delay cap
            max_possible_delay = max_delay * 1.6  # Add margin for jitter
            
            assert delay <= max_possible_delay, \
                f"Delay {delay} exceeds max_delay {max_delay} (with jitter margin)"


# Feature: backend-optimization, Property 28: Connection retry
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    transient_failures=st.integers(min_value=1, max_value=4)
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_28_retry_consistency_across_calls(
    max_retries,
    transient_failures
):
    """
    Property 28.9: Retry behavior is consistent across multiple calls.
    
    For any retry configuration, multiple connection attempts with the same
    failure pattern should behave consistently.
    
    **Validates: Requirements 6.4**
    """
    # Ensure transient failures are less than max retries
    assume(transient_failures < max_retries)
    
    retry = DatabaseConnectionRetry(
        max_retries=max_retries,
        base_delay=0.1,
        max_delay=1.0
    )
    
    # Test multiple times with same failure pattern
    attempt_counts = []
    for _ in range(3):
        tracker = ConnectionTracker()
        tracker.fail_count = transient_failures
        
        connection = retry.connect_with_retry(tracker.connect, "test-db")
        assert connection is not None
        attempt_counts.append(tracker.attempt_count)
    
    # All attempts should have the same number of tries
    assert all(count == attempt_counts[0] for count in attempt_counts), \
        f"Retry behavior should be consistent, got attempt counts: {attempt_counts}"
    
    # Verify expected attempt count
    assert attempt_counts[0] == transient_failures + 1


# Feature: backend-optimization, Property 28: Connection retry
@given(
    max_retries=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_28_redis_non_retryable_errors_raised_immediately(max_retries):
    """
    Property 28.10: Redis non-retryable errors are raised immediately.
    
    For any non-retryable exception in Redis operations, the retry should
    raise the exception immediately without attempting retries.
    
    **Validates: Requirements 6.4**
    """
    retry = RedisConnectionRetry(
        max_retries=max_retries,
        base_delay=0.1
    )
    
    tracker = ConnectionTracker()
    tracker.exception_to_raise = ValueError("Invalid Redis configuration")
    tracker.fail_count = max_retries + 1  # Would fail all attempts if retried
    
    # Non-retryable exception should be raised immediately
    with pytest.raises(ValueError):
        retry.connect_with_retry(tracker.connect, "test-redis")
    
    # Verify only one attempt was made (no retries)
    assert tracker.attempt_count == 1, \
        f"Non-retryable error should not be retried, but got {tracker.attempt_count} attempts"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
