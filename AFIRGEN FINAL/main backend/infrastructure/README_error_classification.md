# Error Classification System

## Overview

The error classification system provides a comprehensive framework for distinguishing between retryable (transient) and non-retryable (permanent) errors in the AFIRGen backend system. This enables intelligent retry logic that automatically determines which errors should trigger retries and which should fail immediately.

**Validates: Requirements 6.5**

## Features

- **Automatic Error Classification**: Classifies exceptions into retryable, non-retryable, and critical categories
- **Inheritance-Based Classification**: Supports exception inheritance for flexible classification
- **Custom Exception Registration**: Allows registering custom exceptions into any category
- **HTTP Status Code Classification**: Provides helpers for classifying HTTP errors
- **Integration with Retry Handler**: Seamlessly integrates with the retry handler for automatic retry logic

## Error Categories

### 1. Retryable Errors (Transient)

Errors that may succeed on retry due to temporary conditions:

- **Network Errors**: `ConnectionError`, `TimeoutError`, `OSError`
- **HTTP Errors**: 408 (Timeout), 429 (Rate Limit), 502 (Bad Gateway), 503 (Service Unavailable), 504 (Gateway Timeout)
- **Server Errors**: Most 5xx errors (may be transient)

### 2. Non-Retryable Errors (Permanent)

Errors that will not succeed on retry due to permanent conditions:

- **Validation Errors**: `ValueError`, `TypeError`, `KeyError`, `AttributeError`
- **Logic Errors**: `AssertionError`, `NotImplementedError`
- **HTTP Errors**: 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found), 422 (Unprocessable Entity)

### 3. Critical Errors

Errors requiring immediate attention that should not be retried:

- **System Errors**: `MemoryError`, `SystemError`, `RecursionError`

## Usage

### Basic Classification

```python
from infrastructure.error_classification import (
    classify_error,
    is_retryable_error,
    is_non_retryable_error,
    is_critical_error,
    ErrorCategory
)

# Classify an exception
try:
    # Some operation
    pass
except Exception as e:
    category = classify_error(e)
    
    if category == ErrorCategory.RETRYABLE:
        print("This error can be retried")
    elif category == ErrorCategory.NON_RETRYABLE:
        print("This error should not be retried")
    elif category == ErrorCategory.CRITICAL:
        print("This is a critical error!")

# Quick checks
try:
    # Some operation
    pass
except Exception as e:
    if is_retryable_error(e):
        # Retry the operation
        pass
    else:
        # Handle the error
        pass
```

### Using ErrorClassifier

```python
from infrastructure.error_classification import ErrorClassifier

# Create a classifier instance
classifier = ErrorClassifier()

# Classify exceptions
try:
    # Some operation
    pass
except Exception as e:
    if classifier.is_retryable(e):
        print("Retryable error")
    elif classifier.is_non_retryable(e):
        print("Non-retryable error")
    elif classifier.is_critical(e):
        print("Critical error")
```

### Registering Custom Exceptions

```python
from infrastructure.error_classification import ErrorClassifier

classifier = ErrorClassifier()

# Define custom exceptions
class CustomNetworkError(Exception):
    """Custom network error that should be retried."""
    pass

class CustomValidationError(Exception):
    """Custom validation error that should not be retried."""
    pass

# Register as retryable
classifier.register_retryable(CustomNetworkError)

# Register as non-retryable
classifier.register_non_retryable(CustomValidationError)

# Now they will be classified correctly
assert classifier.is_retryable(CustomNetworkError("Failed"))
assert classifier.is_non_retryable(CustomValidationError("Invalid"))
```

### Integration with Retry Handler

The error classification system integrates seamlessly with the retry handler:

```python
from infrastructure.retry_handler import RetryHandler

# Automatic classification (recommended)
handler = RetryHandler(max_retries=3)

def my_operation():
    # This will automatically retry on retryable errors
    # and fail immediately on non-retryable errors
    pass

result = handler.execute_with_retry(my_operation)

# Manual classification (backward compatible)
result = handler.execute_with_retry(
    my_operation,
    retryable_exceptions=(ConnectionError, TimeoutError)
)

# Custom classifier
from infrastructure.error_classification import ErrorClassifier

classifier = ErrorClassifier()
classifier.register_retryable(CustomNetworkError)

handler = RetryHandler(max_retries=3, error_classifier=classifier)
result = handler.execute_with_retry(my_operation)
```

