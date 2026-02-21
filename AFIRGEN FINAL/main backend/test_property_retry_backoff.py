"""
test_property_retry_backoff.py
-----------------------------------------------------------------------------
Property-Based Tests for Retry with Exponential Backoff
-----------------------------------------------------------------------------

Property tests for retry handler mechanism using Hypothesis to verify:
- Property 25: Retry with exponential backoff

Requirements Validated: 6.1 (Error Handling and Retry Mechanisms)
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch
import time

from infrastructure.retry_handler import (
    RetryHandler,
    retry,
    get_retry_handler,
    NETWORK_EXCEPTIONS
)


# Feature: backend-optimization, Property 25: Retry with exponential backoff
@given(
    attempt=st.integers(min_value=0, max_value=10),
    base_delay=st.floats(min_value=0.1, max_value=10.0),
    exponential_base=st.floats(min_value=1.5, max_value=5.0),
    max_delay=st.floats(min_value=10.0, max_value=600.0)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_exponential_backoff_formula(attempt, base_delay, exponential_base, max_delay):
    """
    Property 25: For any operation that fails with a transient error,
    the Retry_Handler should retry the operation with delays that increase
    exponentially (base_delay * exponential_base^retry_count).
    
    **Validates: Requirements 6.1**
    
    This property verifies that:
    1. Retry delay follows exponential backoff formula
    2. Delay is capped at max_delay
    3. Delay is always non-negative
    """
    # Ensure max_delay is greater than base_delay for meaningful test
    assume(max_delay >= base_delay)
    
    handler = RetryHandler(
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=False  # Disable jitter for deterministic testing
    )
    
    # Calculate delay
    delay = handler.calculate_delay(attempt)
    
    # Property assertions
    
    # 1. Delay should be non-negative
    assert delay >= 0, "Retry delay must be non-negative"
    
    # 2. Calculate expected delay (before capping)
    expected_delay = base_delay * (exponential_base ** attempt)
    
    # 3. Delay should match expected or be capped at max_delay
    if expected_delay <= max_delay:
        assert abs(delay - expected_delay) < 0.001, \
            f"Delay should match exponential formula: {base_delay} * {exponential_base}^{attempt} = {expected_delay}"
    else:
        assert delay == max_delay, \
            f"Delay should be capped at max_delay ({max_delay}) when exponential exceeds it"
    
    # 4. Delay should never exceed max_delay
    assert delay <= max_delay, \
        f"Delay ({delay}) must not exceed max_delay ({max_delay})"


@given(
    attempt=st.integers(min_value=0, max_value=5),
    base_delay=st.floats(min_value=1.0, max_value=5.0),
    exponential_base=st.floats(min_value=2.0, max_value=3.0)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_exponential_growth(attempt, base_delay, exponential_base):
    """
    Property 25 (extended): For any sequence of retry attempts,
    each subsequent retry delay should be larger than the previous
    (exponential growth property).
    
    **Validates: Requirements 6.1**
    
    This property verifies that delays increase monotonically
    with attempt count (until max_delay is reached).
    """
    handler = RetryHandler(
        base_delay=base_delay,
        max_delay=1000.0,  # High enough to not interfere
        exponential_base=exponential_base,
        jitter=False
    )
    
    # Calculate delays for current and next attempt
    if attempt > 0:
        previous_delay = handler.calculate_delay(attempt - 1)
    else:
        previous_delay = 0
    
    current_delay = handler.calculate_delay(attempt)
    
    # Property assertions
    
    # 1. Current delay should be at least as large as previous
    if attempt > 0:
        assert current_delay >= previous_delay, \
            f"Delay should increase with attempt count: attempt {attempt-1} = {previous_delay}s, " \
            f"attempt {attempt} = {current_delay}s"
    
    # 2. For exponential_base > 1, delay should strictly increase
    if attempt > 0 and exponential_base > 1.0:
        # Allow for floating point precision
        assert current_delay > previous_delay * 0.999, \
            "Delay should grow exponentially with base > 1"


@given(
    attempt=st.integers(min_value=0, max_value=5),
    base_delay=st.floats(min_value=1.0, max_value=10.0)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_jitter_range(attempt, base_delay):
    """
    Property 25 (extended): For any retry delay calculation with jitter enabled,
    the jitter should be within the range of 0.5 to 1.5 of the base delay.
    
    **Validates: Requirements 6.1**
    
    This property verifies that jitter adds randomness within acceptable bounds
    to prevent thundering herd problem.
    """
    handler = RetryHandler(
        base_delay=base_delay,
        max_delay=1000.0,
        exponential_base=2.0,
        jitter=True
    )
    
    # Calculate base delay without jitter
    base_calculated_delay = RetryHandler(
        base_delay=base_delay,
        max_delay=1000.0,
        exponential_base=2.0,
        jitter=False
    ).calculate_delay(attempt)
    
    # Calculate multiple delays with jitter
    jittered_delays = [handler.calculate_delay(attempt) for _ in range(20)]
    
    # Property assertions
    
    # 1. Jittered delays should vary (not all identical)
    unique_delays = len(set(jittered_delays))
    assert unique_delays >= 5, \
        f"Jitter should produce varied delays (got {unique_delays} unique values out of 20)"
    
    # 2. All jittered delays should be within [0.5, 1.5] range of base calculation
    for delay in jittered_delays:
        lower_bound = base_calculated_delay * 0.5
        upper_bound = base_calculated_delay * 1.5
        assert lower_bound <= delay <= upper_bound, \
            f"Jittered delay ({delay}) should be within [0.5, 1.5] of base ({base_calculated_delay})"
    
    # 3. All delays should be non-negative
    for delay in jittered_delays:
        assert delay >= 0, "Jittered delay must be non-negative"


@given(
    max_retries=st.integers(min_value=1, max_value=5),
    failure_count=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_max_retries_respected(max_retries, failure_count):
    """
    Property 25 (extended): For any operation that fails repeatedly,
    the retry handler should respect the max_retries limit and stop retrying.
    
    **Validates: Requirements 6.1**
    
    This property verifies that the retry handler doesn't retry indefinitely
    and respects the configured max_retries limit.
    """
    handler = RetryHandler(
        max_retries=max_retries,
        base_delay=0.01,  # Small delay for fast testing
        jitter=False
    )
    
    # Create a mock function that always fails
    mock_func = Mock(side_effect=ConnectionError("Always fails"))
    
    # Attempt to execute with retry
    with pytest.raises(ConnectionError):
        handler.execute_with_retry(
            mock_func,
            retryable_exceptions=(ConnectionError,)
        )
    
    # Property assertions
    
    # 1. Function should be called exactly max_retries + 1 times
    # (initial attempt + max_retries retry attempts)
    expected_calls = max_retries + 1
    assert mock_func.call_count == expected_calls, \
        f"Function should be called {expected_calls} times (1 initial + {max_retries} retries), " \
        f"but was called {mock_func.call_count} times"


@given(
    retryable_exception=st.sampled_from([
        ConnectionError("Connection failed"),
        TimeoutError("Request timeout"),
        OSError("OS error"),
    ]),
    max_retries=st.integers(min_value=1, max_value=3)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_retryable_exceptions_trigger_retry(retryable_exception, max_retries):
    """
    Property 25 (extended): For any retryable exception,
    the retry handler should attempt retries up to max_retries.
    
    **Validates: Requirements 6.1**
    
    This property verifies that retryable exceptions trigger the retry mechanism.
    """
    handler = RetryHandler(
        max_retries=max_retries,
        base_delay=0.01,
        jitter=False
    )
    
    # Create a mock function that fails with retryable exception
    mock_func = Mock(side_effect=retryable_exception)
    
    # Attempt to execute with retry
    with pytest.raises(type(retryable_exception)):
        handler.execute_with_retry(
            mock_func,
            retryable_exceptions=(ConnectionError, TimeoutError, OSError)
        )
    
    # Property assertions
    
    # 1. Function should be called multiple times (retries occurred)
    assert mock_func.call_count > 1, \
        f"Retryable exception should trigger retries (called {mock_func.call_count} times)"
    
    # 2. Function should be called exactly max_retries + 1 times
    expected_calls = max_retries + 1
    assert mock_func.call_count == expected_calls, \
        f"Should retry {max_retries} times after initial failure"


@given(
    non_retryable_exception=st.sampled_from([
        ValueError("Invalid input"),
        TypeError("Type error"),
        KeyError("Key not found"),
        AttributeError("Attribute error"),
    ])
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_non_retryable_exceptions_no_retry(non_retryable_exception):
    """
    Property 25 (extended): For any non-retryable exception,
    the retry handler should raise immediately without retrying.
    
    **Validates: Requirements 6.1**
    
    This property verifies that non-retryable exceptions don't trigger retries.
    """
    handler = RetryHandler(
        max_retries=3,
        base_delay=0.01,
        jitter=False
    )
    
    # Create a mock function that fails with non-retryable exception
    mock_func = Mock(side_effect=non_retryable_exception)
    
    # Attempt to execute with retry (only ConnectionError is retryable)
    with pytest.raises(type(non_retryable_exception)):
        handler.execute_with_retry(
            mock_func,
            retryable_exceptions=(ConnectionError,)
        )
    
    # Property assertions
    
    # 1. Function should be called exactly once (no retries)
    assert mock_func.call_count == 1, \
        f"Non-retryable exception should not trigger retries (called {mock_func.call_count} times)"


@given(
    success_after=st.integers(min_value=1, max_value=3)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_successful_execution_stops_retrying(success_after):
    """
    Property 25 (extended): For any operation that succeeds after N failures,
    the retry handler should stop retrying and return the successful result.
    
    **Validates: Requirements 6.1**
    
    This property verifies that successful execution stops the retry loop.
    """
    handler = RetryHandler(
        max_retries=5,
        base_delay=0.01,
        jitter=False
    )
    
    # Create a mock function that fails N times then succeeds
    failures = [ConnectionError("Failed")] * success_after
    mock_func = Mock(side_effect=failures + ["success"])
    
    # Execute with retry
    result = handler.execute_with_retry(
        mock_func,
        retryable_exceptions=(ConnectionError,)
    )
    
    # Property assertions
    
    # 1. Result should be the success value
    assert result == "success", "Should return successful result"
    
    # 2. Function should be called exactly success_after + 1 times
    expected_calls = success_after + 1
    assert mock_func.call_count == expected_calls, \
        f"Should stop retrying after success (called {mock_func.call_count} times, expected {expected_calls})"


@given(
    base_delay=st.floats(min_value=0.1, max_value=5.0),
    max_delay=st.floats(min_value=10.0, max_value=100.0),
    exponential_base=st.floats(min_value=2.0, max_value=4.0)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_max_delay_cap_enforcement(base_delay, max_delay, exponential_base):
    """
    Property 25 (extended): For any retry attempt that would produce a delay
    exceeding max_delay, the actual delay should be capped at max_delay.
    
    **Validates: Requirements 6.1**
    
    This property verifies that the max_delay cap is always enforced,
    preventing unbounded retry delays.
    """
    handler = RetryHandler(
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=False
    )
    
    # Use a high attempt count that will definitely exceed max_delay
    high_attempt = 20
    
    delay = handler.calculate_delay(high_attempt)
    
    # Property assertions
    
    # 1. Delay should not exceed max_delay
    assert delay <= max_delay, \
        f"Delay ({delay}) must be capped at max_delay ({max_delay})"
    
    # 2. For high attempt counts, delay should equal max_delay
    expected_uncapped = base_delay * (exponential_base ** high_attempt)
    if expected_uncapped > max_delay:
        assert delay == max_delay, \
            f"Delay should be exactly max_delay ({max_delay}) when exponential exceeds it"


@given(
    attempt=st.integers(min_value=0, max_value=5),
    base_delay=st.floats(min_value=0.5, max_value=5.0),
    exponential_base=st.floats(min_value=2.0, max_value=3.0)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_delay_calculation_deterministic(attempt, base_delay, exponential_base):
    """
    Property 25 (extended): For any given retry parameters,
    calculating the delay multiple times should produce consistent results
    (when jitter is disabled).
    
    **Validates: Requirements 6.1**
    
    This property verifies that the retry delay calculation is deterministic
    when jitter is disabled.
    """
    handler = RetryHandler(
        base_delay=base_delay,
        max_delay=1000.0,
        exponential_base=exponential_base,
        jitter=False
    )
    
    # Calculate delay multiple times
    delays = [handler.calculate_delay(attempt) for _ in range(5)]
    
    # Property assertions
    
    # 1. All delays should be identical (deterministic)
    assert len(set(delays)) == 1, \
        "Retry delay calculation should be deterministic when jitter is disabled"
    
    # 2. Delay should match expected formula
    expected_delay = min(base_delay * (exponential_base ** attempt), 1000.0)
    assert abs(delays[0] - expected_delay) < 0.001, \
        f"Delay should match formula: min({base_delay} * {exponential_base}^{attempt}, 1000.0)"


@given(
    attempt_sequence=st.lists(
        st.integers(min_value=0, max_value=5),
        min_size=2,
        max_size=6,
        unique=True
    ).map(sorted)  # Ensure sequence is sorted (increasing attempts)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_delay_sequence_monotonic_increase(attempt_sequence):
    """
    Property 25 (extended): For any sequence of increasing retry attempts,
    the calculated delays should form a monotonically increasing sequence
    (until max_delay is reached).
    
    **Validates: Requirements 6.1**
    
    This property verifies that retry delays increase consistently
    across a sequence of retries.
    """
    handler = RetryHandler(
        base_delay=1.0,
        max_delay=1000.0,
        exponential_base=2.0,
        jitter=False
    )
    
    # Calculate delays for the sequence
    delays = [handler.calculate_delay(attempt) for attempt in attempt_sequence]
    
    # Property assertions
    
    # 1. Delays should be monotonically increasing (or equal if capped)
    for i in range(1, len(delays)):
        assert delays[i] >= delays[i-1], \
            f"Delay sequence should be monotonically increasing: " \
            f"attempt {attempt_sequence[i-1]} = {delays[i-1]}s, " \
            f"attempt {attempt_sequence[i]} = {delays[i]}s"
    
    # 2. If not capped, delays should strictly increase
    if all(d < 1000.0 for d in delays):
        for i in range(1, len(delays)):
            assert delays[i] > delays[i-1], \
                "Delays should strictly increase when not capped at max_delay"


@given(
    args=st.tuples(st.integers(), st.integers()),
    kwargs=st.dictionaries(
        keys=st.sampled_from(['x', 'y', 'z']),
        values=st.integers(),
        min_size=0,
        max_size=3
    )
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_function_arguments_preserved(args, kwargs):
    """
    Property 25 (extended): For any function with arguments,
    the retry handler should preserve and pass through all arguments correctly.
    
    **Validates: Requirements 6.1**
    
    This property verifies that function arguments are correctly passed
    through the retry mechanism.
    """
    handler = RetryHandler(max_retries=2, base_delay=0.01, jitter=False)
    
    # Create a mock function that captures arguments
    def test_func(*func_args, **func_kwargs):
        return (func_args, func_kwargs)
    
    # Execute with retry
    result_args, result_kwargs = handler.execute_with_retry(
        test_func,
        (Exception,),
        *args,
        **kwargs
    )
    
    # Property assertions
    
    # 1. Arguments should be preserved
    assert result_args == args, "Positional arguments should be preserved"
    
    # 2. Keyword arguments should be preserved
    assert result_kwargs == kwargs, "Keyword arguments should be preserved"


@given(
    exception_type=st.sampled_from([
        ConnectionError,
        TimeoutError,
        OSError,
    ])
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_is_retryable_classification(exception_type):
    """
    Property 25 (extended): For any exception type in the retryable list,
    is_retryable should return True.
    
    **Validates: Requirements 6.1**
    
    This property verifies that the is_retryable method correctly
    classifies exceptions.
    """
    handler = RetryHandler()
    
    # Create an instance of the exception
    exc = exception_type("Test error")
    
    # Property assertions
    
    # 1. Exception should be classified as retryable
    # The RetryHandler uses ErrorClassifier internally which knows about retryable exceptions
    assert handler.is_retryable(exc), \
        f"{exception_type.__name__} should be classified as retryable"
    
    # 2. Non-retryable exceptions should not be retryable
    non_retryable_exc = ValueError("Invalid input")
    assert not handler.is_retryable(non_retryable_exc), \
        "ValueError should not be retryable"


@given(
    max_retries=st.integers(min_value=1, max_value=5),
    base_delay=st.floats(min_value=0.05, max_value=0.2)
)
@settings(max_examples=10, deadline=None)
@pytest.mark.property_test
def test_property_retry_timing_accuracy(max_retries, base_delay):
    """
    Property 25 (extended): For any retry sequence,
    the total execution time should approximately match the sum of delays.
    
    **Validates: Requirements 6.1**
    
    This property verifies that the retry handler actually waits
    for the calculated delays.
    """
    handler = RetryHandler(
        max_retries=max_retries,
        base_delay=base_delay,
        exponential_base=2.0,
        jitter=False
    )
    
    # Create a mock function that always fails
    mock_func = Mock(side_effect=ConnectionError("Failed"))
    
    # Calculate expected total delay
    expected_delay = sum(handler.calculate_delay(i) for i in range(max_retries))
    
    # Measure execution time
    start_time = time.time()
    with pytest.raises(ConnectionError):
        handler.execute_with_retry(
            mock_func,
            retryable_exceptions=(ConnectionError,)
        )
    elapsed_time = time.time() - start_time
    
    # Property assertions
    
    # 1. Elapsed time should be at least the expected delay
    assert elapsed_time >= expected_delay * 0.8, \
        f"Elapsed time ({elapsed_time:.3f}s) should be at least expected delay ({expected_delay:.3f}s)"
    
    # 2. Elapsed time should not be much more than expected (allow 100% overhead for system variance)
    assert elapsed_time <= expected_delay * 2.0, \
        f"Elapsed time ({elapsed_time:.3f}s) should not greatly exceed expected delay ({expected_delay:.3f}s)"


@given(
    max_retries=st.integers(min_value=1, max_value=3),
    base_delay=st.floats(min_value=0.5, max_value=2.0)
)
@settings(max_examples=10, deadline=None)
@pytest.mark.property_test
def test_property_retry_decorator_integration(max_retries, base_delay):
    """
    Property 25 (extended): For any function decorated with @retry,
    the retry behavior should match the RetryHandler behavior.
    
    **Validates: Requirements 6.1**
    
    This property verifies that the retry decorator provides
    the same retry functionality as the RetryHandler class.
    """
    call_count = 0
    
    @retry(
        max_retries=max_retries,
        base_delay=base_delay,
        exponential_base=2.0,
        jitter=False,
        retryable_exceptions=(ConnectionError,)
    )
    def test_func():
        nonlocal call_count
        call_count += 1
        if call_count <= max_retries:
            raise ConnectionError("Failed")
        return "success"
    
    # Execute decorated function
    result = test_func()
    
    # Property assertions
    
    # 1. Function should eventually succeed
    assert result == "success", "Decorated function should return success"
    
    # 2. Function should be called max_retries + 1 times
    expected_calls = max_retries + 1
    assert call_count == expected_calls, \
        f"Decorated function should be called {expected_calls} times"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property_test"])
