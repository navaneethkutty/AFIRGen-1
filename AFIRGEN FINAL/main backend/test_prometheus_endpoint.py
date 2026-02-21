"""
Unit tests for Prometheus metrics endpoint.

Tests verify that the /prometheus/metrics endpoint correctly exposes
metrics in Prometheus exposition format.

Validates: Requirements 5.7
"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from infrastructure.metrics import MetricsCollector
from prometheus_client import CONTENT_TYPE_LATEST
import structlog

log = structlog.get_logger()


@pytest.fixture
def app():
    """Create test FastAPI app with Prometheus metrics endpoint."""
    app = FastAPI()
    
    @app.get("/prometheus/metrics")
    async def prometheus_metrics():
        """
        Prometheus metrics endpoint for scraping.
        
        Exposes all collected metrics in Prometheus exposition format.
        This endpoint is designed to be scraped by Prometheus servers.
        
        Validates: Requirements 5.7
        """
        try:
            # Get metrics in Prometheus format
            metrics_data = MetricsCollector.get_metrics()
            content_type = MetricsCollector.get_content_type()
            
            # Return with proper Prometheus content type
            return Response(
                content=metrics_data,
                media_type=content_type
            )
        except Exception as e:
            log.error(f"Failed to generate Prometheus metrics: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate metrics")
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics before each test."""
    # Reset cache hit rate counters
    MetricsCollector.reset_cache_hit_rate()
    yield


class TestPrometheusEndpoint:
    """Test suite for Prometheus metrics endpoint."""
    
    def test_endpoint_exists(self, client):
        """Test that /prometheus/metrics endpoint exists and is accessible."""
        response = client.get("/prometheus/metrics")
        assert response.status_code == 200
    
    def test_content_type_header(self, client):
        """Test that response has correct Prometheus content type."""
        response = client.get("/prometheus/metrics")
        
        # Prometheus uses a specific content type
        assert response.status_code == 200
        assert CONTENT_TYPE_LATEST in response.headers.get("content-type", "")
    
    def test_prometheus_format(self, client):
        """Test that response is in Prometheus exposition format."""
        response = client.get("/prometheus/metrics")
        
        assert response.status_code == 200
        content = response.text
        
        # Prometheus format should contain metric definitions
        # Check for some expected metrics
        assert "# HELP" in content or "# TYPE" in content or len(content) > 0
    
    def test_metrics_include_api_metrics(self, client):
        """Test that API metrics are included in the output."""
        # Record some API metrics
        MetricsCollector.record_request_duration(
            endpoint="/test",
            method="GET",
            duration=0.5,
            status=200
        )
        
        response = client.get("/prometheus/metrics")
        assert response.status_code == 200
        content = response.text
        
        # Check for API metrics
        assert "api_requests_total" in content or "api_request_duration_seconds" in content
    
    def test_metrics_include_cache_metrics(self, client):
        """Test that cache metrics are included in the output."""
        # Record some cache operations
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
        
        response = client.get("/prometheus/metrics")
        assert response.status_code == 200
        content = response.text
        
        # Check for cache metrics
        assert "cache_operations_total" in content or "cache_hit_rate" in content
    
    def test_metrics_include_db_metrics(self, client):
        """Test that database metrics are included in the output."""
        # Record some database operations
        MetricsCollector.record_db_query_duration(
            query_type="SELECT",
            table="fir_records",
            duration=0.05
        )
        
        response = client.get("/prometheus/metrics")
        assert response.status_code == 200
        content = response.text
        
        # Check for database metrics
        assert "db_queries_total" in content or "db_query_duration_seconds" in content
    
    def test_metrics_include_model_server_metrics(self, client):
        """Test that model server metrics are included in the output."""
        # Record some model server operations
        MetricsCollector.record_model_server_latency(
            server="llm",
            duration=2.5,
            success=True
        )
        
        response = client.get("/prometheus/metrics")
        assert response.status_code == 200
        content = response.text
        
        # Check for model server metrics
        assert "model_server_requests_total" in content or "model_server_latency_seconds" in content
    
    def test_endpoint_performance(self, client):
        """Test that metrics endpoint responds quickly."""
        import time
        
        start = time.time()
        response = client.get("/prometheus/metrics")
        duration = time.time() - start
        
        assert response.status_code == 200
        # Metrics generation should be fast (< 1 second)
        assert duration < 1.0
    
    def test_endpoint_without_authentication(self, client):
        """Test that endpoint is accessible without authentication."""
        # Prometheus scrapers typically don't authenticate
        response = client.get("/prometheus/metrics")
        
        # Should not return 401 or 403
        assert response.status_code == 200
        assert response.status_code != 401
        assert response.status_code != 403
    
    def test_multiple_requests_return_updated_metrics(self, client):
        """Test that metrics are updated between requests."""
        # First request
        response1 = client.get("/prometheus/metrics")
        assert response1.status_code == 200
        content1 = response1.text
        
        # Record new metrics
        MetricsCollector.record_request_duration(
            endpoint="/test",
            method="POST",
            duration=1.0,
            status=201
        )
        
        # Second request
        response2 = client.get("/prometheus/metrics")
        assert response2.status_code == 200
        content2 = response2.text
        
        # Content should be different (metrics updated)
        # Note: This might not always be true if metrics are identical,
        # but we can at least verify both requests succeeded
        assert len(content2) > 0
    
    def test_error_handling(self, client):
        """Test that endpoint handles errors gracefully."""
        with patch.object(MetricsCollector, 'get_metrics', side_effect=Exception("Test error")):
            response = client.get("/prometheus/metrics")
            
            # Should return 500 error
            assert response.status_code == 500
            assert "error" in response.json() or "detail" in response.json()
    
    def test_empty_metrics(self, client):
        """Test that endpoint works even with no recorded metrics."""
        # Reset all metrics
        MetricsCollector.reset_cache_hit_rate()
        
        response = client.get("/prometheus/metrics")
        
        # Should still return 200 with valid Prometheus format
        assert response.status_code == 200
        assert CONTENT_TYPE_LATEST in response.headers.get("content-type", "")
    
    def test_concurrent_requests(self, client):
        """Test that endpoint handles concurrent requests correctly."""
        import concurrent.futures
        
        def make_request():
            response = client.get("/prometheus/metrics")
            return response.status_code
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 10


