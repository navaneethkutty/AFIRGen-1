"""
Error response formatting system for standardized error responses.

This module provides a comprehensive error response formatting system that creates
standardized error responses with descriptive messages and correlation IDs for tracing.

Validates: Requirements 6.2, 6.6
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
import traceback


class ErrorCode(str, Enum):
    """
    Standard error codes for categorizing errors.
    
    These codes help clients understand the type of error and take appropriate action.
    """
    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INVALID_REQUEST = "INVALID_REQUEST"
    
    # Server errors (5xx)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    
    # Retry-related errors
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"
    CIRCUIT_BREAKER_OPEN = "CIRCUIT_BREAKER_OPEN"


class ErrorResponse(BaseModel):
    """
    Standardized error response model.
    
    Provides a consistent error response format across the entire API with:
    - Descriptive error messages
    - Error codes for categorization
    - Correlation IDs for tracing
    - Timestamps for debugging
    - Optional additional details
    
    Validates: Requirements 6.2, 6.6
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "error": "Resource not found",
            "error_code": "RESOURCE_NOT_FOUND",
            "correlation_id": "abc-123-def-456",
            "timestamp": "2024-01-15T10:30:45.123Z",
            "details": {
                "resource_type": "FIR",
                "resource_id": "fir_12345"
            }
        }
    })
    
    error: str = Field(..., description="Human-readable error message")
    error_code: ErrorCode = Field(..., description="Machine-readable error code")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for request tracing")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), description="ISO 8601 timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying (for rate limits)")


