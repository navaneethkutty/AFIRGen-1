# Error Response Formatting System

## Overview

The error response formatting system provides a standardized way to create error responses across the AFIRGen backend. All error responses follow a consistent format with descriptive messages, error codes, correlation IDs for tracing, and optional additional details.

## Features

- **Standardized Format**: All errors follow the same response structure
- **Error Codes**: Machine-readable error codes for client-side handling
- **Correlation IDs**: Request tracing across the system
- **Descriptive Messages**: Human-readable error messages
- **Additional Details**: Optional context-specific error information
- **Retry Information**: Retry-after hints for rate limits and service unavailability

## Error Response Model

```python
{
    "error": "Human-readable error message",
    "error_code": "MACHINE_READABLE_CODE",
    "correlation_id": "abc-123-def-456",
    "timestamp": "2024-01-15T10:30:45.123Z",
    "details": {
        "additional": "context-specific information"
    },
    "retry_after": 60  # Optional, for rate limits
}
```

## Error Codes

### Client Errors (4xx)
- `VALIDATION_ERROR`: Input validation failed
- `AUTHENTICATION_FAILED`: Authentication credentials invalid
- `AUTHORIZATION_FAILED`: Insufficient permissions
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `RESOURCE_CONFLICT`: Resource already exists or conflicts
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INVALID_REQUEST`: Malformed request

### Server Errors (5xx)
- `INTERNAL_SERVER_ERROR`: Unexpected server error
- `SERVICE_UNAVAILABLE`: Service temporarily unavailable
- `DATABASE_ERROR`: Database operation failed
- `CACHE_ERROR`: Cache operation failed
- `EXTERNAL_SERVICE_ERROR`: External service returned error
- `TIMEOUT_ERROR`: Operation timed out

### Retry-Related Errors
- `RETRY_EXHAUSTED`: All retry attempts failed
- `CIRCUIT_BREAKER_OPEN`: Circuit breaker is open

## Usage Examples

### Basic Error Response

```python
from infrastructure.error_response import ErrorResponseFormatter, ErrorCode

# Create a simple error response
error = ErrorResponseFormatter.create_error_response(
    message="Invalid input data",
    error_code=ErrorCode.VALIDATION_ERROR,
    correlation_id="abc-123-def-456"
)
```

### Validation Error

```python
error = ErrorResponseFormatter.validation_error(
    message="Invalid input data",
    correlation_id="abc-123",
    field_errors={
        "email": "Invalid email format",
        "age": "Must be a positive integer"
    }
)
```

### Resource Not Found

```python
error = ErrorResponseFormatter.resource_not_found(
    resource_type="FIR",
    resource_id="fir_12345",
    correlation_id="abc-123"
)
# Returns: "FIR with ID 'fir_12345' not found"
```

### Retry Exhausted

```python
error = ErrorResponseFormatter.retry_exhausted(
    operation="fetch_model_server_data",
    retry_count=3,
    last_error="Connection timeout",
    correlation_id="abc-123"
)
```

### Circuit Breaker Open

```python
error = ErrorResponseFormatter.circuit_breaker_open(
    service_name="model_server",
    correlation_id="abc-123",
    retry_after=60
)
```

### Internal Server Error

```python
try:
    # Some operation
    result = risky_operation()
except Exception as e:
    error = ErrorResponseFormatter.internal_server_error(
        message="Failed to process request",
        correlation_id="abc-123",
        exception=e,
        include_traceback=False  # Set to True only in development
    )
```

### Rate Limit Exceeded

```python
error = ErrorResponseFormatter.rate_limit_exceeded(
    message="Too many requests",
    correlation_id="abc-123",
    retry_after=60  # Seconds to wait
)
```

### Service Unavailable

```python
error = ErrorResponseFormatter.service_unavailable(
    service_name="model_server",
    correlation_id="abc-123",
    retry_after=30
)
```

### External Service Error

```python
error = ErrorResponseFormatter.external_service_error(
    service_name="model_server",
    message="Model server returned an error",
    correlation_id="abc-123",
    status_code=503
)
```

### Timeout Error

```python
error = ErrorResponseFormatter.timeout_error(
    operation="model_inference",
    timeout_seconds=30.0,
    correlation_id="abc-123"
)
```

## Integration with FastAPI

### Using in Exception Handlers

```python
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from infrastructure.error_response import ErrorResponseFormatter, format_exception_response