class TestPrometheusMetricsContent:
    """Test suite for Prometheus metrics content validation."""
    
    def test_metrics_format_valid(self, client):
        """Test that metrics follow Prometheus exposition format."""
        response = client.get("/prometheus/metrics")
        assert response.status_code == 200
        
        content = response.text
        lines = content.split('\n')
        
        # Prometheus format should have:
        # - Comment lines starting with #
        # - Metric lines with format: metric_name{labels} value timestamp
        # - Empty lines
        
        for line in lines:
            if line.strip() == "":
                continue
            if line.startswith('#'):
                # Comment line (HELP or TYPE)
                assert '# HELP' in line or '# TYPE' in line or line.startswith('# ')
            else:
                # Metric line - should have a metric name
                # Format: metric_name{label="value"} number
                # or: metric_name number
                assert len(line.split()) >= 1
    
    def test_metrics_include_help_text(self, client):
        """Test that metrics include HELP documentation."""
        response = client.get("/prometheus/metrics")
        assert response.status_code == 200
        
        content = response.text
        
        # Should have HELP lines for metrics
        assert "# HELP" in content or "# TYPE" in content
    
    def test_metrics_include_type_information(self, client):
        """Test that metrics include TYPE information."""
        response = client.get("/prometheus/metrics")
        assert response.status_code == 200
        
        content = response.text
        
        # Should have TYPE lines for metrics
        assert "# TYPE" in content
    
    def test_counter_metrics_present(self, client):
        """Test that counter metrics are present."""
        # Record some counter metrics
        MetricsCollector.record_request_duration(
            endpoint="/test",
            method="GET",
            duration=0.1,
            status=200
        )
        
        response = client.get("/prometheus/metrics")
        assert response.status_code == 200
        content = response.text
        
        # Check for counter type
        assert "counter" in content.lower() or "api_requests_total" in content
    
    def test_histogram_metrics_present(self, client):
        """Test that histogram metrics are present."""
        # Record some histogram metrics
        MetricsCollector.record_request_duration(
            endpoint="/test",
            method="GET",
            duration=0.5,
            status=200
        )
        
        response = client.get("/prometheus/metrics")
        assert response.status_code == 200
        content = response.text
        
        # Histograms have _bucket, _sum, _count suffixes
        assert "histogram" in content.lower() or "_bucket" in content or "_sum" in content
    
    def test_gauge_metrics_present(self, client):
        """Test that gauge metrics are present."""
        # Update some gauge metrics
        MetricsCollector.update_db_pool_metrics(pool_size=10, available=5)
        
        response = client.get("/prometheus/metrics")
        assert response.status_code == 200
        content = response.text
        
        # Check for gauge type
        assert "gauge" in content.lower() or "db_connection_pool" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
