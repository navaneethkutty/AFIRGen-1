"""
Unit tests for error response formatting system.

Tests the ErrorResponseFormatter and ErrorResponse model to ensure
standardized error responses with correlation IDs and descriptive messages.

Validates: Requirements 6.2, 6.6
"""

import pytest
from datetime import datetime
from infrastructure.error_response import (
    ErrorResponse,
    ErrorCode,
    ErrorResponseFormatter,
    format_exception_response,
    create_error_response
)


class TestErrorResponse:
    """Test ErrorResponse model."""
    
    def test_error_response_creation(self):
        """Test creating an error response with all fields."""
        error = ErrorResponse(
            error="Test error message",
            error_code=ErrorCode.VALIDATION_ERROR,
            correlation_id="test-123",
            details={"field": "value"}
        )
        
        assert error.error == "Test error message"
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.correlation_id == "test-123"
        assert error.details == {"field": "value"}
        assert error.timestamp is not None
        assert error.retry_after is None
    
    def test_error_response_with_retry_after(self):
        """Test error response with retry_after field."""
        error = ErrorResponse(
            error="Rate limit exceeded",
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            retry_after=60
        )
        
        assert error.retry_after == 60
    
    def test_error_response_timestamp_format(self):
        """Test that timestamp is in ISO 8601 format."""
        error = ErrorResponse(
            error="Test error",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR
        )
        
        # Should be able to parse as ISO 8601
        timestamp = error.timestamp.rstrip('Z')
        parsed = datetime.fromisoformat(timestamp)
        assert isinstance(parsed, datetime)
    
    def test_error_response_dict_serialization(self):
        """Test that error response can be serialized to dict."""
        error = ErrorResponse(
            error="Test error",
            error_code=ErrorCode.VALIDATION_ERROR,
            correlation_id="test-123",
            details={"field": "value"}
        )
        
        error_dict = error.model_dump()
        assert error_dict["error"] == "Test error"
        assert error_dict["error_code"] == "VALIDATION_ERROR"
        assert error_dict["correlation_id"] == "test-123"
        assert error_dict["details"] == {"field": "value"}


