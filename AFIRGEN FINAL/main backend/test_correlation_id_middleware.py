"""
Unit tests for correlation ID middleware.

Tests the correlation ID generation, propagation, and context binding.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
import structlog

from middleware.correlation_id_middleware import (
    CorrelationIdMiddleware,
    setup_correlation_id_middleware
)


@pytest.fixture
def app():
    """Create a test FastAPI application."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint(request: Request):
        """Test endpoint that returns correlation ID from request state."""
        correlation_id = getattr(request.state, "correlation_id", None)
        return {"correlation_id": correlation_id}
    
    @app.get("/test-log")
    async def test_log_endpoint(request: Request):
        """Test endpoint that logs a message."""
        logger = structlog.get_logger()
        logger.info("test message")
        correlation_id = getattr(request.state, "correlation_id", None)
        return {"correlation_id": correlation_id}
    
    return app


@pytest.fixture
def client(app):
    """Create a test client with correlation ID middleware."""
    setup_correlation_id_middleware(app)
    return TestClient(app)


class TestCorrelationIdGeneration:
    """Test correlation ID generation."""
    
    def test_generates_correlation_id_when_not_provided(self, client):
        """Test that middleware generates a correlation ID when not provided in request."""
        response = client.get("/test")
        
        assert response.status_code == 200
        data = response.json()
        
        # Correlation ID should be generated
        assert data["correlation_id"] is not None
        assert len(data["correlation_id"]) > 0
        
        # Should be a valid UUID
        try:
            uuid.UUID(data["correlation_id"])
        except ValueError:
            pytest.fail("Generated correlation ID is not a valid UUID")
    
    def test_uses_existing_correlation_id_from_header(self, client):
        """Test that middleware uses correlation ID from request header if provided."""
        existing_id = "test-correlation-id-12345"
        
        response = client.get(
            "/test",
            headers={"X-Correlation-ID": existing_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should use the provided correlation ID
        assert data["correlation_id"] == existing_id
    
    def test_generates_unique_correlation_ids(self, client):
        """Test that each request gets a unique correlation ID."""
        response1 = client.get("/test")
        response2 = client.get("/test")
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Correlation IDs should be different
        assert data1["correlation_id"] != data2["correlation_id"]
    
    def test_correlation_id_is_uuid_format(self, client):
        """Test that generated correlation IDs are valid UUIDs."""
        response = client.get("/test")
        data = response.json()
        
        correlation_id = data["correlation_id"]
        
        # Should be a valid UUID4
        parsed_uuid = uuid.UUID(correlation_id)
        assert str(parsed_uuid) == correlation_id
        assert parsed_uuid.version == 4


class TestCorrelationIdPropagation:
    """Test correlation ID propagation through request context."""
    
    def test_correlation_id_added_to_request_state(self, client):
        """Test that correlation ID is added to request.state."""
        response = client.get("/test")
        
        assert response.status_code == 200
        data = response.json()
        
        # Correlation ID should be accessible from request.state
        assert data["correlation_id"] is not None
    
    def test_correlation_id_in_response_header(self, client):
        """Test that correlation ID is added to response headers."""
        response = client.get("/test")
        
        # Response should include X-Correlation-ID header
        assert "X-Correlation-ID" in response.headers
        assert response.headers["X-Correlation-ID"] is not None
        assert len(response.headers["X-Correlation-ID"]) > 0
    
    def test_response_header_matches_request_state(self, client):
        """Test that correlation ID in response header matches request state."""
        response = client.get("/test")
        data = response.json()
        
        # Correlation ID in response header should match request state
        assert response.headers["X-Correlation-ID"] == data["correlation_id"]
    
    def test_correlation_id_preserved_from_request_to_response(self, client):
        """Test that correlation ID from request header is preserved in response."""
        existing_id = "test-id-abc-123"
        
        response = client.get(
            "/test",
            headers={"X-Correlation-ID": existing_id}
        )
        
        # Response header should have the same correlation ID
        assert response.headers["X-Correlation-ID"] == existing_id


class TestStructlogContextBinding:
    """Test structlog context binding for correlation IDs."""
    
    def test_correlation_id_bound_to_structlog_context(self, client):
        """Test that correlation ID is bound to structlog context during request."""
        with patch('structlog.contextvars.bind_contextvars') as mock_bind:
            response = client.get("/test")
            
            # bind_contextvars should be called with correlation_id
            mock_bind.assert_called_once()
            call_kwargs = mock_bind.call_args[1]
            assert 'correlation_id' in call_kwargs
            assert call_kwargs['correlation_id'] is not None
    
    def test_structlog_context_cleared_after_request(self, client):
        """Test that structlog context is cleared after request completes."""
        with patch('structlog.contextvars.clear_contextvars') as mock_clear:
            response = client.get("/test")
            
            # clear_contextvars should be called after request
            mock_clear.assert_called_once()
    
    def test_structlog_context_cleared_on_error(self, app):
        """Test that structlog context is cleared even when request raises error."""
        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        
        setup_correlation_id_middleware(app)
        client = TestClient(app, raise_server_exceptions=False)
        
        with patch('structlog.contextvars.clear_contextvars') as mock_clear:
            response = client.get("/error")
            
            # clear_contextvars should still be called
            mock_clear.assert_called_once()


class TestMiddlewareSetup:
    """Test middleware setup function."""
    
    def test_setup_adds_middleware_to_app(self):
        """Test that setup function adds middleware to FastAPI app."""
        app = FastAPI()
        
        # Get initial middleware count
        initial_count = len(app.user_middleware)
        
        setup_correlation_id_middleware(app)
        
        # Middleware should be added
        assert len(app.user_middleware) > initial_count
    
    def test_middleware_can_be_added_multiple_times(self):
        """Test that middleware can be added to app (FastAPI handles duplicates)."""
        app = FastAPI()
        
        setup_correlation_id_middleware(app)
        setup_correlation_id_middleware(app)
        
        # Should not raise an error
        # FastAPI will handle duplicate middleware appropriately


class TestCorrelationIdMiddlewareIntegration:
    """Integration tests for correlation ID middleware."""
    
    def test_end_to_end_correlation_id_flow(self, client):
        """Test complete flow: generate ID, add to state, bind to context, add to response."""
        response = client.get("/test")
        
        assert response.status_code == 200
        data = response.json()
        
        # Correlation ID should be generated
        correlation_id = data["correlation_id"]
        assert correlation_id is not None
        
        # Should be in response header
        assert response.headers["X-Correlation-ID"] == correlation_id
        
        # Should be a valid UUID
        uuid.UUID(correlation_id)
    
    def test_correlation_id_with_existing_header(self, client):
        """Test complete flow when correlation ID is provided in request."""
        existing_id = str(uuid.uuid4())
        
        response = client.get(
            "/test",
            headers={"X-Correlation-ID": existing_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should use existing ID throughout
        assert data["correlation_id"] == existing_id
        assert response.headers["X-Correlation-ID"] == existing_id
    
    def test_multiple_requests_have_independent_correlation_ids(self, client):
        """Test that multiple concurrent requests have independent correlation IDs."""
        # Make multiple requests
        responses = [client.get("/test") for _ in range(5)]
        
        # Extract correlation IDs
        correlation_ids = [r.json()["correlation_id"] for r in responses]
        
        # All should be unique
        assert len(correlation_ids) == len(set(correlation_ids))


class TestCorrelationIdAccessibility:
    """Test that correlation ID is accessible in request handlers."""
    
    def test_correlation_id_accessible_in_handler(self, client):
        """Test that handlers can access correlation ID from request.state."""
        response = client.get("/test")
        data = response.json()
        
        # Handler should be able to access correlation ID
        assert data["correlation_id"] is not None
    
    def test_correlation_id_consistent_across_handler(self, app):
        """Test that correlation ID remains consistent throughout request handling."""
        correlation_ids = []
        
        @app.get("/multi-access")
        async def multi_access_endpoint(request: Request):
            # Access correlation ID multiple times
            id1 = request.state.correlation_id
            id2 = request.state.correlation_id
            id3 = request.state.correlation_id
            return {"ids": [id1, id2, id3]}
        
        setup_correlation_id_middleware(app)
        client = TestClient(app)
        
        response = client.get("/multi-access")
        data = response.json()
        
        # All accesses should return the same ID
        ids = data["ids"]
        assert len(set(ids)) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
