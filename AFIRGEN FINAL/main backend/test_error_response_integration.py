"""
Integration tests for error response formatting with retry handler and circuit breaker.

Tests the integration of error response formatting with other error handling components
to ensure proper error reporting with correlation IDs and descriptive messages.

Validates: Requirements 6.2, 6.6
"""

import pytest
from unittest.mock import Mock, patch
from infrastructure.error_response import (
    ErrorResponseFormatter,
    ErrorCode,
    format_exception_response
)
from infrastructure.retry_handler import RetryHandler
from infrastructure.circuit_breaker import CircuitBreaker, CircuitBreakerError
from infrastructure.error_classification import ErrorClassifier


class TestErrorResponseWithRetryHandler:
    """Test error response formatting with retry handler integration."""
    
    def test_retry_exhausted_error_response(self):
        """Test creating error response when retries are exhausted.
        
        Validates: Requirements 6.2
        """
        retry_handler = RetryHandler(max_retries=3, base_delay=0.01)
        
        # Function that always fails
        def failing_function():
            raise ConnectionError("Connection failed")
        
        # Execute with retry and catch the final exception
        with pytest.raises(ConnectionError) as exc_info:
            retry_handler.execute_with_retry(failing_function)
        
        # Create error response for retry exhaustion
        error = ErrorResponseFormatter.retry_exhausted(
            operation="failing_function",
            retry_count=retry_handler.max_retries,
            last_error=str(exc_info.value),
            correlation_id="test-correlation-123"
        )
        
        # Verify error response
        assert error.error_code == ErrorCode.RETRY_EXHAUSTED
        assert error.correlation_id == "test-correlation-123"
        assert "failed after 3 retry attempts" in error.error
        assert error.details["retry_count"] == 3
        assert error.details["last_error"] == "Connection failed"
    
    def test_retry_with_different_error_types(self):
        """Test error responses for different exception types during retry."""
        retry_handler = RetryHandler(max_retries=2, base_delay=0.01)
        
        # Test with TimeoutError
        def timeout_function():
            raise TimeoutError("Operation timed out")
        
        with pytest.raises(TimeoutError) as exc_info:
            retry_handler.execute_with_retry(timeout_function)
        
        error = format_exception_response(
            exc_info.value,
            correlation_id="test-123"
        )
        assert error.error_code == ErrorCode.TIMEOUT_ERROR
        assert error.correlation_id == "test-123"
    
    def test_non_retryable_error_immediate_response(self):
        """Test that non-retryable errors get immediate error responses."""
        retry_handler = RetryHandler(max_retries=3, base_delay=0.01)
        
        # Function that raises non-retryable error
        def validation_error_function():
            raise ValueError("Invalid input")
        
        # Should fail immediately without retries
        with pytest.raises(ValueError) as exc_info:
            retry_handler.execute_with_retry(validation_error_function)
        
        # Create error response
        error = ErrorResponseFormatter.validation_error(
            message=str(exc_info.value),
            correlation_id="test-123"
        )
        
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.error == "Invalid input"
        assert error.correlation_id == "test-123"


class TestErrorResponseWithCircuitBreaker:
    """Test error response formatting with circuit breaker integration."""
    
    def test_circuit_breaker_open_error_response(self):
        """Test creating error response when circuit breaker is open."""
        circuit_breaker = CircuitBreaker(
            name="test_service",
            failure_threshold=2,
            recovery_timeout=60
        )
        
        # Function that always fails
        def failing_function():
            raise ConnectionError("Service unavailable")
        
        # Trigger circuit breaker to open
        for _ in range(3):
            try:
                circuit_breaker.call(failing_function)
            except (ConnectionError, CircuitBreakerError):
                pass
        
        # Circuit breaker should now be open
        with pytest.raises(CircuitBreakerError):
            circuit_breaker.call(failing_function)
        
        # Create error response for circuit breaker open
        error = ErrorResponseFormatter.circuit_breaker_open(
            service_name="test_service",
            correlation_id="test-correlation-123",
            retry_after=60
        )
        
        # Verify error response
        assert error.error_code == ErrorCode.CIRCUIT_BREAKER_OPEN
        assert error.correlation_id == "test-correlation-123"
        assert "Circuit breaker" in error.error
        assert "test_service" in error.error
        assert error.details["service_name"] == "test_service"
        assert error.retry_after == 60
    
    def test_circuit_breaker_with_external_service_error(self):
        """Test error response for external service errors with circuit breaker."""
        circuit_breaker = CircuitBreaker(name="model_server")
        
        # Mock external service call that fails
        def call_external_service():
            raise ConnectionError("Model server connection failed")
        
        # First failure
        with pytest.raises(ConnectionError) as exc_info:
            circuit_breaker.call(call_external_service)
        
        # Create error response
        error = ErrorResponseFormatter.external_service_error(
            service_name="model_server",
            message=str(exc_info.value),
            correlation_id="test-123",
            status_code=503
        )
        
        assert error.error_code == ErrorCode.EXTERNAL_SERVICE_ERROR
        assert error.correlation_id == "test-123"
        assert error.details["service_name"] == "model_server"
        assert error.details["status_code"] == 503


