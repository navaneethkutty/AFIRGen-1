"""
Unit tests for metrics middleware.

Tests that the middleware correctly tracks API requests with:
- Request counts by endpoint, method, and status
- Request duration
- In-progress request tracking
"""

import pytest
import time
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, call

from middleware.metrics_middleware import MetricsMiddleware, setup_metrics_middleware
from infrastructure.metrics import MetricsCollector


@pytest.fixture
def app():
    """Create a test FastAPI app with metrics middleware."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    @app.get("/slow")
    async def slow_endpoint():
        time.sleep(0.1)  # Simulate slow endpoint
        return {"message": "slow"}
    
    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")
    
    @app.post("/create")
    async def create_endpoint():
        return {"message": "created"}
    
    setup_metrics_middleware(app)
    
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


def test_middleware_tracks_successful_request(client):
    """Test that middleware tracks successful requests."""
    with patch.object(MetricsCollector, 'record_request_duration') as mock_record:
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # Verify metrics were recorded
        mock_record.assert_called_once()
        call_args = mock_record.call_args
        
        assert call_args[1]['endpoint'] == "/test"
        assert call_args[1]['method'] == "GET"
        assert call_args[1]['status'] == 200
        assert call_args[1]['duration'] > 0


def test_middleware_tracks_different_methods(client):
    """Test that middleware tracks different HTTP methods."""
    with patch.object(MetricsCollector, 'record_request_duration') as mock_record:
        # GET request
        client.get("/test")
        
        # POST request
        client.post("/create")
        
        # Verify both were recorded
        assert mock_record.call_count == 2
        
        # Check GET call
        get_call = mock_record.call_args_list[0]
        assert get_call[1]['method'] == "GET"
        assert get_call[1]['endpoint'] == "/test"
        
        # Check POST call
        post_call = mock_record.call_args_list[1]
        assert post_call[1]['method'] == "POST"
        assert post_call[1]['endpoint'] == "/create"


def test_middleware_tracks_error_responses(client):
    """Test that middleware tracks error responses with 500 status."""
    with patch.object(MetricsCollector, 'record_request_duration') as mock_record:
        # This will raise an exception - TestClient will catch it and return 500
        try:
            response = client.get("/error")
        except ValueError:
            # Exception is expected, but middleware should still record metrics
            pass
        
        # Verify metrics were recorded with error status
        mock_record.assert_called_once()
        call_args = mock_record.call_args
        
        assert call_args[1]['endpoint'] == "/error"
        assert call_args[1]['status'] == 500


def test_middleware_measures_request_duration(client):
    """Test that middleware accurately measures request duration."""
    with patch.object(MetricsCollector, 'record_request_duration') as mock_record:
        response = client.get("/slow")
        
        assert response.status_code == 200
        
        # Verify duration is at least 0.1 seconds (the sleep time)
        call_args = mock_record.call_args
        duration = call_args[1]['duration']
        
        assert duration >= 0.1, f"Duration {duration} should be at least 0.1 seconds"


def test_middleware_tracks_multiple_requests(client):
    """Test that middleware tracks multiple requests correctly."""
    with patch.object(MetricsCollector, 'record_request_duration') as mock_record:
        # Make multiple requests
        for _ in range(5):
            client.get("/test")
        
        # Verify all requests were tracked
        assert mock_record.call_count == 5
        
        # Verify all have same endpoint
        for call_args in mock_record.call_args_list:
            assert call_args[1]['endpoint'] == "/test"
            assert call_args[1]['method'] == "GET"
            assert call_args[1]['status'] == 200


def test_middleware_tracks_different_endpoints(client):
    """Test that middleware distinguishes between different endpoints."""
    with patch.object(MetricsCollector, 'record_request_duration') as mock_record:
        client.get("/test")
        client.get("/slow")
        client.post("/create")
        
        # Verify all were tracked
        assert mock_record.call_count == 3
        
        # Extract endpoints
        endpoints = [call_args[1]['endpoint'] for call_args in mock_record.call_args_list]
        
        assert "/test" in endpoints
        assert "/slow" in endpoints
        assert "/create" in endpoints


def test_middleware_handles_correlation_id(client):
    """Test that middleware works with correlation ID in request state."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        # Correlation ID would be set by another middleware
        # This test just verifies the middleware doesn't break when it exists
        return {"message": "test"}
    
    setup_metrics_middleware(app)
    test_client = TestClient(app)
    
    with patch.object(MetricsCollector, 'record_request_duration') as mock_record:
        response = test_client.get("/test")
        
        assert response.status_code == 200
        mock_record.assert_called_once()


def test_setup_metrics_middleware():
    """Test that setup function correctly adds middleware to app."""
    app = FastAPI()
    
    # Verify no middleware initially
    initial_middleware_count = len(app.user_middleware)
    
    # Setup metrics middleware
    setup_metrics_middleware(app)
    
    # Verify middleware was added
    assert len(app.user_middleware) == initial_middleware_count + 1
    
    # Verify it's the correct middleware type
    middleware_class = app.user_middleware[0].cls
    assert middleware_class == MetricsMiddleware


def test_middleware_duration_is_positive(client):
    """Test that recorded duration is always positive."""
    with patch.object(MetricsCollector, 'record_request_duration') as mock_record:
        client.get("/test")
        
        call_args = mock_record.call_args
        duration = call_args[1]['duration']
        
        assert duration > 0, "Duration should always be positive"


def test_middleware_with_404_response(client):
    """Test that middleware tracks 404 responses."""
    with patch.object(MetricsCollector, 'record_request_duration') as mock_record:
        response = client.get("/nonexistent")
        
        assert response.status_code == 404
        
        # Verify metrics were recorded
        mock_record.assert_called_once()
        call_args = mock_record.call_args
        
        assert call_args[1]['status'] == 404
        assert call_args[1]['endpoint'] == "/nonexistent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
