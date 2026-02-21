# Retry Handler Component

## Overview

The Retry Handler component provides a reusable retry mechanism for handling transient failures with exponential backoff and jitter. It helps improve system reliability by automatically retrying failed operations that may succeed on subsequent attempts.

## Features

- **Exponential Backoff**: Delays between retries increase exponentially to avoid overwhelming failing services
- **Jitter**: Adds randomness to retry delays to prevent thundering herd problems
- **Configurable**: Supports customizable max retries, delays, and exponential base
- **Generic**: Works with any callable function
- **Decorator Support**: Can be used as a decorator for easy integration
- **Type-Safe**: Fully typed with Python type hints

## Installation

The retry handler is part of the infrastructure package and requires no additional dependencies beyond Python's standard library.

## Usage

### Basic Usage

```python
from infrastructure.retry_handler import RetryHandler

# Create a retry handler
handler = RetryHandler(
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True
)

# Execute a function with retry logic
def fetch_data():
    # Your code that might fail transiently
    response = requests.get("https://api.example.com/data")
    return response.json()

result = handler.execute_with_retry(
    fetch_data,
    retryable_exceptions=(ConnectionError, TimeoutError)
)
```

### Using the Decorator

```python
from infrastructure.retry_handler import retry

@retry(
    max_retries=3,
    base_delay=1.0,
    retryable_exceptions=(ConnectionError, TimeoutError)
)
def fetch_user_data(user_id: str):
    response = requests.get(f"https://api.example.com/users/{user_id}")
    return response.json()

# The function will automatically retry on ConnectionError or TimeoutError
user = fetch_user_data("12345")
```

### With Function Arguments

```python
from infrastructure.retry_handler import RetryHandler

handler = RetryHandler(max_retries=3, base_delay=0.5)

def save_to_database(record_id: str, data: dict):
    db.save(record_id, data)

# Pass arguments to the function
handler.execute_with_retry(
    save_to_database,
    (ConnectionError,),
    "record_123",
    {"name": "John", "age": 30}
)
```

### Predefined Exception Groups

```python
from infrastructure.retry_handler import RetryHandler, NETWORK_EXCEPTIONS

handler = RetryHandler(max_retries=3)

# Use predefined network exceptions
result = handler.execute_with_retry(
    my_network_call,
    NETWORK_EXCEPTIONS
)
```

## Configuration

### Parameters

- **max_retries** (int, default: 3): Maximum number of retry attempts
- **base_delay** (float, default: 1.0): Base delay in seconds for the first retry
- **max_delay** (float, default: 60.0): Maximum delay in seconds between retries
- **exponential_base** (float, default: 2.0): Base for exponential backoff calculation
- **jitter** (bool, default: True): Whether to add jitter to prevent thundering herd

### Delay Calculation

The delay between retries is calculated using exponential backoff:

```
delay = base_delay * (exponential_base ^ attempt)
```

With jitter enabled, the final delay is:

```
final_delay = delay * random(0.5, 1.5)
```

The delay is capped at `max_delay`.

#### Example Delays

With `base_delay=1.0`, `exponential_base=2.0`, and no jitter:

- Attempt 0 (first retry): 1.0 seconds
- Attempt 1 (second retry): 2.0 seconds
- Attempt 2 (third retry): 4.0 seconds
- Attempt 3 (fourth retry): 8.0 seconds

With jitter enabled, each delay is multiplied by a random factor between 0.5 and 1.5.

## Exception Handling

### Retryable vs Non-Retryable Exceptions

The retry handler distinguishes between retryable and non-retryable exceptions:

- **Retryable exceptions**: Transient failures that may succeed on retry (e.g., network timeouts, temporary service unavailability)
- **Non-retryable exceptions**: Permanent failures that won't succeed on retry (e.g., validation errors, authentication failures)

Only exceptions specified in the `retryable_exceptions` tuple will trigger retries. All other exceptions are raised immediately.

### Common Retryable Exceptions

```python
# Network-related
NETWORK_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

# Database-related (example)
DATABASE_EXCEPTIONS = (
    pymysql.err.OperationalError,
    pymysql.err.InterfaceError,
)

# Redis-related (example)
REDIS_EXCEPTIONS = (
    redis.exceptions.ConnectionError,
    redis.exceptions.TimeoutError,
)
```

## Best Practices

### 1. Choose Appropriate Retryable Exceptions

Only retry on transient failures:

```python
# Good: Retry on network errors
handler.execute_with_retry(
    api_call,
    (ConnectionError, TimeoutError)
)

# Bad: Don't retry on validation errors
# These won't succeed on retry
handler.execute_with_retry(
    validate_input,
    (ValueError,)  # Don't do this!
)
```

### 2. Set Reasonable Max Retries

Too many retries can delay error reporting:

