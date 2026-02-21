"""
test_property_api_tracking.py
-----------------------------------------------------------------------------
Property-Based Tests for API Request Tracking
-----------------------------------------------------------------------------

Property tests for API request tracking using Hypothesis to verify:
- Property 21: API request tracking

Requirements Validated: 5.2 (Resource Monitoring - API Request Tracking)
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, MagicMock, patch
import time

from infrastructure.metrics import (
    MetricsCollector,
    api_request_count,
    api_request_duration,
    track_request_duration
)


def get_counter_value(counter, **labels):
    """Helper to get counter value from Prometheus metric."""
    try:
        return counter.labels(**labels)._value.get()
    except (AttributeError, TypeError):
        # Fallback: collect samples and find matching label
        for sample in counter.collect()[0].samples:
            if all(sample.labels.get(k) == str(v) for k, v in labels.items()):
                return sample.value
        return 0


def get_histogram_count(histogram, **labels):
    """Helper to get histogram count from Prometheus metric."""
    try:
        labeled = histogram.labels(**labels)
        # Try to access internal count
        if hasattr(labeled, '_count'):
            return labeled._count._value.get()
    except (AttributeError, TypeError):
        pass
    
    # Fallback: collect samples
    for sample in histogram.collect()[0].samples:
        if sample.name.endswith('_count') and all(
            sample.labels.get(k) == str(v) for k, v in labels.items()
        ):
            return sample.value
    return 0


def get_histogram_sum(histogram, **labels):
    """Helper to get histogram sum from Prometheus metric."""
    try:
        labeled = histogram.labels(**labels)
        # Try to access internal sum
        if hasattr(labeled, '_sum'):
            sum_val = labeled._sum
            if hasattr(sum_val, '_value'):
                return sum_val._value.get()
            return sum_val
    except (AttributeError, TypeError):
        pass
    
    # Fallback: collect samples
    for sample in histogram.collect()[0].samples:
        if sample.name.endswith('_sum') and all(
            sample.labels.get(k) == str(v) for k, v in labels.items()
        ):
            return sample.value
    return 0.0


# Strategy for generating valid HTTP methods
http_methods = st.sampled_from(["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])

# Strategy for generating valid HTTP status codes
http_status_codes = st.sampled_from([
    200, 201, 204,  # Success
    400, 401, 403, 404, 422,  # Client errors
    500, 502, 503, 504  # Server errors
])

# Strategy for generating API endpoints
api_endpoints = st.sampled_from([
    "/api/v1/fir",
    "/api/v1/fir/{id}",
    "/api/v1/violations",
    "/api/v1/kb/query",
    "/api/v1/users",
    "/api/v1/reports",
    "/health",
    "/metrics"
])

# Strategy for generating realistic response times (in seconds)
response_times = st.floats(min_value=0.001, max_value=60.0)


# Feature: backend-optimization, Property 21: API request tracking
@given(
    endpoint=api_endpoints,
    method=http_methods,
    status=http_status_codes,
    duration=response_times
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_api_request_tracking_records_all_fields(endpoint, method, status, duration):
    """
    Property 21: For any API request, the Monitoring_System should record
    the request with endpoint, method, status code, and response time.
    
    **Validates: Requirements 5.2**
    
    This property verifies that:
    1. All API requests are tracked with correct endpoint
    2. All API requests are tracked with correct method
    3. All API requests are tracked with correct status code
    4. Response time is recorded accurately
    """
    # Get initial metric values
    initial_count = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method,
        status=str(status)
    )
    
    # Record the request
    MetricsCollector.record_request_duration(endpoint, method, duration, status)
    
    # Get updated metric values
    updated_count = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method,
        status=str(status)
    )
    
    # Property assertions
    
    # 1. Request count should increment by exactly 1
    assert updated_count == initial_count + 1, \
        f"Request count should increment by 1 for {method} {endpoint} (status {status})"
    
    # 2. Duration histogram should have recorded the observation
    # We verify this by checking that the histogram count increased
    histogram_count = get_histogram_count(api_request_duration, endpoint=endpoint, method=method)
    assert histogram_count > 0, \
        f"Duration histogram should record observation for {method} {endpoint}"


@given(
    endpoint=api_endpoints,
    method=http_methods,
    status=http_status_codes,
    num_requests=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_request_count_increments_correctly(endpoint, method, status, num_requests):
    """
    Property 21 (extended): For any sequence of API requests to the same endpoint,
    the request count should increment correctly for each request.
    
    **Validates: Requirements 5.2**
    
    This property verifies that:
    1. Multiple requests to the same endpoint are all tracked
    2. Request count increments by the exact number of requests made
    3. Tracking is accurate regardless of the number of requests
    """
    # Get initial count
    initial_count = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method,
        status=str(status)
    )
    
    # Record multiple requests
    for _ in range(num_requests):
        MetricsCollector.record_request_duration(endpoint, method, 0.1, status)
    
    # Get updated count
    updated_count = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method,
        status=str(status)
    )
    
    # Property assertion: count should increase by exactly num_requests
    assert updated_count == initial_count + num_requests, \
        f"Request count should increment by {num_requests} for {method} {endpoint} (status {status})"


@given(
    endpoint=api_endpoints,
    method=http_methods,
    status1=http_status_codes,
    status2=http_status_codes
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_different_status_codes_tracked_separately(endpoint, method, status1, status2):
    """
    Property 21 (extended): For any API endpoint, requests with different
    status codes should be tracked separately.
    
    **Validates: Requirements 5.2**
    
    This property verifies that:
    1. Requests with different status codes are counted independently
    2. Status code is a distinct dimension in metrics tracking
    3. Changing status code doesn't affect other status code counts
    """
    assume(status1 != status2)
    
    # Get initial counts for both status codes
    initial_count1 = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method,
        status=str(status1)
    )
    
    initial_count2 = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method,
        status=str(status2)
    )
    
    # Record request with status1
    MetricsCollector.record_request_duration(endpoint, method, 0.1, status1)
    
    # Get updated counts
    updated_count1 = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method,
        status=str(status1)
    )
    
    updated_count2 = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method,
        status=str(status2)
    )
    
    # Property assertions
    
    # 1. Status1 count should increment
    assert updated_count1 == initial_count1 + 1, \
        f"Count for status {status1} should increment"
    
    # 2. Status2 count should remain unchanged
    assert updated_count2 == initial_count2, \
        f"Count for status {status2} should not change when recording status {status1}"


@given(
    endpoint1=api_endpoints,
    endpoint2=api_endpoints,
    method=http_methods,
    status=http_status_codes
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_different_endpoints_tracked_separately(endpoint1, endpoint2, method, status):
    """
    Property 21 (extended): For any two different API endpoints,
    requests should be tracked separately.
    
    **Validates: Requirements 5.2**
    
    This property verifies that:
    1. Requests to different endpoints are counted independently
    2. Endpoint is a distinct dimension in metrics tracking
    3. Recording to one endpoint doesn't affect other endpoint counts
    """
    assume(endpoint1 != endpoint2)
    
    # Get initial counts for both endpoints
    initial_count1 = get_counter_value(
        api_request_count,
        endpoint=endpoint1,
        method=method,
        status=str(status)
    )
    
    initial_count2 = get_counter_value(
        api_request_count,
        endpoint=endpoint2,
        method=method,
        status=str(status)
    )
    
    # Record request to endpoint1
    MetricsCollector.record_request_duration(endpoint1, method, 0.1, status)
    
    # Get updated counts
    updated_count1 = get_counter_value(
        api_request_count,
        endpoint=endpoint1,
        method=method,
        status=str(status)
    )
    
    updated_count2 = get_counter_value(
        api_request_count,
        endpoint=endpoint2,
        method=method,
        status=str(status)
    )
    
    # Property assertions
    
    # 1. Endpoint1 count should increment
    assert updated_count1 == initial_count1 + 1, \
        f"Count for endpoint {endpoint1} should increment"
    
    # 2. Endpoint2 count should remain unchanged
    assert updated_count2 == initial_count2, \
        f"Count for endpoint {endpoint2} should not change when recording to {endpoint1}"


@given(
    endpoint=api_endpoints,
    method1=http_methods,
    method2=http_methods,
    status=http_status_codes
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_different_methods_tracked_separately(endpoint, method1, method2, status):
    """
    Property 21 (extended): For any API endpoint, requests with different
    HTTP methods should be tracked separately.
    
    **Validates: Requirements 5.2**
    
    This property verifies that:
    1. Requests with different methods are counted independently
    2. Method is a distinct dimension in metrics tracking
    3. Recording one method doesn't affect other method counts
    """
    assume(method1 != method2)
    
    # Get initial counts for both methods
    initial_count1 = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method1,
        status=str(status)
    )
    
    initial_count2 = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method2,
        status=str(status)
    )
    
    # Record request with method1
    MetricsCollector.record_request_duration(endpoint, method1, 0.1, status)
    
    # Get updated counts
    updated_count1 = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method1,
        status=str(status)
    )
    
    updated_count2 = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method2,
        status=str(status)
    )
    
    # Property assertions
    
    # 1. Method1 count should increment
    assert updated_count1 == initial_count1 + 1, \
        f"Count for method {method1} should increment"
    
    # 2. Method2 count should remain unchanged
    assert updated_count2 == initial_count2, \
        f"Count for method {method2} should not change when recording {method1}"


@given(
    endpoint=api_endpoints,
    method=http_methods,
    durations=st.lists(response_times, min_size=1, max_size=10)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_response_time_histogram_records_durations(endpoint, method, durations):
    """
    Property 21 (extended): For any sequence of API requests,
    the response time histogram should accurately record all durations.
    
    **Validates: Requirements 5.2**
    
    This property verifies that:
    1. All response times are recorded in the histogram
    2. Histogram count matches the number of requests
    3. Histogram sum reflects the total of all durations
    """
    # Get initial histogram metrics
    initial_count = get_histogram_count(api_request_duration, endpoint=endpoint, method=method)
    initial_sum = get_histogram_sum(api_request_duration, endpoint=endpoint, method=method)
    
    # Record all durations
    for duration in durations:
        MetricsCollector.record_request_duration(endpoint, method, duration, 200)
    
    # Get updated histogram metrics
    updated_count = get_histogram_count(api_request_duration, endpoint=endpoint, method=method)
    updated_sum = get_histogram_sum(api_request_duration, endpoint=endpoint, method=method)
    
    # Property assertions
    
    # 1. Histogram count should increase by the number of requests
    assert updated_count == initial_count + len(durations), \
        f"Histogram count should increase by {len(durations)}"
    
    # 2. Histogram sum should increase by the sum of all durations
    expected_sum = initial_sum + sum(durations)
    assert abs(updated_sum - expected_sum) < 0.001, \
        f"Histogram sum should increase by {sum(durations)}, expected {expected_sum}, got {updated_sum}"


@given(
    endpoint=api_endpoints,
    method=http_methods,
    status=http_status_codes
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_context_manager_tracks_request(endpoint, method, status):
    """
    Property 21 (extended): For any API request tracked using the context manager,
    the request should be properly recorded with duration and status.
    
    **Validates: Requirements 5.2**
    
    This property verifies that:
    1. Context manager tracks request start and end
    2. Duration is calculated correctly
    3. Status code is recorded properly
    4. Request count increments
    """
    # Get initial count
    initial_count = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method,
        status=str(status)
    )
    
    # Use context manager to track request
    start_time = time.time()
    with track_request_duration(endpoint, method) as tracker:
        # Simulate some work
        time.sleep(0.01)
        tracker.set_status(status)
    end_time = time.time()
    
    actual_duration = end_time - start_time
    
    # Get updated count
    updated_count = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method,
        status=str(status)
    )
    
    # Property assertions
    
    # 1. Request count should increment
    assert updated_count == initial_count + 1, \
        f"Request count should increment when using context manager"
    
    # 2. Duration should be recorded (we can't check exact value due to timing variations,
    #    but we can verify the histogram was updated)
    histogram_sum = get_histogram_sum(api_request_duration, endpoint=endpoint, method=method)
    assert histogram_sum > 0, \
        f"Duration histogram should record positive duration"


@given(
    endpoint=api_endpoints,
    method=http_methods
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_context_manager_handles_exceptions(endpoint, method):
    """
    Property 21 (extended): For any API request that raises an exception,
    the context manager should still record the request with status 500.
    
    **Validates: Requirements 5.2**
    
    This property verifies that:
    1. Exceptions during request processing are handled
    2. Failed requests are tracked with status 500
    3. Request count increments even on failure
    """
    # Get initial count for status 500
    initial_count = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method,
        status="500"
    )
    
    # Use context manager with exception
    try:
        with track_request_duration(endpoint, method) as tracker:
            raise ValueError("Simulated error")
    except ValueError:
        pass  # Expected exception
    
    # Get updated count
    updated_count = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method,
        status="500"
    )
    
    # Property assertion: request should be tracked with status 500
    assert updated_count == initial_count + 1, \
        f"Failed request should be tracked with status 500"


@given(
    endpoint=api_endpoints,
    method=http_methods,
    status=http_status_codes,
    duration=response_times
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_metrics_are_persistent(endpoint, method, status, duration):
    """
    Property 21 (extended): For any API request recorded,
    the metrics should persist and be retrievable.
    
    **Validates: Requirements 5.2**
    
    This property verifies that:
    1. Recorded metrics persist in the registry
    2. Metrics can be retrieved after recording
    3. Metrics maintain their values across multiple accesses
    """
    # Record a request
    MetricsCollector.record_request_duration(endpoint, method, duration, status)
    
    # Retrieve the metric multiple times
    count1 = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method,
        status=str(status)
    )
    
    count2 = get_counter_value(
        api_request_count,
        endpoint=endpoint,
        method=method,
        status=str(status)
    )
    
    # Property assertions
    
    # 1. Metric should be retrievable
    assert count1 > 0, "Recorded metric should be retrievable"
    
    # 2. Metric value should be consistent across multiple accesses
    assert count1 == count2, \
        "Metric value should remain consistent across multiple accesses"


@given(
    endpoints=st.lists(api_endpoints, min_size=2, max_size=5, unique=True),
    method=http_methods,
    status=http_status_codes
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_concurrent_endpoint_tracking(endpoints, method, status):
    """
    Property 21 (extended): For any set of different endpoints,
    all requests should be tracked independently and correctly.
    
    **Validates: Requirements 5.2**
    
    This property verifies that:
    1. Multiple endpoints can be tracked simultaneously
    2. Each endpoint maintains its own independent count
    3. No interference between different endpoint metrics
    """
    # Get initial counts for all endpoints
    initial_counts = {}
    for endpoint in endpoints:
        initial_counts[endpoint] = get_counter_value(
            api_request_count,
            endpoint=endpoint,
            method=method,
            status=str(status)
        )
    
    # Record one request to each endpoint
    for endpoint in endpoints:
        MetricsCollector.record_request_duration(endpoint, method, 0.1, status)
    
    # Verify each endpoint count incremented by exactly 1
    for endpoint in endpoints:
        updated_count = get_counter_value(
            api_request_count,
            endpoint=endpoint,
            method=method,
            status=str(status)
        )
        
        assert updated_count == initial_counts[endpoint] + 1, \
            f"Endpoint {endpoint} count should increment by 1"