app = FastAPI()

@app.exception_handler(ValueError)
async def validation_exception_handler(request: Request, exc: ValueError):
    correlation_id = request.state.correlation_id if hasattr(request.state, 'correlation_id') else None
    error = ErrorResponseFormatter.validation_error(
        message=str(exc),
        correlation_id=correlation_id
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error.dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    correlation_id = request.state.correlation_id if hasattr(request.state, 'correlation_id') else None
    error = format_exception_response(
        exception=exc,
        correlation_id=correlation_id,
        include_traceback=False
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error.dict()
    )
```

### Using in Endpoints

```python
from fastapi import HTTPException, status
from infrastructure.error_response import ErrorResponseFormatter

@app.get("/fir/{fir_id}")
async def get_fir(fir_id: str, request: Request):
    correlation_id = request.state.correlation_id
    
    fir = await fir_repository.get_by_id(fir_id)
    if not fir:
        error = ErrorResponseFormatter.resource_not_found(
            resource_type="FIR",
            resource_id=fir_id,
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error.dict()
        )
    
    return fir
```

### Integration with Retry Handler

```python
from infrastructure.retry_handler import RetryHandler
from infrastructure.error_response import ErrorResponseFormatter

retry_handler = RetryHandler(max_retries=3)

try:
    result = retry_handler.execute_with_retry(
        fetch_data_from_service,
        url="https://api.example.com"
    )
except Exception as e:
    # All retries exhausted
    error = ErrorResponseFormatter.retry_exhausted(
        operation="fetch_data_from_service",
        retry_count=retry_handler.max_retries,
        last_error=str(e),
        correlation_id=correlation_id
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error.dict()
    )
```

### Integration with Circuit Breaker

```python
from infrastructure.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from infrastructure.error_response import ErrorResponseFormatter

circuit_breaker = CircuitBreaker(name="model_server")

try:
    result = circuit_breaker.call(call_model_server, data=input_data)
except CircuitBreakerOpenError:
    error = ErrorResponseFormatter.circuit_breaker_open(
        service_name="model_server",
        correlation_id=correlation_id,
        retry_after=60
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error.dict()
    )
```

## Logging Integration

Error responses should be logged with their correlation IDs:

```python
from infrastructure.logging import get_logger
from infrastructure.error_response import ErrorResponseFormatter

logger = get_logger(__name__)

error = ErrorResponseFormatter.internal_server_error(
    message="Database connection failed",
    correlation_id=correlation_id,
    exception=exc
)

logger.error(
    "Error response created",
    correlation_id=correlation_id,
    error_code=error.error_code,
    error_message=error.error,
    exception_type=type(exc).__name__
)
```

## Best Practices

1. **Always Include Correlation IDs**: Pass correlation IDs from the request context to enable tracing
2. **Use Appropriate Error Codes**: Choose the most specific error code for the situation
3. **Provide Descriptive Messages**: Write clear, actionable error messages for users
4. **Include Relevant Details**: Add context-specific information in the details field
5. **Don't Expose Sensitive Data**: Never include passwords, tokens, or PII in error responses
6. **Use Retry-After for Rate Limits**: Help clients implement proper backoff strategies
7. **Log All Errors**: Ensure all errors are logged with correlation IDs for debugging
8. **Don't Include Tracebacks in Production**: Only include stack traces in development environments

## Testing

The error response formatting system includes comprehensive tests:

```bash
# Run unit tests
pytest test_error_response.py -v

# Run property-based tests
pytest test_error_response_property.py -v
```

## Requirements Validation

This module validates:
- **Requirement 6.2**: Error response after retry exhaustion with descriptive messages
- **Requirement 6.6**: Error logging completeness with correlation IDs and context

## Related Components

- **Error Classification** (`error_classification.py`): Classifies errors as retryable/non-retryable
- **Retry Handler** (`retry_handler.py`): Handles retry logic with exponential backoff
- **Circuit Breaker** (`circuit_breaker.py`): Implements circuit breaker pattern
- **Structured Logging** (`logging.py`): Provides structured logging with correlation IDs
