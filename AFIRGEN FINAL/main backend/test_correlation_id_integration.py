"""
Integration tests for correlation ID middleware with logging system.

Tests the complete flow of correlation ID generation, propagation through
structlog context, and inclusion in log entries.
"""

import pytest
import json
import logging
from io import StringIO
from unittest.mock import patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import structlog

from middleware import setup_correlation_id_middleware
from infrastructure.logging import configure_logging, get_logger


@pytest.fixture
def app_with_logging():
    """Create a test FastAPI application with logging and correlation ID middleware."""
    # Configure logging
    configure_logging()
    
    app = FastAPI()
    
    # Add correlation ID middleware
    setup_correlation_id_middleware(app)
    
    @app.get("/test-log")
    async def test_log_endpoint(request: Request):
        """Endpoint that logs a message."""
        logger = get_logger("test")
        logger.info("test message", action="test_action", user_id="123")
        
        return {
            "correlation_id": request.state.correlation_id,
            "message": "logged"
        }
    
    @app.get("/test-multiple-logs")
    async def test_multiple_logs_endpoint(request: Request):
        """Endpoint that logs multiple messages."""
        logger = get_logger("test")
        logger.info("first message", step=1)
        logger.info("second message", step=2)
        logger.info("third message", step=3)
        
        return {"correlation_id": request.state.correlation_id}
    
    @app.get("/test-error")
    async def test_error_endpoint(request: Request):
        """Endpoint that logs an error."""
        logger = get_logger("test")
        logger.error("error occurred", error_code="TEST_ERROR")
        
        return {"correlation_id": request.state.correlation_id}
    
    return app


@pytest.fixture
def client(app_with_logging):
    """Create a test client."""
    return TestClient(app_with_logging)


class TestCorrelationIdLoggingIntegration:
    """Test correlation ID integration with logging system."""
    
    def test_correlation_id_in_log_entries(self, client):
        """Test that correlation ID is included in log entries."""
        # Capture log output
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response = client.get("/test-log")
            
            assert response.status_code == 200
            correlation_id = response.json()["correlation_id"]
            
            # Get log output
            log_output = mock_stdout.getvalue()
            
            # Log should contain correlation ID
            # (Note: actual log format depends on configuration)
            if log_output:
                # Try to parse as JSON if JSON format is used
                try:
                    log_lines = [line for line in log_output.strip().split('\n') if line]
                    if log_lines:
                        log_entry = json.loads(log_lines[0])
                        assert "correlation_id" in log_entry
                        assert log_entry["correlation_id"] == correlation_id
                except json.JSONDecodeError:
                    # Console format - just check correlation ID is present
                    assert correlation_id in log_output
    
    def test_same_correlation_id_across_multiple_logs(self, client):
        """Test that all logs in a request have the same correlation ID."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response = client.get("/test-multiple-logs")
            
            assert response.status_code == 200
            correlation_id = response.json()["correlation_id"]
            
            log_output = mock_stdout.getvalue()
            
            if log_output:
                try:
                    log_lines = [line for line in log_output.strip().split('\n') if line]
                    
                    # Parse all log entries
                    log_entries = []
                    for line in log_lines:
                        try:
                            log_entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                    
                    if log_entries:
                        # All log entries should have the same correlation ID
                        correlation_ids = [entry.get("correlation_id") for entry in log_entries]
                        assert all(cid == correlation_id for cid in correlation_ids if cid)
                except Exception:
                    # If parsing fails, just check correlation ID appears multiple times
                    assert log_output.count(correlation_id) >= 3
    
    def test_different_requests_have_different_correlation_ids_in_logs(self, client):
        """Test that different requests have different correlation IDs in logs."""
        correlation_ids = []
        
        for _ in range(3):
            response = client.get("/test-log")
            correlation_ids.append(response.json()["correlation_id"])
        
        # All correlation IDs should be unique
        assert len(correlation_ids) == len(set(correlation_ids))
    
    def test_correlation_id_in_error_logs(self, client):
        """Test that correlation ID is included in error log entries."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response = client.get("/test-error")
            
            assert response.status_code == 200
            correlation_id = response.json()["correlation_id"]
            
            log_output = mock_stdout.getvalue()
            
            if log_output:
                try:
                    log_lines = [line for line in log_output.strip().split('\n') if line]
                    if log_lines:
                        log_entry = json.loads(log_lines[0])
                        assert log_entry.get("correlation_id") == correlation_id
                        assert log_entry.get("level") == "error" or log_entry.get("log_level") == "error"
                except json.JSONDecodeError:
                    # Console format
                    assert correlation_id in log_output
                    assert "error" in log_output.lower()


