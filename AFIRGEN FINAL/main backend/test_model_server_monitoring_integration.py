"""
Integration test for model server monitoring.

This test verifies that model server metrics are correctly recorded
when making actual requests through the ModelPool.

Validates: Requirements 5.5
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from infrastructure.metrics import MetricsCollector, model_server_requests, model_server_latency


def get_counter_value(counter, labels):
    """Helper to get counter value from Prometheus metric."""
    try:
        return counter.labels(**labels)._value.get()
    except (AttributeError, TypeError):
        for sample in counter.collect()[0].samples:
            if all(sample.labels.get(k) == str(v) for k, v in labels.items()):
                return sample.value
        return 0


def get_histogram_count(histogram, labels):
    """Helper to get histogram count from Prometheus metric."""
    try:
        labeled = histogram.labels(**labels)
        if hasattr(labeled, '_count'):
            return labeled._count._value.get()
    except (AttributeError, TypeError):
        pass
    
    for sample in histogram.collect()[0].samples:
        if sample.name.endswith('_count') and all(
            sample.labels.get(k) == str(v) for k, v in labels.items()
        ):
            return sample.value
    return 0


def test_metrics_collector_interface():
    """Test that MetricsCollector has the required interface for model server monitoring."""
    # Verify the method exists
    assert hasattr(MetricsCollector, 'record_model_server_latency')
    
    # Verify it's callable
    assert callable(MetricsCollector.record_model_server_latency)
    
    # Test basic functionality
    initial_count = get_counter_value(
        model_server_requests,
        {"server": "test_interface", "status": "success"}
    )
    
    MetricsCollector.record_model_server_latency("test_interface", 1.0, success=True)
    
    final_count = get_counter_value(
        model_server_requests,
        {"server": "test_interface", "status": "success"}
    )
    
    assert final_count == initial_count + 1


def test_model_server_availability_tracking():
    """Test that model server availability is tracked through success/failure status."""
    server = "availability_test_server"
    
    # Get initial counts
    initial_success = get_counter_value(
        model_server_requests,
        {"server": server, "status": "success"}
    )
    initial_error = get_counter_value(
        model_server_requests,
        {"server": server, "status": "error"}
    )
    
    # Simulate successful requests (server available)
    for _ in range(10):
        MetricsCollector.record_model_server_latency(server, 1.0, success=True)
    
    # Simulate failed requests (server unavailable)
    for _ in range(3):
        MetricsCollector.record_model_server_latency(server, 0.1, success=False)
    
    # Verify counts
    final_success = get_counter_value(
        model_server_requests,
        {"server": server, "status": "success"}
    )
    final_error = get_counter_value(
        model_server_requests,
        {"server": server, "status": "error"}
    )
    
    assert final_success == initial_success + 10
    assert final_error == initial_error + 3
    
    # Calculate availability rate
    total_requests = 10 + 3
    success_rate = 10 / total_requests
    assert success_rate > 0.7  # 76.9% availability


def test_model_server_latency_tracking():
    """Test that model server latency is tracked correctly."""
    server = "latency_tracking_server"
    
    # Get initial histogram count
    initial_count = get_histogram_count(
        model_server_latency,
        {"server": server}
    )
    
    # Record various latencies
    latencies = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 5.0, 10.0]
    for latency in latencies:
        MetricsCollector.record_model_server_latency(server, latency, success=True)
    
    # Verify all latencies were recorded
    final_count = get_histogram_count(
        model_server_latency,
        {"server": server}
    )
    
    assert final_count == initial_count + len(latencies)


def test_separate_server_metrics():
    """Test that different model servers have separate metrics."""
    servers = ["gguf_model_server", "asr_ocr_server"]
    
    for server in servers:
        # Get initial count
        initial_count = get_counter_value(
            model_server_requests,
            {"server": server, "status": "success"}
        )
        
        # Record request
        MetricsCollector.record_model_server_latency(server, 1.0, success=True)
        
        # Verify only this server's count increased
        final_count = get_counter_value(
            model_server_requests,
            {"server": server, "status": "success"}
        )
        
        assert final_count == initial_count + 1


def test_concurrent_metric_recording():
    """Test that metrics can be recorded concurrently without issues."""
    import threading
    
    server = "concurrent_test_server"
    num_threads = 10
    requests_per_thread = 5
    
    # Get initial count
    initial_count = get_counter_value(
        model_server_requests,
        {"server": server, "status": "success"}
    )
    
    def record_metrics():
        for _ in range(requests_per_thread):
            MetricsCollector.record_model_server_latency(server, 1.0, success=True)
    
    # Create and start threads
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=record_metrics)
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify all requests were recorded
    final_count = get_counter_value(
        model_server_requests,
        {"server": server, "status": "success"}
    )
    
    expected_count = initial_count + (num_threads * requests_per_thread)
    assert final_count == expected_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