class TestErrorResponseFormatter:
    """Test ErrorResponseFormatter methods."""
    
    def test_create_error_response(self):
        """Test creating a basic error response."""
        error = ErrorResponseFormatter.create_error_response(
            message="Test error",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            correlation_id="test-123"
        )
        
        assert error.error == "Test error"
        assert error.error_code == ErrorCode.INTERNAL_SERVER_ERROR
        assert error.correlation_id == "test-123"
    
    def test_create_error_response_with_details(self):
        """Test creating error response with additional details."""
        error = ErrorResponseFormatter.create_error_response(
            message="Test error",
            error_code=ErrorCode.VALIDATION_ERROR,
            correlation_id="test-123",
            details={"field": "email", "reason": "invalid format"}
        )
        
        assert error.details == {"field": "email", "reason": "invalid format"}
    
    def test_validation_error(self):
        """Test creating a validation error response."""
        error = ErrorResponseFormatter.validation_error(
            message="Invalid input",
            correlation_id="test-123",
            field_errors={"email": "Invalid format", "age": "Must be positive"}
        )
        
        assert error.error == "Invalid input"
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.correlation_id == "test-123"
        assert error.details == {
            "field_errors": {
                "email": "Invalid format",
                "age": "Must be positive"
            }
        }
    
    def test_validation_error_without_field_errors(self):
        """Test validation error without field-specific errors."""
        error = ErrorResponseFormatter.validation_error(
            message="Invalid input",
            correlation_id="test-123"
        )
        
        assert error.error == "Invalid input"
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.details is None
    
    def test_authentication_error(self):
        """Test creating an authentication error response."""
        error = ErrorResponseFormatter.authentication_error(
            message="Invalid credentials",
            correlation_id="test-123"
        )
        
        assert error.error == "Invalid credentials"
        assert error.error_code == ErrorCode.AUTHENTICATION_FAILED
        assert error.correlation_id == "test-123"
    
    def test_authentication_error_default_message(self):
        """Test authentication error with default message."""
        error = ErrorResponseFormatter.authentication_error(
            correlation_id="test-123"
        )
        
        assert error.error == "Authentication failed"
        assert error.error_code == ErrorCode.AUTHENTICATION_FAILED
    
    def test_authorization_error(self):
        """Test creating an authorization error response."""
        error = ErrorResponseFormatter.authorization_error(
            message="Access denied",
            correlation_id="test-123",
            required_permission="admin"
        )
        
        assert error.error == "Access denied"
        assert error.error_code == ErrorCode.AUTHORIZATION_FAILED
        assert error.correlation_id == "test-123"
        assert error.details == {"required_permission": "admin"}
    
    def test_resource_not_found(self):
        """Test creating a resource not found error response."""
        error = ErrorResponseFormatter.resource_not_found(
            resource_type="FIR",
            resource_id="fir_12345",
            correlation_id="test-123"
        )
        
        assert error.error == "FIR with ID 'fir_12345' not found"
        assert error.error_code == ErrorCode.RESOURCE_NOT_FOUND
        assert error.correlation_id == "test-123"
        assert error.details == {
            "resource_type": "FIR",
            "resource_id": "fir_12345"
        }
    
    def test_resource_conflict(self):
        """Test creating a resource conflict error response."""
        error = ErrorResponseFormatter.resource_conflict(
            message="Resource already exists",
            correlation_id="test-123",
            conflicting_resource="fir_12345"
        )
        
        assert error.error == "Resource already exists"
        assert error.error_code == ErrorCode.RESOURCE_CONFLICT
        assert error.correlation_id == "test-123"
        assert error.details == {"conflicting_resource": "fir_12345"}
    
    def test_rate_limit_exceeded(self):
        """Test creating a rate limit exceeded error response."""
        error = ErrorResponseFormatter.rate_limit_exceeded(
            message="Too many requests",
            correlation_id="test-123",
            retry_after=60
        )
        
        assert error.error == "Too many requests"
        assert error.error_code == ErrorCode.RATE_LIMIT_EXCEEDED
        assert error.correlation_id == "test-123"
        assert error.retry_after == 60
    
    def test_rate_limit_exceeded_default_message(self):
        """Test rate limit error with default message."""
        error = ErrorResponseFormatter.rate_limit_exceeded(
            correlation_id="test-123"
        )
        
        assert error.error == "Rate limit exceeded"
        assert error.retry_after == 60
    
    def test_internal_server_error(self):
        """Test creating an internal server error response."""
        error = ErrorResponseFormatter.internal_server_error(
            message="Unexpected error",
            correlation_id="test-123"
        )
        
        assert error.error == "Unexpected error"
        assert error.error_code == ErrorCode.INTERNAL_SERVER_ERROR
        assert error.correlation_id == "test-123"
    
    def test_internal_server_error_with_exception(self):
        """Test internal server error with exception details."""
        exc = ValueError("Invalid value")
        error = ErrorResponseFormatter.internal_server_error(
            message="Processing failed",
            correlation_id="test-123",
            exception=exc,
            include_traceback=False
        )
        
        assert error.error == "Processing failed"
        assert error.error_code == ErrorCode.INTERNAL_SERVER_ERROR
        assert error.details["exception_type"] == "ValueError"
        assert error.details["exception_message"] == "Invalid value"
        assert "traceback" not in error.details
    
    def test_internal_server_error_with_traceback(self):
        """Test internal server error with traceback included."""
        exc = ValueError("Invalid value")
        error = ErrorResponseFormatter.internal_server_error(
            message="Processing failed",
            correlation_id="test-123",
            exception=exc,
            include_traceback=True
        )
        
        assert "traceback" in error.details
        assert isinstance(error.details["traceback"], str)
    
    def test_service_unavailable(self):
        """Test creating a service unavailable error response."""
        error = ErrorResponseFormatter.service_unavailable(
            service_name="model_server",
            correlation_id="test-123",
            retry_after=30
        )
        
        assert error.error == "Service 'model_server' is temporarily unavailable"
        assert error.error_code == ErrorCode.SERVICE_UNAVAILABLE
        assert error.correlation_id == "test-123"
        assert error.details == {"service_name": "model_server"}
        assert error.retry_after == 30
    
    def test_database_error(self):
        """Test creating a database error response."""
        error = ErrorResponseFormatter.database_error(
            message="Query failed",
            correlation_id="test-123",
            operation="SELECT"
        )
        
        assert error.error == "Query failed"
        assert error.error_code == ErrorCode.DATABASE_ERROR
        assert error.correlation_id == "test-123"
        assert error.details == {"operation": "SELECT"}
    
    def test_cache_error(self):
        """Test creating a cache error response."""
        error = ErrorResponseFormatter.cache_error(
            message="Cache get failed",
            correlation_id="test-123",
            operation="GET"
        )
        
        assert error.error == "Cache get failed"
        assert error.error_code == ErrorCode.CACHE_ERROR
        assert error.correlation_id == "test-123"
        assert error.details == {"operation": "GET"}
    
    def test_external_service_error(self):
        """Test creating an external service error response."""
        error = ErrorResponseFormatter.external_service_error(
            service_name="model_server",
            message="Service returned error",
            correlation_id="test-123",
            status_code=503
        )
        
        assert error.error == "Service returned error"
        assert error.error_code == ErrorCode.EXTERNAL_SERVICE_ERROR
        assert error.correlation_id == "test-123"
        assert error.details == {
            "service_name": "model_server",
            "status_code": 503
        }
    
    def test_external_service_error_default_message(self):
        """Test external service error with default message."""
        error = ErrorResponseFormatter.external_service_error(
            service_name="model_server",
            correlation_id="test-123"
        )
        
        assert error.error == "External service 'model_server' returned an error"
    
    def test_timeout_error(self):
        """Test creating a timeout error response."""
        error = ErrorResponseFormatter.timeout_error(
            operation="model_inference",
            timeout_seconds=30.0,
            correlation_id="test-123"
        )
        
        assert error.error == "Operation 'model_inference' timed out after 30.0 seconds"
        assert error.error_code == ErrorCode.TIMEOUT_ERROR
        assert error.correlation_id == "test-123"
        assert error.details == {
            "operation": "model_inference",
            "timeout_seconds": 30.0
        }
    
    def test_retry_exhausted(self):
        """Test creating a retry exhausted error response.
        
        Validates: Requirements 6.2
        """
        error = ErrorResponseFormatter.retry_exhausted(
            operation="fetch_data",
            retry_count=3,
            last_error="Connection timeout",
            correlation_id="test-123"
        )
        
        assert error.error == "Operation 'fetch_data' failed after 3 retry attempts"
        assert error.error_code == ErrorCode.RETRY_EXHAUSTED
        assert error.correlation_id == "test-123"
        assert error.details == {
            "operation": "fetch_data",
            "retry_count": 3,
            "last_error": "Connection timeout"
        }
    
    def test_retry_exhausted_without_last_error(self):
        """Test retry exhausted without last error message."""
        error = ErrorResponseFormatter.retry_exhausted(
            operation="fetch_data",
            retry_count=3,
            correlation_id="test-123"
        )
        
        assert error.error == "Operation 'fetch_data' failed after 3 retry attempts"
        assert error.details == {
            "operation": "fetch_data",
            "retry_count": 3
        }
        assert "last_error" not in error.details
    
    def test_circuit_breaker_open(self):
        """Test creating a circuit breaker open error response."""
        error = ErrorResponseFormatter.circuit_breaker_open(
            service_name="model_server",
            correlation_id="test-123",
            retry_after=60
        )
        
        assert "Circuit breaker for 'model_server' is open" in error.error
        assert error.error_code == ErrorCode.CIRCUIT_BREAKER_OPEN
        assert error.correlation_id == "test-123"
        assert error.details == {"service_name": "model_server"}
        assert error.retry_after == 60


