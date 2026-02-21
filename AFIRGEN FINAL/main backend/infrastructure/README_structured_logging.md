# Structured Logging with structlog

## Overview

This module provides structured logging capabilities using `structlog` with JSON formatting, correlation ID tracking, sensitive data redaction, and configurable log levels per module.

## Features

- **JSON Formatting**: All logs are output in structured JSON format for easy parsing and analysis
- **Required Fields**: Every log entry includes timestamp, level, service, and message fields
- **Correlation ID Tracking**: Automatic correlation ID propagation through request lifecycle
- **Context Injection**: Easy context injection via `with_context()` and `with_correlation_id()` methods
- **Sensitive Data Redaction**: Automatic redaction of sensitive fields (passwords, tokens, etc.)
- **Per-Module Log Levels**: Configure different log levels for different modules
- **Configurable Output**: Support for stdout, stderr, or file output
- **Service Name Tagging**: All logs include the service name for multi-service environments

## Configuration

### Environment Variables

```bash
# Global log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log format (json or console)
LOG_FORMAT=json

# Service name (included in all log entries)
SERVICE_NAME=afirgen-backend

# Output destination (stdout, stderr, or file path)
LOG_OUTPUT=stdout

# Per-module log levels (comma-separated MODULE=LEVEL pairs)
LOG_MODULE_LEVELS=infrastructure.database=DEBUG,services.fir_service=INFO,api.routes=WARNING
```

### Configuration Examples

**Development (Console Output)**:
```bash
LOG_LEVEL=DEBUG
LOG_FORMAT=console
LOG_OUTPUT=stdout
```

**Production (JSON to File)**:
```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_OUTPUT=/var/log/afirgen/app.log
LOG_MODULE_LEVELS=infrastructure.database=WARNING,infrastructure.cache_manager=INFO
```

**Debugging Specific Modules**:
```bash
LOG_LEVEL=INFO
LOG_MODULE_LEVELS=infrastructure.retry_handler=DEBUG,services.model_server_service=DEBUG
```

## Usage

### Basic Logging

```python
from infrastructure.logging import get_logger

logger = get_logger(__name__)

# Simple log messages
logger.info("FIR created successfully")
logger.error("Failed to connect to database")

# Log with context
logger.info("Processing request", user_id="user_123", fir_id="fir_456")
```

### Logging with Context

```python
# Create a logger with persistent context
logger = get_logger(__name__)
request_logger = logger.with_context(
    correlation_id="abc-123-def-456",
    user_id="user_789"
)

# All subsequent logs will include the context
request_logger.info("Request started")
request_logger.info("Validation passed")
request_logger.info("Request completed")
```

### Correlation ID Injection

The logger provides multiple ways to inject correlation IDs:

**Method 1: Using `with_correlation_id()` (Recommended)**
```python
logger = get_logger(__name__)
request_logger = logger.with_correlation_id("abc-123-def-456")

# All logs will include the correlation ID
request_logger.info("Processing request")
request_logger.info("Request completed")
```

**Method 2: Using `with_context()`**
```python
logger = get_logger(__name__)
request_logger = logger.with_context(correlation_id="abc-123-def-456")

request_logger.info("Processing request")
```

**Method 3: Using structlog contextvars (for middleware)**
```python
from infrastructure.logging import get_logger
import structlog

logger = get_logger(__name__)

# Bind correlation ID to context (typically done in middleware)
structlog.contextvars.bind_contextvars(correlation_id="abc-123")

# All logs in this context will include the correlation ID
logger.info("Processing FIR creation")
logger.info("Validation completed")
```

## Log Output Format

### JSON Format

All log entries include the following required fields:

```json
{
  "message": "FIR created successfully",
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "info",
  "service": "afirgen-backend",
  "logger": "services.fir_service",
  "correlation_id": "abc-123-def-456",
  "user_id": "user_789",
  "fir_id": "fir_12345"
}
```

**Required Fields:**
- `message`: The log message
- `timestamp`: ISO 8601 formatted timestamp
- `level`: Log level (debug, info, warning, error, critical)
- `service`: Service name from configuration

**Optional Context Fields:**
- `correlation_id`: Request correlation ID for tracing
- `logger`: Module name where log was generated
- Any additional context passed via `with_context()` or as kwargs

### Console Format (Development)

```
2024-01-15T10:30:45.123456Z [info     ] FIR created successfully [services.fir_service] correlation_id=abc-123-def-456 user_id=user_789 fir_id=fir_12345
```

## Sensitive Data Redaction

The following fields are automatically redacted in logs:
- `password`
- `token`
- `api_key`
- `secret`
- `authorization`
- `credit_card`
- `ssn`
- `phone`
- `email`

Example:
```python
logger.info("User login", username="john", password="secret123")
# Output: {"event": "User login", "username": "john", "password": "***REDACTED***"}
```

