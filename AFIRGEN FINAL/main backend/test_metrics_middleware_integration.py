"""
Integration test for metrics middleware with actual MetricsCollector.

Verifies that the middleware correctly integrates with Prometheus metrics.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.metrics_middleware import setup_metrics_middleware
from infrastructure.metrics import (
    MetricsCollector,
    api_request_count,
    api_request_duration,
    api_request_in_progress
)


@pytest.fixture
def app():
    """Create a test FastAPI app with metrics middleware."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    @app.post("/create")
    async def create_endpoint():
        return {"message": "created"}
    
    setup_metrics_middleware(app)
    
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


def test_metrics_integration_request_count(client):
    """Test that request count metrics are incremented."""
    # Get initial count
    initial_count = api_request_count.labels(
        endpoint="/test",
        method="GET",
        status=200
    )._value.get()
    
    # Make request
    response = client.get("/test")
    assert response.status_code == 200
    
    # Verify count increased
    final_count = api_request_count.labels(
        endpoint="/test",
        method="GET",
        status=200
    )._value.get()
    
    assert final_count > initial_count


def test_metrics_integration_duration_recorded(client):
    """Test that request duration is recorded."""
    # Get initial sample count
    initial_samples = api_request_duration.labels(
        endpoint="/test",
        method="GET"
    )._sum.get()
    
    # Make request
    response = client.get("/test")
    assert response.status_code == 200
    
    # Verify duration was recorded (sum should increase)
    final_samples = api_request_duration.labels(
        endpoint="/test",
        method="GET"
    )._sum.get()
    
    assert final_samples > initial_samples


def test_metrics_integration_different_status_codes(client):
    """Test that different status codes are tracked separately."""
    # Make successful request
    response = client.get("/test")
    assert response.status_code == 200
    
    # Make 404 request
    response = client.get("/nonexistent")
    assert response.status_code == 404
    
    # Verify both status codes were tracked
    count_200 = api_request_count.labels(
        endpoint="/test",
        method="GET",
        status=200
    )._value.get()
    
    count_404 = api_request_count.labels(
        endpoint="/nonexistent",
        method="GET",
        status=404
    )._value.get()
    
    assert count_200 > 0
    assert count_404 > 0


def test_metrics_integration_different_methods(client):
    """Test that different HTTP methods are tracked separately."""
    # Make GET request
    response = client.get("/test")
    assert response.status_code == 200
    
    # Make POST request
    response = client.post("/create")
    assert response.status_code == 200
    
    # Verify both methods were tracked
    get_count = api_request_count.labels(
        endpoint="/test",
        method="GET",
        status=200
    )._value.get()
    
    post_count = api_request_count.labels(
        endpoint="/create",
        method="POST",
        status=200
    )._value.get()
    
    assert get_count > 0
    assert post_count > 0


def test_metrics_collector_get_metrics(client):
    """Test that metrics can be exported in Prometheus format."""
    # Make some requests
    client.get("/test")
    client.post("/create")
    
    # Get metrics
    metrics_output = MetricsCollector.get_metrics()
    
    # Verify it's bytes
    assert isinstance(metrics_output, bytes)
    
    # Verify it contains our metrics
    metrics_str = metrics_output.decode('utf-8')
    assert 'api_requests_total' in metrics_str
    assert 'api_request_duration_seconds' in metrics_str


def test_metrics_content_type():
    """Test that metrics content type is correct."""
    content_type = MetricsCollector.get_content_type()
    
    # Should be Prometheus text format
    assert 'text/plain' in content_type


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
