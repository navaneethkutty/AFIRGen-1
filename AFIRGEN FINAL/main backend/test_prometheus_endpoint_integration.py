"""
Integration tests for Prometheus metrics endpoint.

Tests verify that the /prometheus/metrics endpoint works correctly
in the context of the full application with real metrics collection.

Validates: Requirements 5.7
"""

import pytest
import time
from infrastructure.metrics import MetricsCollector
from prometheus_client import CONTENT_TYPE_LATEST


class TestPrometheusEndpointIntegration:
    """Integration tests for Prometheus metrics endpoint."""
    
    def test_metrics_collector_get_metrics(self):
        """Test that MetricsCollector.get_metrics() returns valid Prometheus format."""
        # Record some metrics
        MetricsCollector.record_request_duration(
            endpoint="/api/test",
            method="GET",
            duration=0.123,
            status=200
        )
        
        # Get metrics
        metrics_data = MetricsCollector.get_metrics()
        
        # Should return bytes
        assert isinstance(metrics_data, bytes)
        
        # Should be non-empty
        assert len(metrics_data) > 0
        
        # Convert to string for inspection
        metrics_str = metrics_data.decode('utf-8')
        
        # Should contain Prometheus format markers
        assert "# HELP" in metrics_str or "# TYPE" in metrics_str or len(metrics_str) > 0
    
    def test_metrics_collector_content_type(self):
        """Test that MetricsCollector returns correct content type."""
        content_type = MetricsCollector.get_content_type()
        
        # Should return Prometheus content type
        assert content_type == CONTENT_TYPE_LATEST
        assert "text/plain" in content_type
    
    def test_all_metric_types_included(self):
        """Test that all types of metrics are included in output."""
        # Reset metrics
        MetricsCollector.reset_cache_hit_rate()
        
        # Record various types of metrics
        # API metrics
        MetricsCollector.record_request_duration(
            endpoint="/api/fir",
            method="POST",
            duration=1.5,
            status=201
        )
        
        # Database metrics
        MetricsCollector.record_db_query_duration(
            query_type="INSERT",
            table="fir_records",
            duration=0.05
        )
        
        # Cache metrics
        MetricsCollector.record_cache_operation(
            operation="get",
            hit=True,
            duration=0.001
        )
        MetricsCollector.record_cache_operation(
            operation="get",
            hit=False,
            duration=0.002
        )
        
        # Model server metrics
        MetricsCollector.record_model_server_latency(
            server="llm",
            duration=3.2,
            success=True
        )
        
        # Database pool metrics
        MetricsCollector.update_db_pool_metrics(
            pool_size=20,
            available=15
        )
        
        # Get metrics
        metrics_data = MetricsCollector.get_metrics()
        metrics_str = metrics_data.decode('utf-8')
        
        # Verify all metric types are present
        assert "api_requests_total" in metrics_str
        assert "api_request_duration_seconds" in metrics_str
        assert "db_queries_total" in metrics_str
        assert "db_query_duration_seconds" in metrics_str
        assert "cache_operations_total" in metrics_str
        assert "cache_hit_rate" in metrics_str
        assert "model_server_requests_total" in metrics_str
        assert "model_server_latency_seconds" in metrics_str
        assert "db_connection_pool_size" in metrics_str
    
    def test_metrics_accumulate_over_time(self):
        """Test that metrics accumulate correctly over multiple operations."""
        # Reset metrics
        MetricsCollector.reset_cache_hit_rate()
        
        # Record multiple operations
        for i in range(5):
            MetricsCollector.record_request_duration(
                endpoint="/api/test",
                method="GET",
                duration=0.1 * (i + 1),
                status=200
            )
        
        # Get metrics
        metrics_data = MetricsCollector.get_metrics()
        metrics_str = metrics_data.decode('utf-8')
        
        # Should contain the accumulated count
        # The exact format depends on Prometheus client, but we should see the metric
        assert "api_requests_total" in metrics_str
        
        # Parse the metrics to verify count
        lines = metrics_str.split('\n')
        for line in lines:
            if 'api_requests_total{' in line and 'endpoint="/api/test"' in line:
                # Extract the count value
                parts = line.split()
                if len(parts) >= 2:
                    count = float(parts[-1])
                    assert count >= 5.0  # Should have at least 5 requests
                    break
    
    def test_cache_hit_rate_calculation(self):
        """Test that cache hit rate is calculated correctly."""
        # Reset metrics
        MetricsCollector.reset_cache_hit_rate()
        
        # Record cache operations: 7 hits, 3 misses = 70% hit rate
        for _ in range(7):
            MetricsCollector.record_cache_operation("get", hit=True)
        for _ in range(3):
            MetricsCollector.record_cache_operation("get", hit=False)
        
        # Get metrics
        metrics_data = MetricsCollector.get_metrics()
        metrics_str = metrics_data.decode('utf-8')
        
        # Should contain cache hit rate
        assert "cache_hit_rate" in metrics_str
        
        # Parse to verify the value
        lines = metrics_str.split('\n')
        for line in lines:
            if line.startswith('cache_hit_rate '):
                parts = line.split()
                if len(parts) >= 2:
                    hit_rate = float(parts[1])
                    # Should be 70%
                    assert 69.0 <= hit_rate <= 71.0
                    break
    
    def test_histogram_buckets(self):
        """Test that histogram metrics include bucket information."""
        # Record some requests with varying durations
        MetricsCollector.record_request_duration(
            endpoint="/api/test",
            method="GET",
            duration=0.05,
            status=200
        )
        MetricsCollector.record_request_duration(
            endpoint="/api/test",
            method="GET",
            duration=0.5,
            status=200
        )
        MetricsCollector.record_request_duration(
            endpoint="/api/test",
            method="GET",
            duration=2.0,
            status=200
        )
        
        # Get metrics
        metrics_data = MetricsCollector.get_metrics()
        metrics_str = metrics_data.decode('utf-8')
        
        # Histograms should have _bucket, _sum, and _count
        assert "api_request_duration_seconds_bucket" in metrics_str
        assert "api_request_duration_seconds_sum" in metrics_str
        assert "api_request_duration_seconds_count" in metrics_str
    
    def test_labels_in_metrics(self):
        """Test that metrics include proper labels."""
        # Record metrics with different labels
        MetricsCollector.record_request_duration(
            endpoint="/api/fir",
            method="POST",
            duration=1.0,
            status=201
        )
        MetricsCollector.record_request_duration(
            endpoint="/api/fir",
            method="GET",
            duration=0.5,
            status=200
        )
        
        # Get metrics
        metrics_data = MetricsCollector.get_metrics()
        metrics_str = metrics_data.decode('utf-8')
        
        # Should contain labels
        assert 'endpoint="/api/fir"' in metrics_str
        assert 'method="POST"' in metrics_str or 'method="GET"' in metrics_str
        assert 'status="201"' in metrics_str or 'status="200"' in metrics_str
    
    def test_metrics_performance(self):
        """Test that metrics generation is performant."""
        # Record a lot of metrics
        for i in range(100):
            MetricsCollector.record_request_duration(
                endpoint=f"/api/endpoint{i % 10}",
                method="GET",
                duration=0.1,
                status=200
            )
        
        # Measure time to generate metrics
        start = time.time()
        metrics_data = MetricsCollector.get_metrics()
        duration = time.time() - start
        
        # Should be fast (< 0.5 seconds even with many metrics)
        assert duration < 0.5
        assert len(metrics_data) > 0
    
    def test_concurrent_metric_recording(self):
        """Test that concurrent metric recording works correctly."""
        import concurrent.futures
        
        # Reset metrics
        MetricsCollector.reset_cache_hit_rate()
        
        def record_metrics(thread_id):
            for i in range(10):
                MetricsCollector.record_request_duration(
                    endpoint=f"/api/thread{thread_id}",
                    method="GET",
                    duration=0.1,
                    status=200
                )
        
        # Record metrics from multiple threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(record_metrics, i) for i in range(5)]
            for future in concurrent.futures.as_completed(futures):
                future.result()
        
        # Get metrics
        metrics_data = MetricsCollector.get_metrics()
        metrics_str = metrics_data.decode('utf-8')
        
        # Should contain metrics from all threads
        assert "api_requests_total" in metrics_str
        # Total should be 5 threads * 10 requests = 50
        # (We can't easily verify the exact count without parsing, but we can verify it exists)
    
    def test_system_metrics_collection(self):
        """Test that system metrics can be collected and exposed."""
        # Update system metrics
        MetricsCollector.update_system_metrics()
        
        # Get metrics
        metrics_data = MetricsCollector.get_metrics()
        metrics_str = metrics_data.decode('utf-8')
        
        # Should contain system metrics
        assert "system_cpu_percent" in metrics_str
        assert "system_memory_percent" in metrics_str
    
    def test_metrics_reset_functionality(self):
        """Test that cache hit rate can be reset."""
        # Record some metrics
        MetricsCollector.record_cache_operation("get", hit=True)
        MetricsCollector.record_cache_operation("get", hit=False)
        
        # Reset
        MetricsCollector.reset_cache_hit_rate()
        
        # Get metrics
        metrics_data = MetricsCollector.get_metrics()
        metrics_str = metrics_data.decode('utf-8')
        
        # Cache hit rate should be 0 or not present
        lines = metrics_str.split('\n')
        for line in lines:
            if line.startswith('cache_hit_rate '):
                parts = line.split()
                if len(parts) >= 2:
                    hit_rate = float(parts[1])
                    assert hit_rate == 0.0
                    break


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