class ErrorResponseFormatter:
    """
    Formatter for creating standardized error responses.
    
    Provides methods to create error responses for different scenarios:
    - Validation errors
    - Authentication/authorization failures
    - Resource not found
    - Internal server errors
    - Retry exhaustion
    - Circuit breaker open
    
    All error responses include correlation IDs for tracing and descriptive messages.
    
    Validates: Requirements 6.2, 6.6
    """
    
    @staticmethod
    def create_error_response(
        message: str,
        error_code: ErrorCode,
        correlation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None
    ) -> ErrorResponse:
        """
        Create a standardized error response.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            correlation_id: Optional correlation ID for request tracing
            details: Optional additional error details
            retry_after: Optional seconds to wait before retrying
            
        Returns:
            ErrorResponse with standardized format
            
        Example:
            >>> formatter = ErrorResponseFormatter()
            >>> error = formatter.create_error_response(
            ...     message="FIR not found",
            ...     error_code=ErrorCode.RESOURCE_NOT_FOUND,
            ...     correlation_id="abc-123",
            ...     details={"resource_id": "fir_12345"}
            ... )
            
        Validates: Requirements 6.2, 6.6
        """
        return ErrorResponse(
            error=message,
            error_code=error_code,
            correlation_id=correlation_id,
            details=details,
            retry_after=retry_after
        )
    
    @staticmethod
    def validation_error(
        message: str,
        correlation_id: Optional[str] = None,
        field_errors: Optional[Dict[str, str]] = None
    ) -> ErrorResponse:
        """
        Create a validation error response.
        
        Args:
            message: Error message
            correlation_id: Correlation ID for tracing
            field_errors: Optional dictionary of field-specific errors
            
        Returns:
            ErrorResponse for validation error
            
        Example:
            >>> error = ErrorResponseFormatter.validation_error(
            ...     message="Invalid input data",
            ...     correlation_id="abc-123",
            ...     field_errors={"email": "Invalid email format"}
            ... )
        """
        details = {"field_errors": field_errors} if field_errors else None
        return ErrorResponseFormatter.create_error_response(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            correlation_id=correlation_id,
            details=details
        )
    
    @staticmethod
    def authentication_error(
        message: str = "Authentication failed",
        correlation_id: Optional[str] = None
    ) -> ErrorResponse:
        """
        Create an authentication error response.
        
        Args:
            message: Error message
            correlation_id: Correlation ID for tracing
            
        Returns:
            ErrorResponse for authentication error
        """
        return ErrorResponseFormatter.create_error_response(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_FAILED,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def authorization_error(
        message: str = "Insufficient permissions",
        correlation_id: Optional[str] = None,
        required_permission: Optional[str] = None
    ) -> ErrorResponse:
        """
        Create an authorization error response.
        
        Args:
            message: Error message
            correlation_id: Correlation ID for tracing
            required_permission: Optional required permission
            
        Returns:
            ErrorResponse for authorization error
        """
        details = {"required_permission": required_permission} if required_permission else None
        return ErrorResponseFormatter.create_error_response(
            message=message,
            error_code=ErrorCode.AUTHORIZATION_FAILED,
            correlation_id=correlation_id,
            details=details
        )
    
    @staticmethod
    def resource_not_found(
        resource_type: str,
        resource_id: str,
        correlation_id: Optional[str] = None
    ) -> ErrorResponse:
        """
        Create a resource not found error response.
        
        Args:
            resource_type: Type of resource (e.g., "FIR", "User")
            resource_id: ID of the resource
            correlation_id: Correlation ID for tracing
            
        Returns:
            ErrorResponse for resource not found
            
        Example:
            >>> error = ErrorResponseFormatter.resource_not_found(
            ...     resource_type="FIR",
            ...     resource_id="fir_12345",
            ...     correlation_id="abc-123"
            ... )
        """
        return ErrorResponseFormatter.create_error_response(
            message=f"{resource_type} with ID '{resource_id}' not found",
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            correlation_id=correlation_id,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id
            }
        )
    
    @staticmethod
    def resource_conflict(
        message: str,
        correlation_id: Optional[str] = None,
        conflicting_resource: Optional[str] = None
    ) -> ErrorResponse:
        """
        Create a resource conflict error response.
        
        Args:
            message: Error message
            correlation_id: Correlation ID for tracing
            conflicting_resource: Optional ID of conflicting resource
            
        Returns:
            ErrorResponse for resource conflict
        """
        details = {"conflicting_resource": conflicting_resource} if conflicting_resource else None
        return ErrorResponseFormatter.create_error_response(
            message=message,
            error_code=ErrorCode.RESOURCE_CONFLICT,
            correlation_id=correlation_id,
            details=details
        )
    
    @staticmethod
    def rate_limit_exceeded(
        message: str = "Rate limit exceeded",
        correlation_id: Optional[str] = None,
        retry_after: int = 60
    ) -> ErrorResponse:
        """
        Create a rate limit exceeded error response.
        
        Args:
            message: Error message
            correlation_id: Correlation ID for tracing
            retry_after: Seconds to wait before retrying
            
        Returns:
            ErrorResponse for rate limit exceeded
        """
        return ErrorResponseFormatter.create_error_response(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            correlation_id=correlation_id,
            retry_after=retry_after
        )
    
    @staticmethod
    def internal_server_error(
        message: str = "Internal server error",
        correlation_id: Optional[str] = None,
        exception: Optional[Exception] = None,
        include_traceback: bool = False
    ) -> ErrorResponse:
        """
        Create an internal server error response.
        
        Args:
            message: Error message
            correlation_id: Correlation ID for tracing
            exception: Optional exception that caused the error
            include_traceback: Whether to include stack trace (only for development)
            
        Returns:
            ErrorResponse for internal server error
            
        Example:
            >>> try:
            ...     # Some operation
            ...     pass
            ... except Exception as e:
            ...     error = ErrorResponseFormatter.internal_server_error(
            ...         message="Failed to process request",
            ...         correlation_id="abc-123",
            ...         exception=e
            ...     )
        """
        details = {}
        if exception:
            details["exception_type"] = type(exception).__name__
            details["exception_message"] = str(exception)
            if include_traceback:
                details["traceback"] = traceback.format_exc()
        
        return ErrorResponseFormatter.create_error_response(
            message=message,
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            correlation_id=correlation_id,
            details=details if details else None
        )
    
    @staticmethod
    def service_unavailable(
        service_name: str,
        correlation_id: Optional[str] = None,
        retry_after: Optional[int] = None
    ) -> ErrorResponse:
        """
        Create a service unavailable error response.
        
        Args:
            service_name: Name of the unavailable service
            correlation_id: Correlation ID for tracing
            retry_after: Optional seconds to wait before retrying
            
        Returns:
            ErrorResponse for service unavailable
        """
        return ErrorResponseFormatter.create_error_response(
            message=f"Service '{service_name}' is temporarily unavailable",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            correlation_id=correlation_id,
            details={"service_name": service_name},
            retry_after=retry_after
        )
    
    @staticmethod
    def database_error(
        message: str = "Database operation failed",
        correlation_id: Optional[str] = None,
        operation: Optional[str] = None
    ) -> ErrorResponse:
        """
        Create a database error response.
        
        Args:
            message: Error message
            correlation_id: Correlation ID for tracing
            operation: Optional database operation that failed
            
        Returns:
            ErrorResponse for database error
        """
        details = {"operation": operation} if operation else None
        return ErrorResponseFormatter.create_error_response(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            correlation_id=correlation_id,
            details=details
        )
    
    @staticmethod
    def cache_error(
        message: str = "Cache operation failed",
        correlation_id: Optional[str] = None,
        operation: Optional[str] = None
    ) -> ErrorResponse:
        """
        Create a cache error response.
        
        Args:
            message: Error message
            correlation_id: Correlation ID for tracing
            operation: Optional cache operation that failed
            
        Returns:
            ErrorResponse for cache error
        """
        details = {"operation": operation} if operation else None
        return ErrorResponseFormatter.create_error_response(
            message=message,
            error_code=ErrorCode.CACHE_ERROR,
            correlation_id=correlation_id,
            details=details
        )
    
    @staticmethod
    def external_service_error(
        service_name: str,
        message: Optional[str] = None,
        correlation_id: Optional[str] = None,
        status_code: Optional[int] = None
    ) -> ErrorResponse:
        """
        Create an external service error response.
        
        Args:
            service_name: Name of the external service
            message: Optional error message
            correlation_id: Correlation ID for tracing
            status_code: Optional HTTP status code from external service
            
        Returns:
            ErrorResponse for external service error
        """
        if not message:
            message = f"External service '{service_name}' returned an error"
        
        details = {"service_name": service_name}
        if status_code:
            details["status_code"] = status_code
        
        return ErrorResponseFormatter.create_error_response(
            message=message,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            correlation_id=correlation_id,
            details=details
        )
    
    @staticmethod
    def timeout_error(
        operation: str,
        timeout_seconds: float,
        correlation_id: Optional[str] = None
    ) -> ErrorResponse:
        """
        Create a timeout error response.
        
        Args:
            operation: Operation that timed out
            timeout_seconds: Timeout duration in seconds
            correlation_id: Correlation ID for tracing
            
        Returns:
            ErrorResponse for timeout error
        """
        return ErrorResponseFormatter.create_error_response(
            message=f"Operation '{operation}' timed out after {timeout_seconds} seconds",
            error_code=ErrorCode.TIMEOUT_ERROR,
            correlation_id=correlation_id,
            details={
                "operation": operation,
                "timeout_seconds": timeout_seconds
            }
        )
    
    @staticmethod
    def retry_exhausted(
        operation: str,
        retry_count: int,
        last_error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> ErrorResponse:
        """
        Create a retry exhausted error response.
        
        This is used when all retry attempts have been exhausted.
        
        Args:
            operation: Operation that failed
            retry_count: Number of retry attempts made
            last_error: Optional last error message
            correlation_id: Correlation ID for tracing
            
        Returns:
            ErrorResponse for retry exhausted
            
        Example:
            >>> error = ErrorResponseFormatter.retry_exhausted(
            ...     operation="fetch_data",
            ...     retry_count=3,
            ...     last_error="Connection timeout",
            ...     correlation_id="abc-123"
            ... )
            
        Validates: Requirements 6.2
        """
        details = {
            "operation": operation,
            "retry_count": retry_count
        }
        if last_error:
            details["last_error"] = last_error
        
        return ErrorResponseFormatter.create_error_response(
            message=f"Operation '{operation}' failed after {retry_count} retry attempts",
            error_code=ErrorCode.RETRY_EXHAUSTED,
            correlation_id=correlation_id,
            details=details
        )
    
    @staticmethod
    def circuit_breaker_open(
        service_name: str,
        correlation_id: Optional[str] = None,
        retry_after: Optional[int] = None
    ) -> ErrorResponse:
        """
        Create a circuit breaker open error response.
        
        Args:
            service_name: Name of the service with open circuit breaker
            correlation_id: Correlation ID for tracing
            retry_after: Optional seconds to wait before retrying
            
        Returns:
            ErrorResponse for circuit breaker open
        """
        return ErrorResponseFormatter.create_error_response(
            message=f"Circuit breaker for '{service_name}' is open. Service is temporarily unavailable.",
            error_code=ErrorCode.CIRCUIT_BREAKER_OPEN,
            correlation_id=correlation_id,
            details={"service_name": service_name},
            retry_after=retry_after
        )


def format_exception_response(
    exception: Exception,
    correlation_id: Optional[str] = None,
    include_traceback: bool = False
) -> ErrorResponse:
    """
    Format an exception into a standardized error response.
    
    Automatically determines the appropriate error code based on exception type.
    
    Args:
        exception: Exception to format
        correlation_id: Correlation ID for tracing
        include_traceback: Whether to include stack trace
        
    Returns:
        ErrorResponse for the exception
        
    Example:
        >>> try:
        ...     # Some operation
        ...     pass
        ... except Exception as e:
        ...     error = format_exception_response(e, correlation_id="abc-123")
    """
    # Map common exception types to error codes
    if isinstance(exception, ValueError):
        return ErrorResponseFormatter.validation_error(
            message=str(exception),
            correlation_id=correlation_id
        )
    elif isinstance(exception, TimeoutError):
        return ErrorResponseFormatter.timeout_error(
            operation="request",
            timeout_seconds=0,  # Unknown timeout
            correlation_id=correlation_id
        )
    elif isinstance(exception, ConnectionError):
        return ErrorResponseFormatter.external_service_error(
            service_name="external_service",
            message=str(exception),
            correlation_id=correlation_id
        )
    else:
        # Default to internal server error
        return ErrorResponseFormatter.internal_server_error(
            message=str(exception) or "An unexpected error occurred",
            correlation_id=correlation_id,
            exception=exception,
            include_traceback=include_traceback
        )


# Convenience function for creating error responses
def create_error_response(
    message: str,
    error_code: ErrorCode,
    correlation_id: Optional[str] = None,
    **kwargs
) -> ErrorResponse:
    """
    Convenience function for creating error responses.
    
    Args:
        message: Error message
        error_code: Error code
        correlation_id: Correlation ID for tracing
        **kwargs: Additional arguments passed to ErrorResponse
        
    Returns:
        ErrorResponse instance
    """
    return ErrorResponseFormatter.create_error_response(
        message=message,
        error_code=error_code,
        correlation_id=correlation_id,
        **kwargs
    )