class TestFormatExceptionResponse:
    """Test format_exception_response function."""
    
    def test_format_value_error(self):
        """Test formatting a ValueError."""
        exc = ValueError("Invalid input")
        error = format_exception_response(exc, correlation_id="test-123")
        
        assert error.error == "Invalid input"
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.correlation_id == "test-123"
    
    def test_format_timeout_error(self):
        """Test formatting a TimeoutError."""
        exc = TimeoutError("Operation timed out")
        error = format_exception_response(exc, correlation_id="test-123")
        
        assert "timed out" in error.error.lower()
        assert error.error_code == ErrorCode.TIMEOUT_ERROR
        assert error.correlation_id == "test-123"
    
    def test_format_connection_error(self):
        """Test formatting a ConnectionError."""
        exc = ConnectionError("Connection failed")
        error = format_exception_response(exc, correlation_id="test-123")
        
        assert error.error == "Connection failed"
        assert error.error_code == ErrorCode.EXTERNAL_SERVICE_ERROR
        assert error.correlation_id == "test-123"
    
    def test_format_generic_exception(self):
        """Test formatting a generic exception."""
        exc = RuntimeError("Unexpected error")
        error = format_exception_response(exc, correlation_id="test-123")
        
        assert error.error == "Unexpected error"
        assert error.error_code == ErrorCode.INTERNAL_SERVER_ERROR
        assert error.correlation_id == "test-123"
    
    def test_format_exception_with_traceback(self):
        """Test formatting exception with traceback."""
        exc = RuntimeError("Test error")
        error = format_exception_response(
            exc,
            correlation_id="test-123",
            include_traceback=True
        )
        
        assert error.details is not None
        assert "traceback" in error.details


