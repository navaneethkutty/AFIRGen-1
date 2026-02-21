"""
test_property_task_retry.py
-----------------------------------------------------------------------------
Property-Based Tests for Task Retry with Exponential Backoff
-----------------------------------------------------------------------------

Property tests for background task retry mechanism using Hypothesis to verify:
- Property 18: Task retry with exponential backoff

Requirements Validated: 4.3 (Background Job Processing - Retry Handler)
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, MagicMock, patch
import time
import socket

from infrastructure.tasks.base_task import (
    DatabaseTask,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BASE_DELAY,
    DEFAULT_MAX_DELAY,
    DEFAULT_EXPONENTIAL_BASE,
)


# Feature: backend-optimization, Property 18: Task retry with exponential backoff
@given(
    retry_count=st.integers(min_value=0, max_value=10),
    base_delay=st.floats(min_value=0.1, max_value=10.0),
    exponential_base=st.floats(min_value=1.5, max_value=5.0),
    max_delay=st.floats(min_value=10.0, max_value=600.0)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_exponential_backoff_calculation(retry_count, base_delay, exponential_base, max_delay):
    """
    Property 18: For any background task that fails with a retryable error,
    the Retry_Handler should retry the task with exponentially increasing
    delays between attempts.
    
    **Validates: Requirements 4.3**
    
    This property verifies that:
    1. Retry delay increases exponentially with retry count
    2. Delay follows formula: base_delay * (exponential_base ^ retry_count)
    3. Delay is capped at max_delay
    4. Delay is always non-negative
    """
    # Ensure max_delay is greater than base_delay for meaningful test
    assume(max_delay >= base_delay)
    
    task = DatabaseTask()
    
    # Calculate delay without jitter for deterministic testing
    delay = task.calculate_retry_delay(
        retry_count=retry_count,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=False
    )
    
    # Property assertions
    
    # 1. Delay should be non-negative
    assert delay >= 0, "Retry delay must be non-negative"
    
    # 2. Calculate expected delay (before capping)
    expected_delay = base_delay * (exponential_base ** retry_count)
    
    # 3. Delay should match expected or be capped at max_delay
    if expected_delay <= max_delay:
        assert abs(delay - expected_delay) < 0.001, \
            f"Delay should match exponential formula: {base_delay} * {exponential_base}^{retry_count} = {expected_delay}"
    else:
        assert delay == max_delay, \
            f"Delay should be capped at max_delay ({max_delay}) when exponential exceeds it"
    
    # 4. Delay should never exceed max_delay
    assert delay <= max_delay, \
        f"Delay ({delay}) must not exceed max_delay ({max_delay})"


@given(
    retry_count=st.integers(min_value=0, max_value=5),
    base_delay=st.floats(min_value=1.0, max_value=5.0),
    exponential_base=st.floats(min_value=2.0, max_value=3.0)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_exponential_growth(retry_count, base_delay, exponential_base):
    """
    Property 18 (extended): For any sequence of retry attempts,
    each subsequent retry delay should be larger than the previous
    (exponential growth property).
    
    **Validates: Requirements 4.3**
    
    This property verifies that delays increase monotonically
    with retry count (until max_delay is reached).
    """
    task = DatabaseTask()
    max_delay = 1000.0  # High enough to not interfere
    
    # Calculate delays for current and next retry
    if retry_count > 0:
        previous_delay = task.calculate_retry_delay(
            retry_count=retry_count - 1,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=False
        )
    else:
        previous_delay = 0
    
    current_delay = task.calculate_retry_delay(
        retry_count=retry_count,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=False
    )
    
    # Property assertions
    
    # 1. Current delay should be at least as large as previous
    if retry_count > 0:
        assert current_delay >= previous_delay, \
            f"Delay should increase with retry count: retry {retry_count-1} = {previous_delay}s, " \
            f"retry {retry_count} = {current_delay}s"
    
    # 2. For exponential_base > 1, delay should strictly increase
    if retry_count > 0 and exponential_base > 1.0:
        # Allow for floating point precision
        assert current_delay > previous_delay * 0.999, \
            "Delay should grow exponentially with base > 1"


@given(
    retry_count=st.integers(min_value=0, max_value=5),
    base_delay=st.floats(min_value=1.0, max_value=10.0)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_jitter_adds_randomness(retry_count, base_delay):
    """
    Property 18 (extended): For any retry delay calculation with jitter enabled,
    the actual delay should vary within acceptable bounds around the base calculation.
    
    **Validates: Requirements 4.3**
    
    This property verifies that jitter adds randomness to prevent
    thundering herd problem while keeping delays within reasonable bounds.
    """
    task = DatabaseTask()
    exponential_base = 2.0
    max_delay = 1000.0
    
    # Calculate base delay without jitter
    base_calculated_delay = task.calculate_retry_delay(
        retry_count=retry_count,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=False
    )
    
    # Calculate multiple delays with jitter
    jittered_delays = [
        task.calculate_retry_delay(
            retry_count=retry_count,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=True
        )
        for _ in range(10)
    ]
    
    # Property assertions
    
    # 1. Jittered delays should vary (not all identical)
    # Allow for small chance of collision in random values
    unique_delays = len(set(jittered_delays))
    assert unique_delays >= 3, \
        f"Jitter should produce varied delays (got {unique_delays} unique values out of 10)"
    
    # 2. All jittered delays should be within ±20% of base calculation
    for delay in jittered_delays:
        lower_bound = base_calculated_delay * 0.8
        upper_bound = base_calculated_delay * 1.2
        assert lower_bound <= delay <= upper_bound, \
            f"Jittered delay ({delay}) should be within ±20% of base ({base_calculated_delay})"
    
    # 3. All delays should be non-negative
    for delay in jittered_delays:
        assert delay >= 0, "Jittered delay must be non-negative"


@given(
    max_retries=st.integers(min_value=1, max_value=10),
    current_retry=st.integers(min_value=0, max_value=15)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_retry_exhaustion(max_retries, current_retry):
    """
    Property 18 (extended): For any task that has exhausted its retry attempts,
    the retry handler should raise the exception without further retries.
    
    **Validates: Requirements 4.3**
    
    This property verifies that tasks stop retrying after max_retries
    and propagate the exception.
    """
    task = DatabaseTask()
    task.name = "test_task"
    task.max_retries = max_retries
    
    # Create a mock request object
    mock_request = Mock()
    mock_request.id = "test-task-id"
    mock_request.retries = current_retry
    
    # Patch the request property
    with patch.object(type(task), 'request', new_callable=lambda: mock_request):
        exc = ConnectionError("Test connection error")
        
        if current_retry >= max_retries:
            # Should raise exception without retrying
            with pytest.raises(ConnectionError, match="Test connection error"):
                task.retry_with_backoff(exc=exc, max_retries=max_retries)
        else:
            # Should attempt retry (will raise Retry exception)
            with patch.object(task, 'retry') as mock_retry:
                mock_retry.side_effect = Exception("Retry called")
                
                with pytest.raises(Exception, match="Retry called"):
                    task.retry_with_backoff(exc=exc, max_retries=max_retries)
                
                # Verify retry was called with appropriate countdown
                assert mock_retry.called, "Task should attempt retry when under max_retries"
                call_kwargs = mock_retry.call_args[1]
                assert 'countdown' in call_kwargs, "Retry should include countdown"
                assert call_kwargs['countdown'] >= 0, "Countdown should be non-negative"


@given(
    error_type=st.sampled_from([
        socket.timeout(),
        TimeoutError("Connection timeout"),
        ConnectionError("Connection failed"),
        ConnectionRefusedError("Connection refused"),
        ConnectionResetError("Connection reset"),
        BrokenPipeError("Broken pipe"),
    ])
)
@settings(max_examples=10, deadline=None)
@pytest.mark.property_test
def test_property_retryable_error_classification(error_type):
    """
    Property 18 (extended): For any network or connection error,
    the error should be classified as retryable.
    
    **Validates: Requirements 4.3, 6.5**
    
    This property verifies that transient errors are correctly
    identified as retryable.
    """
    # Property assertion
    assert DatabaseTask.is_retryable_error(error_type), \
        f"Network/connection error {type(error_type).__name__} should be retryable"


@given(
    error_type=st.sampled_from([
        ValueError("Invalid input"),
        TypeError("Type mismatch"),
        KeyError("Missing key"),
        AttributeError("Missing attribute"),
    ])
)
@settings(max_examples=10, deadline=None)
@pytest.mark.property_test
def test_property_non_retryable_error_classification(error_type):
    """
    Property 18 (extended): For any validation or programming error,
    the error should be classified as non-retryable.
    
    **Validates: Requirements 4.3, 6.5**
    
    This property verifies that permanent errors are correctly
    identified as non-retryable.
    """
    # Property assertion
    assert not DatabaseTask.is_retryable_error(error_type), \
        f"Validation/programming error {type(error_type).__name__} should not be retryable"


@given(
    error_message=st.sampled_from([
        "Rate limit exceeded",
        "Too many requests",
        "429 Too Many Requests",
        "Service temporarily unavailable",
        "503 Service Unavailable",
        "Gateway timeout",
        "Bad gateway",
        "Connection timeout",
    ])
)
@settings(max_examples=10, deadline=None)
@pytest.mark.property_test
def test_property_retryable_error_message_patterns(error_message):
    """
    Property 18 (extended): For any error with retryable message patterns,
    the error should be classified as retryable.
    
    **Validates: Requirements 4.3, 6.5**
    
    This property verifies that errors with specific message patterns
    (rate limits, service unavailable, etc.) are identified as retryable.
    """
    exc = Exception(error_message)
    
    # Property assertion
    assert DatabaseTask.is_retryable_error(exc), \
        f"Error with message '{error_message}' should be retryable"


@given(
    retry_count=st.integers(min_value=0, max_value=5),
    base_delay=st.floats(min_value=0.5, max_value=5.0),
    exponential_base=st.floats(min_value=2.0, max_value=3.0)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_retry_delay_consistency(retry_count, base_delay, exponential_base):
    """
    Property 18 (extended): For any given retry parameters,
    calculating the delay multiple times should produce consistent results
    (when jitter is disabled).
    
    **Validates: Requirements 4.3**
    
    This property verifies that the retry delay calculation is deterministic
    when jitter is disabled.
    """
    task = DatabaseTask()
    max_delay = 1000.0
    
    # Calculate delay multiple times
    delays = [
        task.calculate_retry_delay(
            retry_count=retry_count,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=False
        )
        for _ in range(5)
    ]
    
    # Property assertions
    
    # 1. All delays should be identical (deterministic)
    assert len(set(delays)) == 1, \
        "Retry delay calculation should be deterministic when jitter is disabled"
    
    # 2. Delay should match expected formula
    expected_delay = min(base_delay * (exponential_base ** retry_count), max_delay)
    assert abs(delays[0] - expected_delay) < 0.001, \
        f"Delay should match formula: min({base_delay} * {exponential_base}^{retry_count}, {max_delay})"


@given(
    retry_sequence=st.lists(
        st.integers(min_value=0, max_value=5),
        min_size=2,
        max_size=6,
        unique=True
    ).map(sorted)  # Ensure sequence is sorted (increasing retry counts)
)
@settings(max_examples=10, deadline=None)
@pytest.mark.property_test
def test_property_retry_sequence_monotonic_increase(retry_sequence):
    """
    Property 18 (extended): For any sequence of increasing retry counts,
    the calculated delays should form a monotonically increasing sequence
    (until max_delay is reached).
    
    **Validates: Requirements 4.3**
    
    This property verifies that retry delays increase consistently
    across a sequence of retries.
    """
    task = DatabaseTask()
    base_delay = 1.0
    exponential_base = 2.0
    max_delay = 1000.0
    
    # Calculate delays for the sequence
    delays = [
        task.calculate_retry_delay(
            retry_count=count,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=False
        )
        for count in retry_sequence
    ]
    
    # Property assertions
    
    # 1. Delays should be monotonically increasing (or equal if capped)
    for i in range(1, len(delays)):
        assert delays[i] >= delays[i-1], \
            f"Delay sequence should be monotonically increasing: " \
            f"retry {retry_sequence[i-1]} = {delays[i-1]}s, " \
            f"retry {retry_sequence[i]} = {delays[i]}s"
    
    # 2. If not capped, delays should strictly increase
    if all(d < max_delay for d in delays):
        for i in range(1, len(delays)):
            assert delays[i] > delays[i-1], \
                "Delays should strictly increase when not capped at max_delay"


@given(
    base_delay=st.floats(min_value=0.1, max_value=5.0),
    max_delay=st.floats(min_value=10.0, max_value=100.0),
    exponential_base=st.floats(min_value=2.0, max_value=4.0)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_max_delay_cap_enforcement(base_delay, max_delay, exponential_base):
    """
    Property 18 (extended): For any retry count that would produce a delay
    exceeding max_delay, the actual delay should be capped at max_delay.
    
    **Validates: Requirements 4.3**
    
    This property verifies that the max_delay cap is always enforced,
    preventing unbounded retry delays.
    """
    task = DatabaseTask()
    
    # Use a high retry count that will definitely exceed max_delay
    high_retry_count = 20
    
    delay = task.calculate_retry_delay(
        retry_count=high_retry_count,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=False
    )
    
    # Property assertions
    
    # 1. Delay should not exceed max_delay
    assert delay <= max_delay, \
        f"Delay ({delay}) must be capped at max_delay ({max_delay})"
    
    # 2. For high retry counts, delay should equal max_delay
    expected_uncapped = base_delay * (exponential_base ** high_retry_count)
    if expected_uncapped > max_delay:
        assert delay == max_delay, \
            f"Delay should be exactly max_delay ({max_delay}) when exponential exceeds it"


@given(
    retry_count=st.integers(min_value=0, max_value=3),
    base_delay=st.floats(min_value=1.0, max_value=5.0)
)
@settings(max_examples=10, deadline=None)
@pytest.mark.property_test
def test_property_retry_with_backoff_integration(retry_count, base_delay):
    """
    Property 18 (extended): For any retryable error at a given retry count,
    the retry_with_backoff method should calculate appropriate delay
    and attempt retry with that countdown.
    
    **Validates: Requirements 4.3**
    
    This property verifies the integration between retry decision,
    delay calculation, and retry execution.
    """
    task = DatabaseTask()
    task.name = "test_task"
    task.max_retries = 5
    
    # Create a mock request object
    mock_request = Mock()
    mock_request.id = "test-task-id"
    mock_request.retries = retry_count
    
    # Patch the request property
    with patch.object(type(task), 'request', new_callable=lambda: mock_request):
        with patch.object(task, 'retry') as mock_retry:
            mock_retry.side_effect = Exception("Retry called")
            
            exc = ConnectionError("Test connection error")
            
            # Attempt retry
            with pytest.raises(Exception, match="Retry called"):
                task.retry_with_backoff(
                    exc=exc,
                    base_delay=base_delay,
                    exponential_base=2.0,
                    jitter=False
                )
            
            # Property assertions
            
            # 1. Retry should be called
            assert mock_retry.called, "Retry should be attempted"
            
            # 2. Countdown should match calculated delay
            call_kwargs = mock_retry.call_args[1]
            countdown = call_kwargs['countdown']
            
            expected_delay = task.calculate_retry_delay(
                retry_count=retry_count,
                base_delay=base_delay,
                exponential_base=2.0,
                jitter=False
            )
            
            assert abs(countdown - expected_delay) < 0.001, \
                f"Retry countdown ({countdown}) should match calculated delay ({expected_delay})"
            
            # 3. Exception should be passed to retry
            assert call_kwargs['exc'] == exc, \
                "Original exception should be passed to retry"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property_test"])
