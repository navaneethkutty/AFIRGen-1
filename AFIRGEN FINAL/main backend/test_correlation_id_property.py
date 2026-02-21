"""
Property-based tests for correlation ID middleware.

Tests universal properties of correlation ID generation and propagation
using Hypothesis.

Feature: backend-optimization
Property 31: Unique correlation ID generation
Property 32: Correlation ID propagation
Validates: Requirements 7.1, 7.2

The correlation ID system should:
1. Generate unique correlation IDs for each request
2. Propagate correlation IDs through all operations and logs
"""

import pytest
import uuid
from unittest.mock import Mock, patch, call
from hypothesis import given, strategies as st, settings, assume
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import structlog

from middleware.correlation_id_middleware import (
    CorrelationIdMiddleware,
    setup_correlation_id_middleware
)


# Strategy for generating valid correlation ID strings (ASCII only for HTTP headers)
correlation_id_strings = st.text(
    min_size=10,
    max_size=100,
    alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
)

# Strategy for generating endpoint paths (ASCII only)
endpoint_paths = st.text(
    min_size=1,
    max_size=50,
    alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
).map(lambda s: f"/{s.strip('/')}" if s.strip('/') else "/test")


def create_test_app():
    """Create a test FastAPI application."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint(request: Request):
        """Test endpoint that returns correlation ID."""
        correlation_id = getattr(request.state, "correlation_id", None)
        return {"correlation_id": correlation_id}
    
    @app.get("/log-test")
    async def log_test_endpoint(request: Request):
        """Test endpoint that logs messages."""
        logger = structlog.get_logger()
        logger.info("test message 1")
        logger.info("test message 2")
        logger.info("test message 3")
        correlation_id = getattr(request.state, "correlation_id", None)
        return {"correlation_id": correlation_id}
    
    setup_correlation_id_middleware(app)
    return app


def create_test_client():
    """Create a test client."""
    return TestClient(create_test_app())


# Feature: backend-optimization, Property 31: Unique correlation ID generation
@given(
    num_requests=st.integers(min_value=2, max_value=20)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_31_unique_correlation_ids_generated(num_requests):
    """
    Property 31.1: Each request generates a unique correlation ID.
    
    For any number of concurrent or sequential requests without provided
    correlation IDs, the system should generate unique correlation IDs
    for each request.
    
    **Validates: Requirements 7.1**
    """
    client = create_test_client()
    
    # Make multiple requests
    responses = [client.get("/test") for _ in range(num_requests)]
    
    # Extract correlation IDs
    correlation_ids = [r.json()["correlation_id"] for r in responses]
    
    # Verify all are non-null
    assert all(cid is not None for cid in correlation_ids), \
        "All correlation IDs should be generated"
    
    # Verify all are unique
    unique_ids = set(correlation_ids)
    assert len(unique_ids) == num_requests, \
        f"Expected {num_requests} unique IDs, got {len(unique_ids)}"


# Feature: backend-optimization, Property 31: Unique correlation ID generation
@given(
    num_requests=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_31_generated_ids_are_valid_uuids(num_requests):
    """
    Property 31.2: Generated correlation IDs are valid UUIDs.
    
    For any request without a provided correlation ID, the generated
    correlation ID should be a valid UUID4 format.
    
    **Validates: Requirements 7.1**
    """
    client = create_test_client()
    
    # Make multiple requests
    responses = [client.get("/test") for _ in range(num_requests)]
    
    # Extract and validate correlation IDs
    for response in responses:
        correlation_id = response.json()["correlation_id"]
        
        # Should be parseable as UUID
        try:
            parsed_uuid = uuid.UUID(correlation_id)
            # Should be UUID version 4
            assert parsed_uuid.version == 4, \
                f"Expected UUID4, got version {parsed_uuid.version}"
        except (ValueError, AttributeError) as e:
            pytest.fail(f"Correlation ID '{correlation_id}' is not a valid UUID: {e}")


# Feature: backend-optimization, Property 31: Unique correlation ID generation
@given(
    provided_id=correlation_id_strings
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_31_uses_provided_correlation_id(provided_id):
    """
    Property 31.3: System uses provided correlation ID from header.
    
    For any request with a correlation ID in the X-Correlation-ID header,
    the system should use that ID instead of generating a new one.
    
    **Validates: Requirements 7.1**
    """
    # Filter out empty strings
    assume(len(provided_id.strip()) > 0)
    
    client = create_test_client()
    
    # Make request with provided correlation ID
    response = client.get(
        "/test",
        headers={"X-Correlation-ID": provided_id}
    )
    
    # Should use the provided ID
    returned_id = response.json()["correlation_id"]
    assert returned_id == provided_id, \
        f"Expected provided ID '{provided_id}', got '{returned_id}'"


# Feature: backend-optimization, Property 31: Unique correlation ID generation
@given(
    num_requests=st.integers(min_value=2, max_value=15),
    provided_ids=st.lists(
        correlation_id_strings,
        min_size=2,
        max_size=15,
        unique=True
    )
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_31_different_provided_ids_remain_different(num_requests, provided_ids):
    """
    Property 31.4: Different provided correlation IDs remain distinct.
    
    For any set of requests with different provided correlation IDs,
    each request should maintain its own unique correlation ID.
    
    **Validates: Requirements 7.1**
    """
    # Ensure we have enough IDs
    assume(len(provided_ids) >= num_requests)
    
    # Filter out empty IDs
    provided_ids = [pid for pid in provided_ids if len(pid.strip()) > 0]
    assume(len(provided_ids) >= num_requests)
    
    # Take only the number we need
    provided_ids = provided_ids[:num_requests]
    
    client = create_test_client()
    
    # Make requests with different provided IDs
    responses = [
        client.get("/test", headers={"X-Correlation-ID": pid})
        for pid in provided_ids
    ]
    
    # Extract returned correlation IDs
    returned_ids = [r.json()["correlation_id"] for r in responses]
    
    # Should match the provided IDs
    assert returned_ids == provided_ids, \
        "Returned IDs should match provided IDs in order"
    
    # Should all be unique
    assert len(set(returned_ids)) == num_requests, \
        "All correlation IDs should remain unique"


# Feature: backend-optimization, Property 31: Unique correlation ID generation
@given(
    num_requests=st.integers(min_value=2, max_value=20)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_31_correlation_ids_in_response_headers(num_requests):
    """
    Property 31.5: Correlation IDs are included in response headers.
    
    For any request, the correlation ID should be included in the
    X-Correlation-ID response header.
    
    **Validates: Requirements 7.1**
    """
    client = create_test_client()
    
    # Make multiple requests
    responses = [client.get("/test") for _ in range(num_requests)]
    
    # Extract correlation IDs from response headers
    header_ids = [r.headers.get("X-Correlation-ID") for r in responses]
    
    # All should have correlation ID header
    assert all(hid is not None for hid in header_ids), \
        "All responses should have X-Correlation-ID header"
    
    # Should match the IDs in response body
    body_ids = [r.json()["correlation_id"] for r in responses]
    assert header_ids == body_ids, \
        "Header IDs should match body IDs"
    
    # All should be unique
    assert len(set(header_ids)) == num_requests, \
        "All correlation IDs in headers should be unique"


# Feature: backend-optimization, Property 32: Correlation ID propagation
@given(
    correlation_id=correlation_id_strings
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_32_correlation_id_bound_to_structlog_context(correlation_id):
    """
    Property 32.1: Correlation ID is bound to structlog context.
    
    For any request with a correlation ID, the ID should be bound to the
    structlog context so it's automatically included in all log entries.
    
    **Validates: Requirements 7.2**
    """
    # Filter out empty strings
    assume(len(correlation_id.strip()) > 0)
    
    client = create_test_client()
    
    with patch('structlog.contextvars.bind_contextvars') as mock_bind:
        # Make request with correlation ID
        response = client.get(
            "/test",
            headers={"X-Correlation-ID": correlation_id}
        )
        
        # Verify bind_contextvars was called with the correlation ID
        mock_bind.assert_called_once()
        call_kwargs = mock_bind.call_args[1]
        assert 'correlation_id' in call_kwargs, \
            "bind_contextvars should be called with correlation_id"
        assert call_kwargs['correlation_id'] == correlation_id, \
            f"Expected correlation_id '{correlation_id}', got '{call_kwargs['correlation_id']}'"


# Feature: backend-optimization, Property 32: Correlation ID propagation
@given(
    num_requests=st.integers(min_value=1, max_value=15)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_32_structlog_context_cleared_after_each_request(num_requests):
    """
    Property 32.2: Structlog context is cleared after each request.
    
    For any request, the structlog context should be cleared after the
    request completes to prevent context leakage between requests.
    
    **Validates: Requirements 7.2**
    """
    client = create_test_client()
    
    with patch('structlog.contextvars.clear_contextvars') as mock_clear:
        # Make multiple requests
        for _ in range(num_requests):
            response = client.get("/test")
            assert response.status_code == 200
        
        # clear_contextvars should be called once per request
        assert mock_clear.call_count == num_requests, \
            f"Expected {num_requests} clear calls, got {mock_clear.call_count}"


# Feature: backend-optimization, Property 32: Correlation ID propagation
@given(
    correlation_id=correlation_id_strings
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_32_correlation_id_accessible_in_request_state(correlation_id):
    """
    Property 32.3: Correlation ID is accessible in request.state.
    
    For any request, the correlation ID should be stored in request.state
    and accessible to all request handlers and middleware.
    
    **Validates: Requirements 7.2**
    """
    # Filter out empty strings
    assume(len(correlation_id.strip()) > 0)
    
    client = create_test_client()
    
    # Make request with correlation ID
    response = client.get(
        "/test",
        headers={"X-Correlation-ID": correlation_id}
    )
    
    # Handler should have access to correlation ID via request.state
    returned_id = response.json()["correlation_id"]
    assert returned_id == correlation_id, \
        f"Handler should access correlation ID '{correlation_id}' from request.state"


# Feature: backend-optimization, Property 32: Correlation ID propagation
@given(
    num_requests=st.integers(min_value=2, max_value=15)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_32_correlation_id_propagates_through_request_lifecycle(num_requests):
    """
    Property 32.4: Correlation ID propagates through entire request lifecycle.
    
    For any request, the same correlation ID should be:
    1. Generated or extracted from header
    2. Stored in request.state
    3. Bound to structlog context
    4. Returned in response header
    
    **Validates: Requirements 7.2**
    """
    client = create_test_client()
    
    # Make multiple requests
    for _ in range(num_requests):
        response = client.get("/test")
        
        # Get correlation ID from response body (from request.state)
        body_id = response.json()["correlation_id"]
        
        # Get correlation ID from response header
        header_id = response.headers.get("X-Correlation-ID")
        
        # Both should exist and match
        assert body_id is not None, "Correlation ID should be in request.state"
        assert header_id is not None, "Correlation ID should be in response header"
        assert body_id == header_id, \
            f"Correlation ID should be consistent: body={body_id}, header={header_id}"


# Feature: backend-optimization, Property 32: Correlation ID propagation
@given(
    provided_ids=st.lists(
        correlation_id_strings,
        min_size=2,
        max_size=15,
        unique=True
    )
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_32_no_correlation_id_leakage_between_requests(provided_ids):
    """
    Property 32.5: No correlation ID leakage between requests.
    
    For any sequence of requests with different correlation IDs,
    each request should maintain its own correlation ID without
    interference from other requests.
    
    **Validates: Requirements 7.2**
    """
    # Filter out empty IDs
    provided_ids = [pid for pid in provided_ids if len(pid.strip()) > 0]
    assume(len(provided_ids) >= 2)
    
    client = create_test_client()
    
    # Make requests with different correlation IDs
    for provided_id in provided_ids:
        response = client.get(
            "/test",
            headers={"X-Correlation-ID": provided_id}
        )
        
        # Each request should have its own correlation ID
        returned_id = response.json()["correlation_id"]
        assert returned_id == provided_id, \
            f"Request should maintain its own correlation ID '{provided_id}', got '{returned_id}'"
        
        # Response header should also match
        header_id = response.headers.get("X-Correlation-ID")
        assert header_id == provided_id, \
            f"Response header should have correlation ID '{provided_id}', got '{header_id}'"


# Feature: backend-optimization, Property 32: Correlation ID propagation
@given(
    correlation_id=correlation_id_strings
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_32_correlation_id_propagates_to_all_operations(correlation_id):
    """
    Property 32.6: Correlation ID propagates to all operations in request.
    
    For any request, the correlation ID should be available throughout
    the entire request processing, including multiple operations.
    
    **Validates: Requirements 7.2**
    """
    # Filter out empty strings
    assume(len(correlation_id.strip()) > 0)
    
    # Create an app with multiple operations
    app = FastAPI()
    
    @app.get("/multi-op")
    async def multi_operation_endpoint(request: Request):
        """Endpoint that performs multiple operations."""
        # Access correlation ID multiple times
        id1 = request.state.correlation_id
        id2 = request.state.correlation_id
        id3 = request.state.correlation_id
        
        return {
            "ids": [id1, id2, id3],
            "all_same": id1 == id2 == id3
        }
    
    setup_correlation_id_middleware(app)
    test_client = TestClient(app)
    
    # Make request with correlation ID
    response = test_client.get(
        "/multi-op",
        headers={"X-Correlation-ID": correlation_id}
    )
    
    data = response.json()
    
    # All operations should see the same correlation ID
    assert data["all_same"] is True, \
        "Correlation ID should be consistent across all operations"
    
    # All IDs should match the provided ID
    assert all(cid == correlation_id for cid in data["ids"]), \
        f"All operations should see correlation ID '{correlation_id}'"


# Feature: backend-optimization, Property 32: Correlation ID propagation
@given(
    num_requests=st.integers(min_value=1, max_value=15)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_32_structlog_context_cleared_even_on_error(num_requests):
    """
    Property 32.7: Structlog context is cleared even when request fails.
    
    For any request that raises an error, the structlog context should
    still be cleared to prevent context leakage.
    
    **Validates: Requirements 7.2**
    """
    # Create app with error endpoint
    app = FastAPI()
    
    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")
    
    setup_correlation_id_middleware(app)
    client = TestClient(app, raise_server_exceptions=False)
    
    with patch('structlog.contextvars.clear_contextvars') as mock_clear:
        # Make multiple requests that will fail
        for _ in range(num_requests):
            response = client.get("/error")
            # Request will fail but that's expected
        
        # clear_contextvars should still be called for each request
        assert mock_clear.call_count == num_requests, \
            f"Context should be cleared {num_requests} times even on errors, got {mock_clear.call_count}"


# Feature: backend-optimization, Property 32: Correlation ID propagation
@given(
    correlation_id=correlation_id_strings
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_32_correlation_id_in_response_matches_request(correlation_id):
    """
    Property 32.8: Correlation ID in response matches the one from request.
    
    For any request with a provided correlation ID, the response should
    include the same correlation ID in both the header and accessible
    from request.state.
    
    **Validates: Requirements 7.2**
    """
    # Filter out empty strings
    assume(len(correlation_id.strip()) > 0)
    
    client = create_test_client()
    
    # Make request with correlation ID
    response = client.get(
        "/test",
        headers={"X-Correlation-ID": correlation_id}
    )
    
    # Get correlation ID from response
    body_id = response.json()["correlation_id"]
    header_id = response.headers.get("X-Correlation-ID")
    
    # Both should match the provided ID
    assert body_id == correlation_id, \
        f"Body should have correlation ID '{correlation_id}', got '{body_id}'"
    assert header_id == correlation_id, \
        f"Header should have correlation ID '{correlation_id}', got '{header_id}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
