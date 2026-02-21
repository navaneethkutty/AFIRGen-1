"""
Tests for model server monitoring metrics.

Validates: Requirements 5.5
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import time
import httpx
from infrastructure.metrics import MetricsCollector, model_server_requests, model_server_latency


def get_counter_value(counter, labels):
    """Helper to get counter value from Prometheus metric."""
    try:
        return counter.labels(**labels)._value.get()
    except (AttributeError, TypeError):
        # Fallback: collect samples and find matching label
        for sample in counter.collect()[0].samples:
            if all(sample.labels.get(k) == str(v) for k, v in labels.items()):
                return sample.value
        return 0


def get_histogram_count(histogram, labels):
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


class TestModelServerMonitoring:
    """Test model server monitoring metrics collection."""
    
    def test_record_model_server_latency_success(self):
        """Test recording successful model server request."""
        # Get initial counts
        initial_success_count = get_counter_value(
            model_server_requests,
            {"server": "gguf_model_server", "status": "success"}
        )
        initial_latency_count = get_histogram_count(
            model_server_latency,
            {"server": "gguf_model_server"}
        )
        
        # Record a successful request
        duration = 1.5
        MetricsCollector.record_model_server_latency("gguf_model_server", duration, success=True)
        
        # Verify success counter incremented
        success_count = get_counter_value(
            model_server_requests,
            {"server": "gguf_model_server", "status": "success"}
        )
        assert success_count == initial_success_count + 1
        
        # Verify latency histogram recorded
        latency_count = get_histogram_count(
            model_server_latency,
            {"server": "gguf_model_server"}
        )
        assert latency_count == initial_latency_count + 1
    
    def test_record_model_server_latency_failure(self):
        """Test recording failed model server request."""
        # Get initial counts
        initial_error_count = get_counter_value(
            model_server_requests,
            {"server": "asr_ocr_server", "status": "error"}
        )
        initial_latency_count = get_histogram_count(
            model_server_latency,
            {"server": "asr_ocr_server"}
        )
        
        # Record a failed request
        duration = 0.5
        MetricsCollector.record_model_server_latency("asr_ocr_server", duration, success=False)
        
        # Verify error counter incremented
        error_count = get_counter_value(
            model_server_requests,
            {"server": "asr_ocr_server", "status": "error"}
        )
        assert error_count == initial_error_count + 1
        
        # Verify latency histogram recorded
        latency_count = get_histogram_count(
            model_server_latency,
            {"server": "asr_ocr_server"}
        )
        assert latency_count == initial_latency_count + 1
    
    def test_record_multiple_model_server_requests(self):
        """Test recording multiple model server requests."""
        server = "test_server"
        
        # Get initial counts
        initial_success_count = get_counter_value(
            model_server_requests,
            {"server": server, "status": "success"}
        )
        initial_error_count = get_counter_value(
            model_server_requests,
            {"server": server, "status": "error"}
        )
        
        # Record multiple requests
        num_success = 5
        num_errors = 3
        
        for _ in range(num_success):
            MetricsCollector.record_model_server_latency(server, 1.0, success=True)
        
        for _ in range(num_errors):
            MetricsCollector.record_model_server_latency(server, 0.5, success=False)
        
        # Verify counts
        success_count = get_counter_value(
            model_server_requests,
            {"server": server, "status": "success"}
        )
        error_count = get_counter_value(
            model_server_requests,
            {"server": server, "status": "error"}
        )
        
        assert success_count == initial_success_count + num_success
        assert error_count == initial_error_count + num_errors
    
    def test_record_different_servers(self):
        """Test recording requests to different model servers."""
        servers = ["gguf_model_server", "asr_ocr_server", "custom_server"]
        
        for server in servers:
            # Get initial count
            initial_count = get_counter_value(
                model_server_requests,
                {"server": server, "status": "success"}
            )
            
            # Record request
            MetricsCollector.record_model_server_latency(server, 1.0, success=True)
            
            # Verify count incremented
            count = get_counter_value(
                model_server_requests,
                {"server": server, "status": "success"}
            )
            assert count == initial_count + 1
    
    def test_latency_values_recorded(self):
        """Test that different latency values are recorded correctly."""
        server = "latency_test_server"
        latencies = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        
        # Get initial count
        initial_count = get_histogram_count(
            model_server_latency,
            {"server": server}
        )
        
        # Record different latencies
        for latency in latencies:
            MetricsCollector.record_model_server_latency(server, latency, success=True)
        
        # Verify all latencies were recorded
        final_count = get_histogram_count(
            model_server_latency,
            {"server": server}
        )
        assert final_count == initial_count + len(latencies)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
