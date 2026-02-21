# Utils Module

This module provides reusable utility functions, validators, and constants for the AFIRGen backend system.

## Overview

The utils module centralizes common operations to reduce code duplication and improve maintainability. It follows the DRY (Don't Repeat Yourself) principle by extracting frequently used logic into dedicated, well-tested modules.

## Modules

### validators.py

Provides input validation and sanitization functions:

- **Text validation**: `sanitize_text()`, `validate_text_length()`
- **Format validation**: `validate_uuid()`, `validate_fir_number()`, `validate_email()`, `validate_url()`
- **File validation**: `validate_file_extension()`, `validate_mime_type()`, `validate_file_size()`
- **Numeric validation**: `validate_positive_integer()`, `validate_range()`
- **Security validation**: `validate_json_depth()` (DoS prevention)

**Example usage:**

```python
from utils.validators import sanitize_text, validate_uuid, ValidationError

try:
    # Sanitize user input
    clean_text = sanitize_text(user_input, allow_html=False)
    
    # Validate UUID format
    session_id = validate_uuid(session_id_param)
except ValidationError as e:
    # Handle validation error
    return {"error": str(e)}
```

### constants.py

Centralizes constants and enums used across the application:

- **Validation limits**: `TextLimits`, `FileLimits`
- **HTTP constants**: `HTTPStatus`, `ContentType`, `HeaderNames`
- **Retry/Circuit breaker**: `RetryDefaults`, `CircuitBreakerDefaults`
- **Cache TTL values**: `CacheTTL`
- **Task priorities**: `TaskPriority`, `TaskStatus`
- **Alert thresholds**: `AlertThresholds`
- **Enums**: `ValidationStep`, `CircuitState`, `LogLevel`, `ErrorCode`

**Example usage:**

```python
from utils.constants import HTTPStatus, CacheTTL, TaskPriority

# Use HTTP status codes
return Response(status_code=HTTPStatus.NOT_FOUND)

# Use cache TTL values
cache.set(key, value, ttl=CacheTTL.FIR_RECORD)

# Use task priorities
task_manager.enqueue(task, priority=TaskPriority.HIGH)
```

### common.py

Provides common utility functions:

- **String operations**: `truncate_string()`, `normalize_whitespace()`, `to_snake_case()`, `mask_sensitive_data()`
- **Date/time**: `get_current_timestamp()`, `format_timestamp()`, `timestamp_to_iso()`
- **Hashing**: `generate_hash()`, `generate_md5()`, `generate_sha256()`
- **Encoding**: `encode_base64()`, `decode_base64()`
- **ID generation**: `generate_uuid()`, `generate_correlation_id()`, `generate_fir_number()`
- **Data structures**: `deep_merge()`, `flatten_dict()`, `chunk_list()`, `get_nested_value()`
- **JSON operations**: `safe_json_loads()`, `safe_json_dumps()`, `pretty_json()`
- **Type conversion**: `to_bool()`, `to_int()`, `to_float()`

**Example usage:**

```python
from utils.common import (
    generate_correlation_id,
    mask_sensitive_data,
    get_current_timestamp,
    deep_merge
)

# Generate correlation ID for request tracking
correlation_id = generate_correlation_id()

# Mask sensitive data in logs
masked_token = mask_sensitive_data(api_token, visible_chars=4)

# Get current timestamp
timestamp = get_current_timestamp()

# Merge configuration dictionaries
config = deep_merge(default_config, user_config)
```

### field_filter.py

Provides field filtering for API responses:

- Filter response fields based on client request
- Validate requested fields against allowed fields
- Support for nested field filtering

**Example usage:**

```python
from utils.field_filter import FieldFilter

# Filter response to include only requested fields
filtered_data = FieldFilter.filter_response(
    data=fir_data,
    fields=["id", "fir_number", "status"],
    allowed_fields=["id", "fir_number", "status", "content", "created_at"]
)
```

### pagination.py

Provides cursor-based pagination utilities:

- Encode/decode pagination cursors
- Create paginated responses with metadata
- Support for custom sort fields

**Example usage:**

```python
from utils.pagination import PaginationHandler

# Create paginated response
paginated = PaginationHandler.create_paginated_response(
    items=fir_records,
    total_count=total,
    limit=100,
    sort_field="created_at"
)

# Decode cursor from request
cursor_info = PaginationHandler.decode_cursor(request.cursor)
```

## Design Principles

### 1. Single Responsibility

Each module has a clear, focused purpose:
- `validators.py`: Input validation
- `constants.py`: Constant definitions
- `common.py`: General utilities
- `field_filter.py`: Response filtering
- `pagination.py`: Pagination logic

### 2. Reusability

All functions are designed to be reusable across different parts of the application. They have clear interfaces, comprehensive documentation, and handle edge cases.

### 3. Type Safety

All functions include type hints for better IDE support and type checking with mypy.

### 4. Error Handling

Validation functions raise `ValidationError` with descriptive messages. Utility functions handle errors gracefully with safe defaults where appropriate.

### 5. Documentation

Every function includes:
- Docstring with description
- Parameter documentation
- Return value documentation
- Example usage
- Requirements reference

## Testing

All utility functions should be tested with:
- Unit tests for specific examples
- Edge case tests (empty inputs, boundary values)
- Error condition tests

Example test structure:

```python
def test_validate_uuid():
    # Valid UUID
    result = validate_uuid("550e8400-e29b-41d4-a716-446655440000")
    assert result == "550e8400-e29b-41d4-a716-446655440000"
    
    # Invalid UUID
    with pytest.raises(ValidationError):
        validate_uuid("invalid-uuid")
```

## Migration Guide

When refactoring existing code to use these utilities:

1. **Identify duplicated logic**: Look for repeated validation, formatting, or conversion code
2. **Replace with utility functions**: Import and use the appropriate utility function
3. **Update imports**: Add imports from the utils module
4. **Test thoroughly**: Ensure behavior is preserved after refactoring

Example migration:

```python
# Before
import re
uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
if not re.match(uuid_pattern, session_id, re.IGNORECASE):
    raise ValueError("Invalid session ID")
session_id = session_id.lower()

# After
from utils.validators import validate_uuid, ValidationError
try:
    session_id = validate_uuid(session_id)
except ValidationError as e:
    raise ValueError(str(e))
```

## Best Practices

1. **Use constants instead of magic numbers**: Replace hardcoded values with named constants
2. **Validate early**: Use validators at API boundaries before processing
3. **Sanitize user input**: Always sanitize text input to prevent XSS/injection
4. **Use type hints**: Leverage type hints for better code quality
5. **Handle errors gracefully**: Use try-except blocks with specific error handling
6. **Log validation failures**: Log validation errors for debugging and security monitoring

## Requirements

This module validates **Requirement 8.5**: Extract reusable utility functions into shared modules.

## Related Modules

- `infrastructure/`: Infrastructure components (database, cache, logging)
- `middleware/`: Request/response middleware
- `models/`: Data models and schemas
- `services/`: Business logic services