### HTTP Status Code Classification

```python
from infrastructure.error_classification import (
    classify_http_error,
    is_retryable_http_status,
    ErrorCategory
)

# Classify HTTP status codes
status_code = 503
category = classify_http_error(status_code)

if category == ErrorCategory.RETRYABLE:
    print("Service unavailable - retry later")

# Quick check
if is_retryable_http_status(429):
    print("Rate limited - retry with backoff")
```

## Classification Rules

### Inheritance-Based Classification

The classifier supports exception inheritance, meaning subclasses inherit their parent's classification:

```python
classifier = ErrorClassifier()

# ConnectionError is retryable by default
class CustomConnectionError(ConnectionError):
    pass

# Subclass is also retryable
assert classifier.is_retryable(CustomConnectionError("Failed"))
```

### Priority Order

When classifying exceptions, the classifier checks in this order:

1. **Critical** (highest priority)
2. **Retryable**
3. **Non-retryable**
4. **Unknown** (defaults to non-retryable for safety)

### Moving Between Categories

Registering an exception in a new category automatically removes it from other categories:

```python
classifier = ErrorClassifier()

class CustomError(Exception):
    pass

# Register as retryable
classifier.register_retryable(CustomError)
assert classifier.is_retryable(CustomError("Failed"))

# Re-register as non-retryable
classifier.register_non_retryable(CustomError)
assert classifier.is_non_retryable(CustomError("Failed"))
assert not classifier.is_retryable(CustomError("Failed"))
```

## Best Practices

### 1. Use Automatic Classification

Prefer automatic classification over manual exception lists:

```python
# Good: Automatic classification
handler = RetryHandler(max_retries=3)
result = handler.execute_with_retry(my_operation)

# Less ideal: Manual exception list
result = handler.execute_with_retry(
    my_operation,
    retryable_exceptions=(ConnectionError, TimeoutError)
)
```

### 2. Register Custom Exceptions Early

Register custom exceptions at application startup:

```python
from infrastructure.error_classification import ErrorClassifier

# At application startup
classifier = ErrorClassifier()

# Register all custom exceptions
classifier.register_retryable(
    CustomNetworkError,
    CustomTimeoutError,
    CustomRateLimitError
)

classifier.register_non_retryable(
    CustomValidationError,
    CustomAuthenticationError
)

# Use the classifier throughout the application
handler = RetryHandler(error_classifier=classifier)
```

### 3. Use Specific Exception Types

Define specific exception types for different error conditions:

```python
# Good: Specific exception types
class NetworkTimeoutError(Exception):
    """Network operation timed out."""
    pass

class ValidationError(Exception):
    """Input validation failed."""
    pass

# Register appropriately
classifier.register_retryable(NetworkTimeoutError)
classifier.register_non_retryable(ValidationError)

# Less ideal: Generic exceptions
raise Exception("Something went wrong")  # Hard to classify
```

### 4. Document Exception Classifications

Document which exceptions are retryable in your code:

```python
class CustomAPIError(Exception):
    """
    Custom API error.
    
    This exception is registered as retryable because API errors
    may be transient (rate limits, temporary unavailability).
    """
    pass
```

### 5. Test Error Classification

Always test that your custom exceptions are classified correctly:

```python
def test_custom_error_classification():
    classifier = ErrorClassifier()
    classifier.register_retryable(CustomNetworkError)
    
    assert classifier.is_retryable(CustomNetworkError("Failed"))
    assert not classifier.is_non_retryable(CustomNetworkError("Failed"))
```

## Examples

### Example 1: Database Operations

```python
from infrastructure.retry_handler import RetryHandler
from infrastructure.error_classification import ErrorClassifier

# Register database-specific exceptions
classifier = ErrorClassifier()

# Retryable: Connection issues
classifier.register_retryable(
    DatabaseConnectionError,
    DatabaseTimeoutError
)

# Non-retryable: Query errors
classifier.register_non_retryable(
    DatabaseQueryError,
    DatabaseConstraintError
)

# Use with retry handler
handler = RetryHandler(
    max_retries=3,
    base_delay=1.0,
    error_classifier=classifier
)

def execute_query(query):
    # Database operation
    pass

result = handler.execute_with_retry(execute_query, "SELECT * FROM users")
```