class TestCreateErrorResponse:
    """Test create_error_response convenience function."""
    
    def test_create_error_response_convenience(self):
        """Test convenience function for creating error responses."""
        error = create_error_response(
            message="Test error",
            error_code=ErrorCode.VALIDATION_ERROR,
            correlation_id="test-123",
            details={"field": "value"}
        )
        
        assert error.error == "Test error"
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.correlation_id == "test-123"
        assert error.details == {"field": "value"}


class TestErrorResponseWithCorrelationID:
    """Test that all error responses include correlation IDs.
    
    Validates: Requirements 6.6
    """
    
    def test_all_formatters_accept_correlation_id(self):
        """Test that all formatter methods accept correlation_id parameter."""
        correlation_id = "test-correlation-123"
        
        # Test each formatter method
        errors = [
            ErrorResponseFormatter.validation_error(
                message="Test", correlation_id=correlation_id
            ),
            ErrorResponseFormatter.authentication_error(
                correlation_id=correlation_id
            ),
            ErrorResponseFormatter.authorization_error(
                correlation_id=correlation_id
            ),
            ErrorResponseFormatter.resource_not_found(
                resource_type="Test", resource_id="123", correlation_id=correlation_id
            ),
            ErrorResponseFormatter.resource_conflict(
                message="Test", correlation_id=correlation_id
            ),
            ErrorResponseFormatter.rate_limit_exceeded(
                correlation_id=correlation_id
            ),
            ErrorResponseFormatter.internal_server_error(
                correlation_id=correlation_id
            ),
            ErrorResponseFormatter.service_unavailable(
                service_name="test", correlation_id=correlation_id
            ),
            ErrorResponseFormatter.database_error(
                correlation_id=correlation_id
            ),
            ErrorResponseFormatter.cache_error(
                correlation_id=correlation_id
            ),
            ErrorResponseFormatter.external_service_error(
                service_name="test", correlation_id=correlation_id
            ),
            ErrorResponseFormatter.timeout_error(
                operation="test", timeout_seconds=30, correlation_id=correlation_id
            ),
            ErrorResponseFormatter.retry_exhausted(
                operation="test", retry_count=3, correlation_id=correlation_id
            ),
            ErrorResponseFormatter.circuit_breaker_open(
                service_name="test", correlation_id=correlation_id
            ),
        ]
        
        # All errors should have the correlation ID
        for error in errors:
            assert error.correlation_id == correlation_id
    
    def test_error_response_includes_timestamp(self):
        """Test that all error responses include timestamps.
        
        Validates: Requirements 6.6
        """
        error = ErrorResponseFormatter.internal_server_error(
            message="Test error",
            correlation_id="test-123"
        )
        
        assert error.timestamp is not None
        assert isinstance(error.timestamp, str)
        # Should be ISO 8601 format
        assert 'T' in error.timestamp
        assert error.timestamp.endswith('Z')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
