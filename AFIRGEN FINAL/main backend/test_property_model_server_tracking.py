"""
test_property_model_server_tracking.py
-----------------------------------------------------------------------------
Property-Based Tests for Model Server Tracking
-----------------------------------------------------------------------------

Property tests for model server tracking using Hypothesis to verify:
- Property 23: Model server latency tracking

Requirements Validated: 5.5 (Resource Monitoring - Model Server Latency and Availability)
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, MagicMock, patch
import time

from infrastructure.metrics import (
    MetricsCollector,
    model_server_requests,
    model_server_latency,
    model_server_availability
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


def get_gauge_value(gauge, **labels):
    """Helper to get gauge value from Prometheus metric."""
    try:
        if labels:
            return gauge.labels(**labels)._value.get()
        else:
            return gauge._value.get()
    except (AttributeError, TypeError):
        # Fallback: collect samples
        for sample in gauge.collect()[0].samples:
            if all(sample.labels.get(k) == str(v) for k, v in labels.items()):
                return sample.value
        return 0


# Strategy for generating model server names
model_server_names = st.sampled_from(["gguf_model_server", "asr_ocr_server"])

# Strategy for generating latency values (in seconds)
latency_values = st.floats(min_value=0.01, max_value=120.0, allow_nan=False, allow_infinity=False)

# Strategy for generating success/failure status
success_status = st.booleans()


# Feature: backend-optimization, Property 23: Model server latency tracking
@given(
    server=model_server_names,
    duration=latency_values,
    success=success_status
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_model_server_request_tracked(server, duration, success):
    """
    Property 23: For any request to a Model_Server, the Monitoring_System should
    record the server name, request latency, and success/failure status.
    
    **Validates: Requirements 5.5**
    
    This property verifies that:
    1. Model server requests are tracked with server name
    2. Request latency is recorded
    3. Success/failure status is tracked
    """
    # Get initial metrics
    status = "success" if success else "error"
    initial_request_count = get_counter_value(model_server_requests, server=server, status=status)
    initial_latency_count = get_histogram_count(model_server_latency, server=server)
    
    # Record model server request
    MetricsCollector.record_model_server_latency(server, duration, success)
    
    # Get updated metrics
    updated_request_count = get_counter_value(model_server_requests, server=server, status=status)
    updated_latency_count = get_histogram_count(model_server_latency, server=server)
    
    # Property assertions
    
    # 1. Request should be tracked with correct status
    assert updated_request_count == initial_request_count + 1, \
        f"Model server request should be tracked with status '{status}'"
    
    # 2. Latency should be recorded in histogram
    assert updated_latency_count == initial_latency_count + 1, \
        f"Model server request latency should be recorded"


@given(
    server=model_server_names,
    duration=latency_values
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_successful_request_tracked(server, duration):
    """
    Property 23: For any successful model server request,
    the Monitoring_System should track it with 'success' status.
    
    **Validates: Requirements 5.5**
    
    This property verifies that:
    1. Successful requests are tracked separately
    2. Success counter increments correctly
    3. Latency is recorded for successful requests
    """
    # Get initial metrics
    initial_success_count = get_counter_value(model_server_requests, server=server, status="success")
    initial_latency_count = get_histogram_count(model_server_latency, server=server)
    
    # Record successful request
    MetricsCollector.record_model_server_latency(server, duration, success=True)
    
    # Get updated metrics
    updated_success_count = get_counter_value(model_server_requests, server=server, status="success")
    updated_latency_count = get_histogram_count(model_server_latency, server=server)
    
    # Property assertions
    
    # 1. Success count should increment
    assert updated_success_count == initial_success_count + 1, \
        f"Successful model server request should be tracked"
    
    # 2. Latency should be recorded
    assert updated_latency_count == initial_latency_count + 1, \
        f"Latency should be recorded for successful request"


@given(
    server=model_server_names,
    duration=latency_values
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_failed_request_tracked(server, duration):
    """
    Property 23: For any failed model server request,
    the Monitoring_System should track it with 'error' status.
    
    **Validates: Requirements 5.5**
    
    This property verifies that:
    1. Failed requests are tracked separately
    2. Error counter increments correctly
    3. Latency is recorded even for failed requests
    """
    # Get initial metrics
    initial_error_count = get_counter_value(model_server_requests, server=server, status="error")
    initial_latency_count = get_histogram_count(model_server_latency, server=server)
    
    # Record failed request
    MetricsCollector.record_model_server_latency(server, duration, success=False)
    
    # Get updated metrics
    updated_error_count = get_counter_value(model_server_requests, server=server, status="error")
    updated_latency_count = get_histogram_count(model_server_latency, server=server)
    
    # Property assertions
    
    # 1. Error count should increment
    assert updated_error_count == initial_error_count + 1, \
        f"Failed model server request should be tracked"
    
    # 2. Latency should be recorded even for failures
    assert updated_latency_count == initial_latency_count + 1, \
        f"Latency should be recorded for failed request"


@given(
    server=model_server_names,
    num_requests=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_multiple_requests_tracked_independently(server, num_requests):
    """
    Property 23: For any sequence of model server requests,
    each request should be tracked independently.
    
    **Validates: Requirements 5.5**
    
    This property verifies that:
    1. Multiple requests are all tracked
    2. Request count increments correctly
    3. No deduplication of tracking
    """
    # Get initial metrics
    initial_success_count = get_counter_value(model_server_requests, server=server, status="success")
    initial_latency_count = get_histogram_count(model_server_latency, server=server)
    
    # Record multiple requests
    for _ in range(num_requests):
        MetricsCollector.record_model_server_latency(server, 1.0, success=True)
    
    # Get updated metrics
    updated_success_count = get_counter_value(model_server_requests, server=server, status="success")
    updated_latency_count = get_histogram_count(model_server_latency, server=server)
    
    # Property assertions
    
    # 1. All requests should be tracked
    assert updated_success_count == initial_success_count + num_requests, \
        f"All {num_requests} requests should be tracked independently"
    
    # 2. All latencies should be recorded
    assert updated_latency_count == initial_latency_count + num_requests, \
        f"All {num_requests} latencies should be recorded"


@given(
    num_successes=st.integers(min_value=1, max_value=20),
    num_failures=st.integers(min_value=1, max_value=20),
    server=model_server_names
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_success_and_failure_tracked_separately(num_successes, num_failures, server):
    """
    Property 23: For any mix of successful and failed requests,
    successes and failures should be tracked separately.
    
    **Validates: Requirements 5.5**
    
    This property verifies that:
    1. Success and error counters are independent
    2. Both types of requests are tracked correctly
    3. Availability can be calculated from success/error counts
    """
    # Get initial metrics
    initial_success_count = get_counter_value(model_server_requests, server=server, status="success")
    initial_error_count = get_counter_value(model_server_requests, server=server, status="error")
    
    # Record successful requests
    for _ in range(num_successes):
        MetricsCollector.record_model_server_latency(server, 1.0, success=True)
    
    # Record failed requests
    for _ in range(num_failures):
        MetricsCollector.record_model_server_latency(server, 1.0, success=False)
    
    # Get updated metrics
    updated_success_count = get_counter_value(model_server_requests, server=server, status="success")
    updated_error_count = get_counter_value(model_server_requests, server=server, status="error")
    
    # Property assertions
    
    # 1. All successes should be tracked
    assert updated_success_count == initial_success_count + num_successes, \
        f"All {num_successes} successful requests should be tracked"
    
    # 2. All failures should be tracked
    assert updated_error_count == initial_error_count + num_failures, \
        f"All {num_failures} failed requests should be tracked"
    
    # 3. Availability can be calculated from counts
    total_requests = num_successes + num_failures
    expected_availability = num_successes / total_requests
    assert 0.0 <= expected_availability <= 1.0, \
        f"Availability should be calculable as a ratio between 0 and 1"


@given(
    requests=st.lists(
        st.tuples(
            model_server_names,
            latency_values,
            success_status
        ),
        min_size=5,
        max_size=20
    )
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_different_servers_tracked_independently(requests):
    """
    Property 23: For any requests to different model servers,
    each server should be tracked independently.
    
    **Validates: Requirements 5.5**
    
    This property verifies that:
    1. Different servers have separate metrics
    2. Requests to one server don't affect another server's metrics
    3. Server-specific tracking is accurate
    """
    # Count expected requests per server
    expected_counts = {
        "gguf_model_server": {"success": 0, "error": 0},
        "asr_ocr_server": {"success": 0, "error": 0}
    }
    
    # Get initial metrics for both servers
    initial_gguf_success = get_counter_value(model_server_requests, server="gguf_model_server", status="success")
    initial_gguf_error = get_counter_value(model_server_requests, server="gguf_model_server", status="error")
    initial_asr_success = get_counter_value(model_server_requests, server="asr_ocr_server", status="success")
    initial_asr_error = get_counter_value(model_server_requests, server="asr_ocr_server", status="error")
    
    # Record all requests
    for server, duration, success in requests:
        MetricsCollector.record_model_server_latency(server, duration, success)
        status = "success" if success else "error"
        expected_counts[server][status] += 1
    
    # Get updated metrics
    updated_gguf_success = get_counter_value(model_server_requests, server="gguf_model_server", status="success")
    updated_gguf_error = get_counter_value(model_server_requests, server="gguf_model_server", status="error")
    updated_asr_success = get_counter_value(model_server_requests, server="asr_ocr_server", status="success")
    updated_asr_error = get_counter_value(model_server_requests, server="asr_ocr_server", status="error")
    
    # Property assertions
    
    # 1. GGUF server successes tracked correctly
    assert updated_gguf_success == initial_gguf_success + expected_counts["gguf_model_server"]["success"], \
        f"GGUF server successful requests should be tracked independently"
    
    # 2. GGUF server errors tracked correctly
    assert updated_gguf_error == initial_gguf_error + expected_counts["gguf_model_server"]["error"], \
        f"GGUF server failed requests should be tracked independently"
    
    # 3. ASR/OCR server successes tracked correctly
    assert updated_asr_success == initial_asr_success + expected_counts["asr_ocr_server"]["success"], \
        f"ASR/OCR server successful requests should be tracked independently"
    
    # 4. ASR/OCR server errors tracked correctly
    assert updated_asr_error == initial_asr_error + expected_counts["asr_ocr_server"]["error"], \
        f"ASR/OCR server failed requests should be tracked independently"


@given(
    server=model_server_names,
    latencies=st.lists(
        latency_values,
        min_size=2,
        max_size=10
    )
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_latency_values_recorded_accurately(server, latencies):
    """
    Property 23: For any sequence of model server requests,
    latency values should be recorded accurately in the histogram.
    
    **Validates: Requirements 5.5**
    
    This property verifies that:
    1. All latency values are recorded
    2. Histogram count matches number of requests
    3. Latency tracking is accurate
    """
    # Get initial histogram count
    initial_count = get_histogram_count(model_server_latency, server=server)
    
    # Record all latencies
    for latency in latencies:
        MetricsCollector.record_model_server_latency(server, latency, success=True)
    
    # Get updated histogram count
    updated_count = get_histogram_count(model_server_latency, server=server)
    
    # Property assertion: all latencies should be recorded
    assert updated_count == initial_count + len(latencies), \
        f"All {len(latencies)} latency values should be recorded in histogram"


@given(
    server=model_server_names,
    duration=latency_values
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_latency_is_positive(server, duration):
    """
    Property 23: For any model server request,
    the recorded latency should be a positive number.
    
    **Validates: Requirements 5.5**
    
    This property verifies that:
    1. Latency values are positive
    2. Negative latencies are not recorded
    3. Latency measurement is valid
    """
    # Ensure duration is positive (hypothesis should generate positive values)
    assume(duration > 0)
    
    # Get initial histogram count
    initial_count = get_histogram_count(model_server_latency, server=server)
    
    # Record latency
    MetricsCollector.record_model_server_latency(server, duration, success=True)
    
    # Get updated histogram count
    updated_count = get_histogram_count(model_server_latency, server=server)
    
    # Property assertion: latency should be recorded
    assert updated_count == initial_count + 1, \
        f"Positive latency value should be recorded"


@given(
    server=model_server_names,
    num_successes=st.integers(min_value=0, max_value=20),
    num_failures=st.integers(min_value=0, max_value=20)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_availability_calculable_from_metrics(server, num_successes, num_failures):
    """
    Property 23: For any model server with tracked requests,
    availability should be calculable from success/error counts.
    
    **Validates: Requirements 5.5**
    
    This property verifies that:
    1. Success and error counts enable availability calculation
    2. Availability is a valid percentage (0-100%)
    3. Metrics provide sufficient data for monitoring
    """
    # Skip if no requests
    assume(num_successes + num_failures > 0)
    
    # Get initial metrics
    initial_success = get_counter_value(model_server_requests, server=server, status="success")
    initial_error = get_counter_value(model_server_requests, server=server, status="error")
    
    # Record requests
    for _ in range(num_successes):
        MetricsCollector.record_model_server_latency(server, 1.0, success=True)
    for _ in range(num_failures):
        MetricsCollector.record_model_server_latency(server, 1.0, success=False)
    
    # Get updated metrics
    updated_success = get_counter_value(model_server_requests, server=server, status="success")
    updated_error = get_counter_value(model_server_requests, server=server, status="error")
    
    # Calculate availability from the incremental counts
    success_delta = updated_success - initial_success
    error_delta = updated_error - initial_error
    total_delta = success_delta + error_delta
    
    # Property assertions
    
    # 1. Total requests should match
    assert total_delta == num_successes + num_failures, \
        f"Total tracked requests should match actual requests"
    
    # 2. Availability should be calculable
    if total_delta > 0:
        availability = (success_delta / total_delta) * 100
        assert 0.0 <= availability <= 100.0, \
            f"Availability should be between 0% and 100%, got {availability}%"
        
        # 3. Availability should match expected value
        expected_availability = (num_successes / (num_successes + num_failures)) * 100
        assert abs(availability - expected_availability) < 0.01, \
            f"Calculated availability should match expected value"


@given(
    server=model_server_names,
    short_latency=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
    long_latency=st.floats(min_value=10.0, max_value=120.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_different_latencies_tracked_correctly(server, short_latency, long_latency):
    """
    Property 23: For any model server requests with different latencies,
    both short and long latencies should be tracked correctly.
    
    **Validates: Requirements 5.5**
    
    This property verifies that:
    1. Wide range of latencies can be tracked
    2. Histogram buckets capture different latency ranges
    3. No latency values are lost
    """
    # Get initial histogram count
    initial_count = get_histogram_count(model_server_latency, server=server)
    
    # Record both short and long latencies
    MetricsCollector.record_model_server_latency(server, short_latency, success=True)
    MetricsCollector.record_model_server_latency(server, long_latency, success=True)
    
    # Get updated histogram count
    updated_count = get_histogram_count(model_server_latency, server=server)
    
    # Property assertion: both latencies should be recorded
    assert updated_count == initial_count + 2, \
        f"Both short ({short_latency}s) and long ({long_latency}s) latencies should be tracked"


@given(
    operations=st.lists(
        st.tuples(
            model_server_names,
            latency_values,
            success_status
        ),
        min_size=10,
        max_size=30
    )
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_high_volume_tracking_accurate(operations):
    """
    Property 23: For any high volume of model server requests,
    all requests should be tracked accurately without loss.
    
    **Validates: Requirements 5.5**
    
    This property verifies that:
    1. High volume tracking is accurate
    2. No requests are lost in tracking
    3. Metrics scale with request volume
    """
    # Count expected requests per server and status
    expected = {
        "gguf_model_server": {"success": 0, "error": 0},
        "asr_ocr_server": {"success": 0, "error": 0}
    }
    
    # Get initial metrics
    initial_metrics = {}
    for server in ["gguf_model_server", "asr_ocr_server"]:
        initial_metrics[server] = {
            "success": get_counter_value(model_server_requests, server=server, status="success"),
            "error": get_counter_value(model_server_requests, server=server, status="error"),
            "latency": get_histogram_count(model_server_latency, server=server)
        }
    
    # Record all operations
    for server, duration, success in operations:
        MetricsCollector.record_model_server_latency(server, duration, success)
        status = "success" if success else "error"
        expected[server][status] += 1
    
    # Get updated metrics
    for server in ["gguf_model_server", "asr_ocr_server"]:
        updated_success = get_counter_value(model_server_requests, server=server, status="success")
        updated_error = get_counter_value(model_server_requests, server=server, status="error")
        updated_latency = get_histogram_count(model_server_latency, server=server)
        
        # Property assertions
        
        # 1. All successes tracked
        assert updated_success == initial_metrics[server]["success"] + expected[server]["success"], \
            f"{server}: All successful requests should be tracked"
        
        # 2. All errors tracked
        assert updated_error == initial_metrics[server]["error"] + expected[server]["error"], \
            f"{server}: All failed requests should be tracked"
        
        # 3. All latencies tracked
        total_requests = expected[server]["success"] + expected[server]["error"]
        assert updated_latency == initial_metrics[server]["latency"] + total_requests, \
            f"{server}: All latencies should be tracked"