## Per-Module Log Levels

Configure different log levels for different modules to control verbosity:

```bash
# Set database module to DEBUG, others to INFO
LOG_LEVEL=INFO
LOG_MODULE_LEVELS=infrastructure.database=DEBUG

# Multiple modules
LOG_MODULE_LEVELS=infrastructure.database=DEBUG,services.fir_service=WARNING,api.routes=ERROR
```

This allows you to:
- Debug specific modules without flooding logs
- Reduce noise from verbose modules in production
- Fine-tune logging for different components

## Integration with FastAPI

### Middleware Integration

```python
from fastapi import FastAPI, Request
import structlog
import uuid

app = FastAPI()

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # Generate correlation ID
    correlation_id = str(uuid.uuid4())
    
    # Bind to context
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method
    )
    
    logger = get_logger(__name__)
    logger.info("Request started")
    
    try:
        response = await call_next(request)
        logger.info("Request completed", status_code=response.status_code)
        return response
    finally:
        structlog.contextvars.clear_contextvars()
```

## Best Practices

1. **Use Structured Context**: Always pass context as keyword arguments, not in the message string
   ```python
   # Good
   logger.info("User logged in", user_id=user_id, ip_address=ip)
   
   # Bad
   logger.info(f"User {user_id} logged in from {ip}")
   ```

2. **Use Appropriate Log Levels**:
   - `DEBUG`: Detailed diagnostic information
   - `INFO`: General informational messages
   - `WARNING`: Warning messages for potentially harmful situations
   - `ERROR`: Error messages for serious problems
   - `CRITICAL`: Critical messages for very serious errors

3. **Include Correlation IDs**: Always include correlation IDs for request tracing
   ```python
   logger.info("Processing request", correlation_id=correlation_id)
   ```

4. **Avoid Logging Sensitive Data**: Be careful not to log passwords, tokens, or PII
   - The redaction system catches common field names
   - But always review what you're logging

5. **Use Module-Specific Loggers**: Always use `get_logger(__name__)` to get module-specific loggers
   ```python
   logger = get_logger(__name__)  # Uses current module name
   ```

## Troubleshooting

### Logs Not Appearing

1. Check log level configuration:
   ```bash
   LOG_LEVEL=DEBUG  # Set to DEBUG to see all logs
   ```

2. Check module-specific log levels:
   ```bash
   # Ensure your module isn't set to a higher level
   LOG_MODULE_LEVELS=your.module.name=DEBUG
   ```

### File Output Not Working

1. Ensure the directory exists:
   ```bash
   mkdir -p /var/log/afirgen
   ```

2. Check file permissions:
   ```bash
   chmod 755 /var/log/afirgen
   ```

3. Verify the path in configuration:
   ```bash
   LOG_OUTPUT=/var/log/afirgen/app.log
   ```

### JSON Parsing Errors

If logs aren't valid JSON, check:
1. `LOG_FORMAT=json` is set
2. No custom formatters are interfering
3. All logged values are JSON-serializable

## Performance Considerations

- Structured logging has minimal overhead (~5-10% compared to standard logging)
- JSON rendering is efficient and suitable for production
- File output is buffered for performance
- Consider log rotation for file-based logging (use logrotate or similar)

## Related Components

- **Correlation ID Middleware**: Generates and propagates correlation IDs (Task 10.2)
- **Error Response Formatting**: Includes correlation IDs in error responses (Task 9.9)
- **Metrics Collection**: Logs can be parsed for metrics extraction (Task 8.1)

## Validates Requirements

- **Requirement 7.3**: JSON log format ✅
- **Requirement 7.4**: Include timestamp, log level, service name, and message in each log entry ✅
- **Requirement 7.5**: Redact or mask sensitive information ✅
- **Requirement 7.6**: Configurable log levels per module ✅

## Implementation Details

### Task 10.4 Enhancements

This implementation was enhanced in task 10.4 to ensure:

1. **Required Fields**: All log entries include the four required fields:
   - `timestamp`: ISO 8601 formatted timestamp
   - `level`: Log level (debug, info, warning, error, critical)
   - `service`: Service name from configuration
   - `message`: The log message (renamed from "event" for consistency)

2. **Correlation ID Injection**: Multiple methods for injecting correlation IDs:
   - `with_correlation_id()`: Convenience method for adding correlation IDs
   - `with_context()`: General context injection including correlation IDs
   - `structlog.contextvars`: For middleware-level correlation ID binding

3. **Sensitive Data Redaction**: Automatic redaction of sensitive fields including:
   - Passwords, tokens, API keys, secrets
   - Email addresses, phone numbers
   - Credit card numbers, SSNs
   - Case-insensitive matching
   - Nested dictionary support
