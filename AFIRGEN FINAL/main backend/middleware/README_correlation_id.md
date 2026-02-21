# Correlation ID Middleware

## Overview

The Correlation ID Middleware generates a unique identifier for each incoming HTTP request and propagates it through all operations. This enables request tracing across the entire system, making it easier to debug issues and track requests through logs.

## Features

- **Automatic ID Generation**: Generates a unique UUID4 for each request
- **Header Support**: Accepts existing correlation IDs from `X-Correlation-ID` header
- **Request Context**: Adds correlation ID to `request.state` for handler access
- **Structlog Integration**: Automatically binds correlation ID to structlog context
- **Response Headers**: Includes correlation ID in response headers for client tracking

## Installation

The middleware is automatically available in the `middleware` package:

```python
from middleware import CorrelationIdMiddleware, setup_correlation_id_middleware
```

## Usage

### Basic Setup

Add the middleware to your FastAPI application:

```python
from fastapi import FastAPI
from middleware import setup_correlation_id_middleware

app = FastAPI()

# Add correlation ID middleware
# This should be added early in the middleware stack
setup_correlation_id_middleware(app)
```

### Accessing Correlation ID in Handlers

The correlation ID is available in `request.state`:

```python
from fastapi import Request

@app.get("/example")
async def example_endpoint(request: Request):
    correlation_id = request.state.correlation_id
    
    # Use correlation ID for logging, tracking, etc.
    logger.info("Processing request", correlation_id=correlation_id)
    
    return {"correlation_id": correlation_id}
```

### Client-Provided Correlation IDs

Clients can provide their own correlation ID via the `X-Correlation-ID` header:

```bash
curl -H "X-Correlation-ID: my-custom-id-123" http://localhost:8000/api/endpoint
```

The middleware will use the provided ID instead of generating a new one.

### Automatic Logging Integration

When using structlog, the correlation ID is automatically included in all log entries:

```python
from infrastructure.logging import get_logger

logger = get_logger(__name__)

@app.get("/example")
async def example_endpoint(request: Request):
    # Correlation ID is automatically included in logs
    logger.info("Processing request", action="create_fir")
    
    # Log output will include: {"correlation_id": "...", "action": "create_fir", ...}
```

## How It Works

### Request Flow

1. **Request Arrives**: Middleware intercepts incoming request
2. **ID Check**: Checks for existing `X-Correlation-ID` header
3. **ID Generation**: Generates UUID4 if no ID provided
4. **State Binding**: Adds ID to `request.state.correlation_id`
5. **Context Binding**: Binds ID to structlog context via `contextvars`
6. **Request Processing**: Request proceeds through handlers
7. **Response Headers**: Adds `X-Correlation-ID` to response
8. **Context Cleanup**: Clears structlog context after request

### Structlog Integration

The middleware uses structlog's `contextvars` to bind the correlation ID:

```python
# Bind correlation ID to context
structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

# All logs during request will include correlation_id
logger.info("message")  # {"correlation_id": "...", "event": "message", ...}

# Clear context after request
structlog.contextvars.clear_contextvars()
```

## Configuration

### Header Name

The default header name is `X-Correlation-ID`. To use a different header:

```python
from middleware.correlation_id_middleware import CorrelationIdMiddleware

# Modify the class constant
CorrelationIdMiddleware.CORRELATION_ID_HEADER = "X-Request-ID"
```

### UUID Format

The middleware uses UUID4 for guaranteed uniqueness. The format is:

```
xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
```

Example: `550e8400-e29b-41d4-a716-446655440000`

## Testing

### Unit Tests

Run the unit tests:

```bash
pytest test_correlation_id_middleware.py -v
```

### Manual Testing

Test correlation ID generation:

```bash
# Request without correlation ID (will generate one)
curl -v http://localhost:8000/api/endpoint

# Check response headers for X-Correlation-ID

# Request with correlation ID (will use provided one)
curl -v -H "X-Correlation-ID: test-123" http://localhost:8000/api/endpoint
```

## Integration with Other Components

### Metrics Middleware

The metrics middleware can access the correlation ID:

```python
correlation_id = getattr(request.state, "correlation_id", None)
# Use in metrics labels or context
```

### Error Responses

Include correlation ID in error responses for debugging:

```python
from fastapi import HTTPException, Request

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    correlation_id = getattr(request.state, "correlation_id", None)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "correlation_id": correlation_id
        }
    )
```

### Background Tasks

Pass correlation ID to background tasks for tracing:

```python
from fastapi import BackgroundTasks, Request

@app.post("/process")
async def process_endpoint(request: Request, background_tasks: BackgroundTasks):
    correlation_id = request.state.correlation_id
    
    # Pass correlation ID to background task
    background_tasks.add_task(process_data, correlation_id=correlation_id)
```

## Best Practices

1. **Add Early**: Add correlation ID middleware early in the middleware stack so it's available for all subsequent middleware and handlers

2. **Include in Logs**: Always include correlation ID in log entries for request tracing

3. **Include in Errors**: Include correlation ID in error responses to help users report issues

4. **Propagate to External Services**: When calling external services, pass the correlation ID in headers

5. **Document for Clients**: Document the `X-Correlation-ID` header in API documentation so clients can provide their own IDs

## Troubleshooting

### Correlation ID Not in Logs

Ensure structlog is configured correctly:

```python
from infrastructure.logging import configure_logging

configure_logging()  # Must be called before using logger
```

### Correlation ID Not in Response

Check that the middleware is added to the app:

```python
# Verify middleware is added
print(app.user_middleware)  # Should include CorrelationIdMiddleware
```

### Different IDs in Request and Response

This should not happen. If it does, check for:
- Multiple correlation ID middleware instances
- Middleware order issues
- Manual modification of `request.state.correlation_id`

## Performance Considerations

- **UUID Generation**: UUID4 generation is fast (~1-2 microseconds)
- **Context Binding**: Structlog context binding is lightweight
- **Memory**: Each request stores one string (~36 bytes for UUID)
- **Overhead**: Total middleware overhead is negligible (<0.1ms per request)

## Requirements Validation

This middleware validates the following requirements:

- **Requirement 7.1**: Generates unique correlation ID for each request
- **Requirement 7.2**: Propagates correlation ID through all operations via structlog context

## Related Components

- `infrastructure/logging.py`: Structured logging with structlog
- `middleware/metrics_middleware.py`: Metrics collection middleware
- `infrastructure/error_response.py`: Error response formatting

## References

- [Structlog Documentation](https://www.structlog.org/)
- [FastAPI Middleware](https://fastapi.tiangolo.com/advanced/middleware/)
- [Correlation IDs Best Practices](https://www.rapid7.com/blog/post/2016/12/23/the-value-of-correlation-ids/)