### Example 2: External API Calls

```python
from infrastructure.retry_handler import retry
from infrastructure.error_classification import ErrorClassifier

classifier = ErrorClassifier()

# Register API-specific exceptions
classifier.register_retryable(
    APIRateLimitError,
    APITimeoutError,
    APIServerError
)

classifier.register_non_retryable(
    APIAuthenticationError,
    APIValidationError,
    APINotFoundError
)

@retry(max_retries=3, base_delay=2.0, error_classifier=classifier)
def call_external_api(endpoint, data):
    # API call
    pass

result = call_external_api("/api/v1/resource", {"key": "value"})
```

### Example 3: HTTP Status Code Handling

```python
from infrastructure.error_classification import (
    classify_http_error,
    ErrorCategory,
    HTTPError
)
from infrastructure.retry_handler import RetryHandler

def make_http_request(url):
    response = requests.get(url)
    
    if response.status_code >= 400:
        # Classify the HTTP error
        category = classify_http_error(response.status_code)
        
        if category == ErrorCategory.RETRYABLE:
            raise HTTPError(
                f"HTTP {response.status_code}: {response.text}",
                response.status_code
            )
        else:
            # Non-retryable error - handle immediately
            raise ValueError(f"Request failed: {response.text}")
    
    return response.json()

# Use with retry handler
handler = RetryHandler(max_retries=3)
result = handler.execute_with_retry(make_http_request, "https://api.example.com")
```

## Architecture

### Class Hierarchy

```
ErrorClassifier
├── RETRYABLE_EXCEPTIONS (class variable)
├── NON_RETRYABLE_EXCEPTIONS (class variable)
├── CRITICAL_EXCEPTIONS (class variable)
├── _retryable (instance variable)
├── _non_retryable (instance variable)
├── _critical (instance variable)
└── Methods:
    ├── classify(exception) -> ErrorCategory
    ├── is_retryable(exception) -> bool
    ├── is_non_retryable(exception) -> bool
    ├── is_critical(exception) -> bool
    ├── register_retryable(*exception_types)
    ├── register_non_retryable(*exception_types)
    └── register_critical(*exception_types)
```

### Integration with Retry Handler

```
RetryHandler
├── error_classifier: ErrorClassifier
└── execute_with_retry(func, retryable_exceptions=None)
    ├── If retryable_exceptions is None:
    │   └── Use error_classifier.is_retryable(exception)
    └── Else:
        └── Use isinstance(exception, retryable_exceptions)
```

## Testing

The error classification system includes comprehensive tests:

- **Unit Tests**: `test_error_classification.py` (38 tests)
- **Integration Tests**: `test_retry_handler_with_classification.py` (23 tests)

Run tests:

```bash
# Test error classification
pytest test_error_classification.py -v

# Test retry handler integration
pytest test_retry_handler_with_classification.py -v

# Test all
pytest test_error_classification.py test_retry_handler_with_classification.py -v
```

## Performance Considerations

- **Classification is fast**: Uses set lookups and MRO traversal (O(n) where n is inheritance depth)
- **Minimal overhead**: Classification adds negligible overhead to retry logic
- **Reusable classifiers**: Create one classifier instance and reuse it across handlers

## Future Enhancements

Potential future improvements:

1. **Configuration-based classification**: Load exception classifications from config files
2. **Pattern-based classification**: Classify exceptions based on message patterns
3. **Metrics integration**: Track classification statistics
4. **Dynamic classification**: Adjust classifications based on runtime behavior

## Related Components

- **Retry Handler**: `infrastructure/retry_handler.py`
- **Circuit Breaker**: `infrastructure/circuit_breaker.py` (future)
- **Error Response Formatting**: `infrastructure/error_responses.py` (future)

## References

- Requirements: 6.5 (Error classification)
- Design Document: Section 6 (Error Handling and Retry Mechanisms)
- Property 29: Error classification correctness