```python
# Good: 3-5 retries for most cases
handler = RetryHandler(max_retries=3)

# Avoid: Too many retries
handler = RetryHandler(max_retries=20)  # Probably too many
```

### 3. Use Jitter to Prevent Thundering Herd

Always enable jitter when multiple clients might retry simultaneously:

```python
# Good: Jitter enabled (default)
handler = RetryHandler(jitter=True)

# Only disable jitter if you have a specific reason
handler = RetryHandler(jitter=False)
```

### 4. Set Appropriate Delays

Balance between quick recovery and avoiding overwhelming the service:

```python
# Good: Reasonable delays
handler = RetryHandler(
    base_delay=1.0,
    max_delay=60.0
)

# Avoid: Too aggressive
handler = RetryHandler(
    base_delay=0.01,  # Too fast
    max_delay=0.1
)
```

### 5. Use Dependency Injection

For testability, use the factory function:

```python
from infrastructure.retry_handler import get_retry_handler

def my_service(retry_handler=None):
    if retry_handler is None:
        retry_handler = get_retry_handler()
    
    return retry_handler.execute_with_retry(
        my_operation,
        (ConnectionError,)
    )
```

## Integration Examples

### With Database Operations

```python
from infrastructure.retry_handler import retry
import pymysql

@retry(
    max_retries=3,
    base_delay=0.5,
    retryable_exceptions=(pymysql.err.OperationalError,)
)
def query_database(query: str):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(query)
    return cursor.fetchall()
```

### With Redis Operations

```python
from infrastructure.retry_handler import RetryHandler
from redis.exceptions import ConnectionError as RedisConnectionError

handler = RetryHandler(max_retries=3, base_delay=0.5)

def get_from_cache(key: str):
    return handler.execute_with_retry(
        lambda: redis_client.get(key),
        (RedisConnectionError,)
    )
```

### With External API Calls

```python
from infrastructure.retry_handler import retry
import requests

@retry(
    max_retries=3,
    base_delay=1.0,
    retryable_exceptions=(
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.HTTPError
    )
)
def call_external_api(endpoint: str):
    response = requests.get(endpoint, timeout=10)
    response.raise_for_status()
    return response.json()
```

### With Model Server Calls

```python
from infrastructure.retry_handler import RetryHandler

handler = RetryHandler(
    max_retries=3,
    base_delay=2.0,
    max_delay=30.0
)

def call_llm_model(prompt: str):
    return handler.execute_with_retry(
        lambda: model_server.generate(prompt),
        (ConnectionError, TimeoutError)
    )
```

## Testing

The retry handler includes comprehensive unit tests covering:

- Initialization and validation
- Exponential backoff calculation
- Jitter application
- Retry logic with various exception types
- Max retries enforcement
- Decorator functionality
- Edge cases

Run tests with:

```bash
pytest test_retry_handler.py -v
```

## Performance Considerations

### Memory Usage

The retry handler has minimal memory overhead:
- No state is stored between retries
- Each retry attempt is independent
- No memory leaks from retry logic

### CPU Usage

CPU usage is minimal:
- Simple exponential calculation
- Random number generation for jitter
- No complex algorithms

### Latency

Total latency depends on configuration:

```python
# Example: 3 retries with base_delay=1.0, exponential_base=2.0
# Total delay: 1.0 + 2.0 + 4.0 = 7.0 seconds (without jitter)
# With jitter: 3.5 - 10.5 seconds (0.5x to 1.5x each delay)
```

## Troubleshooting

### Issue: Retries Not Happening

**Cause**: Exception type not in retryable_exceptions tuple

**Solution**: Add the exception type to retryable_exceptions:

```python
# Before
handler.execute_with_retry(func, (ConnectionError,))

# After
handler.execute_with_retry(func, (ConnectionError, TimeoutError))
```

### Issue: Too Many Retries

**Cause**: max_retries set too high

**Solution**: Reduce max_retries:

```python
# Before
handler = RetryHandler(max_retries=10)

# After
handler = RetryHandler(max_retries=3)
```

### Issue: Delays Too Long

**Cause**: exponential_base or max_delay too high

**Solution**: Adjust configuration:

```python
# Before
handler = RetryHandler(exponential_base=3.0, max_delay=300.0)

# After
handler = RetryHandler(exponential_base=2.0, max_delay=60.0)
```

## Related Components

- **Circuit Breaker**: Use in combination with retry handler for better fault tolerance
- **Metrics Collector**: Track retry attempts and success rates
- **Structured Logger**: Log retry attempts for debugging

## Requirements Validation

This component validates:
- **Requirement 6.1**: Implement retry logic with exponential backoff for transient failures

## Future Enhancements

Potential improvements:
- Async/await support for asynchronous functions
- Retry budget tracking (limit total retry time)
- Callback hooks for retry events
- Integration with circuit breaker pattern
- Metrics collection for retry attempts