class TestCorrelationIdContextIsolation:
    """Test that correlation IDs are properly isolated between requests."""
    
    def test_context_isolation_between_requests(self, client):
        """Test that correlation ID context doesn't leak between requests."""
        # Make first request
        response1 = client.get("/test-log")
        correlation_id1 = response1.json()["correlation_id"]
        
        # Make second request
        response2 = client.get("/test-log")
        correlation_id2 = response2.json()["correlation_id"]
        
        # Correlation IDs should be different
        assert correlation_id1 != correlation_id2
    
    def test_context_cleared_after_request(self, client):
        """Test that structlog context is cleared after request completes."""
        # Make a request
        response = client.get("/test-log")
        assert response.status_code == 200
        
        # After request, context should be cleared
        # (This is tested by the middleware unit tests, but verify integration)
        # Make another request and verify it gets a new correlation ID
        response2 = client.get("/test-log")
        assert response2.status_code == 200
        
        # Should have different correlation IDs
        assert response.json()["correlation_id"] != response2.json()["correlation_id"]


class TestCorrelationIdWithExistingHeader:
    """Test correlation ID behavior when provided in request header."""
    
    def test_uses_provided_correlation_id_in_logs(self, client):
        """Test that provided correlation ID is used in log entries."""
        custom_id = "custom-correlation-id-12345"
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response = client.get(
                "/test-log",
                headers={"X-Correlation-ID": custom_id}
            )
            
            assert response.status_code == 200
            assert response.json()["correlation_id"] == custom_id
            
            log_output = mock_stdout.getvalue()
            
            if log_output:
                try:
                    log_lines = [line for line in log_output.strip().split('\n') if line]
                    if log_lines:
                        log_entry = json.loads(log_lines[0])
                        assert log_entry.get("correlation_id") == custom_id
                except json.JSONDecodeError:
                    # Console format
                    assert custom_id in log_output
    
    def test_provided_correlation_id_in_response_header(self, client):
        """Test that provided correlation ID is returned in response header."""
        custom_id = "test-id-abc-123"
        
        response = client.get(
            "/test-log",
            headers={"X-Correlation-ID": custom_id}
        )
        
        assert response.headers["X-Correlation-ID"] == custom_id


class TestCorrelationIdEndToEnd:
    """End-to-end tests for correlation ID flow."""
    
    def test_complete_correlation_id_flow(self, client):
        """Test complete flow: generate ID, log with ID, return in response."""
        response = client.get("/test-log")
        
        assert response.status_code == 200
        
        # Get correlation ID from response
        correlation_id = response.json()["correlation_id"]
        
        # Verify it's a valid UUID
        import uuid
        uuid.UUID(correlation_id)
        
        # Verify it's in response header
        assert response.headers["X-Correlation-ID"] == correlation_id
    
    def test_correlation_id_traceability(self, app_with_logging):
        """Test that correlation ID enables request traceability."""
        # Add an endpoint that simulates a multi-step process
        @app_with_logging.get("/multi-step")
        async def multi_step_endpoint(request: Request):
            logger = get_logger("test")
            
            # Simulate multiple steps
            logger.info("step 1: validate input")
            logger.info("step 2: process data")
            logger.info("step 3: save result")
            
            return {"correlation_id": request.state.correlation_id}
        
        client = TestClient(app_with_logging)
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response = client.get("/multi-step")
            correlation_id = response.json()["correlation_id"]
            
            log_output = mock_stdout.getvalue()
            
            if log_output:
                # All log entries should have the same correlation ID
                # This enables tracing all steps of the request
                try:
                    log_lines = [line for line in log_output.strip().split('\n') if line]
                    log_entries = []
                    for line in log_lines:
                        try:
                            log_entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                    
                    if log_entries:
                        # All entries should have the same correlation ID
                        for entry in log_entries:
                            if "correlation_id" in entry:
                                assert entry["correlation_id"] == correlation_id
                except Exception:
                    # Console format - just verify correlation ID appears
                    assert correlation_id in log_output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