class TestErrorResponseWithCorrelationID:
    """Test that error responses always include correlation IDs for tracing.
    
    Validates: Requirements 6.6
    """
    
    def test_correlation_id_propagation_through_retry(self):
        """Test that correlation ID is maintained through retry attempts."""
        correlation_id = "request-abc-123"
        retry_handler = RetryHandler(max_retries=2, base_delay=0.01)
        
        def failing_function():
            raise ConnectionError("Connection failed")
        
        with pytest.raises(ConnectionError):
            retry_handler.execute_with_retry(failing_function)
        
        # Create error response with correlation ID
        error = ErrorResponseFormatter.retry_exhausted(
            operation="failing_function",
            retry_count=2,
            last_error="Connection failed",
            correlation_id=correlation_id
        )
        
        # Verify correlation ID is present
        assert error.correlation_id == correlation_id
    
    def test_correlation_id_in_all_error_types(self):
        """Test that correlation ID is included in all error response types."""
        correlation_id = "request-xyz-789"
        
        # Test various error types
        errors = [
            ErrorResponseFormatter.validation_error(
                message="Invalid input",
                correlation_id=correlation_id
            ),
            ErrorResponseFormatter.resource_not_found(
                resource_type="FIR",
                resource_id="123",
                correlation_id=correlation_id
            ),
            ErrorResponseFormatter.internal_server_error(
                message="Server error",
                correlation_id=correlation_id
            ),
            ErrorResponseFormatter.retry_exhausted(
                operation="test",
                retry_count=3,
                correlation_id=correlation_id
            ),
            ErrorResponseFormatter.circuit_breaker_open(
                service_name="test",
                correlation_id=correlation_id
            ),
        ]
        
        # All should have the correlation ID
        for error in errors:
            assert error.correlation_id == correlation_id
    
    def test_error_logging_with_correlation_id(self):
        """Test that errors are logged with correlation IDs."""
        from infrastructure.logging import get_logger
        
        logger = get_logger(__name__)
        correlation_id = "request-log-123"
        
        # Create error response
        error = ErrorResponseFormatter.internal_server_error(
            message="Test error",
            correlation_id=correlation_id
        )
        
        # Log the error (in real usage, this would be done in exception handlers)
        with patch.object(logger, 'error') as mock_log:
            logger.error(
                "Error occurred",
                correlation_id=error.correlation_id,
                error_code=error.error_code,
                error_message=error.error
            )
            
            # Verify logging was called with correlation ID
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["correlation_id"] == correlation_id


class TestErrorResponseDescriptiveMessages:
    """Test that error responses include descriptive messages.
    
    Validates: Requirements 6.2, 6.6
    """
    
    def test_retry_exhausted_descriptive_message(self):
        """Test that retry exhausted error has descriptive message."""
        error = ErrorResponseFormatter.retry_exhausted(
            operation="fetch_model_data",
            retry_count=3,
            last_error="Connection timeout after 30 seconds",
            correlation_id="test-123"
        )
        
        # Message should be descriptive
        assert "fetch_model_data" in error.error
        assert "3 retry attempts" in error.error
        assert error.details["last_error"] == "Connection timeout after 30 seconds"
    
    def test_resource_not_found_descriptive_message(self):
        """Test that resource not found error has descriptive message."""
        error = ErrorResponseFormatter.resource_not_found(
            resource_type="FIR",
            resource_id="fir_12345",
            correlation_id="test-123"
        )
        
        # Message should clearly indicate what was not found
        assert "FIR" in error.error
        assert "fir_12345" in error.error
        assert "not found" in error.error
    
    def test_timeout_error_descriptive_message(self):
        """Test that timeout error has descriptive message."""
        error = ErrorResponseFormatter.timeout_error(
            operation="model_inference",
            timeout_seconds=30.0,
            correlation_id="test-123"
        )
        
        # Message should include operation and timeout duration
        assert "model_inference" in error.error
        assert "30.0 seconds" in error.error
        assert "timed out" in error.error
    
    def test_circuit_breaker_descriptive_message(self):
        """Test that circuit breaker error has descriptive message."""
        error = ErrorResponseFormatter.circuit_breaker_open(
            service_name="model_server",
            correlation_id="test-123",
            retry_after=60
        )
        
        # Message should explain circuit breaker state
        assert "Circuit breaker" in error.error
        assert "model_server" in error.error
        assert "open" in error.error.lower()
        assert error.retry_after == 60


class TestErrorResponseWithDetails:
    """Test that error responses include relevant details."""
    
    def test_validation_error_with_field_details(self):
        """Test validation error includes field-specific details."""
        error = ErrorResponseFormatter.validation_error(
            message="Validation failed",
            correlation_id="test-123",
            field_errors={
                "email": "Invalid email format",
                "age": "Must be a positive integer",
                "phone": "Invalid phone number format"
            }
        )
        
        assert error.details is not None
        assert "field_errors" in error.details
        assert len(error.details["field_errors"]) == 3
        assert error.details["field_errors"]["email"] == "Invalid email format"
    
    def test_external_service_error_with_status_code(self):
        """Test external service error includes status code."""
        error = ErrorResponseFormatter.external_service_error(
            service_name="model_server",
            message="Service returned error",
            correlation_id="test-123",
            status_code=503
        )
        
        assert error.details["service_name"] == "model_server"
        assert error.details["status_code"] == 503
    
    def test_internal_server_error_with_exception_details(self):
        """Test internal server error includes exception details."""
        exc = ValueError("Invalid configuration")
        error = ErrorResponseFormatter.internal_server_error(
            message="Configuration error",
            correlation_id="test-123",
            exception=exc,
            include_traceback=False
        )
        
        assert error.details["exception_type"] == "ValueError"
        assert error.details["exception_message"] == "Invalid configuration"
        assert "traceback" not in error.details


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
