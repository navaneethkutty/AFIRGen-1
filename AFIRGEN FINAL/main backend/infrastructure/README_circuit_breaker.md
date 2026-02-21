# Circuit Breaker Pattern

## Overview

The circuit breaker pattern prevents cascading failures by temporarily blocking calls to failing services, allowing them to recover. This implementation provides a thread-safe circuit breaker with three states: CLOSED, OPEN, and HALF_OPEN.

**Validates: Requirements 6.3**

## Circuit States

### 1. CLOSED (Normal Operation)
- Requests pass through normally
- Failures are counted
- When `failure_threshold` consecutive failures occur, transitions to OPEN

### 2. OPEN (Service Failing)
- All requests are immediately rejected with `CircuitBreakerError`
- No calls are made to the failing service
- After `recovery_timeout` seconds, transitions to HALF_OPEN

### 3. HALF_OPEN (Testing Recovery)
- Allows `half_open_max_calls` test requests
- If all test calls succeed, transitions to CLOSED
- If any test call fails, transitions back to OPEN

## State Transition Diagram

```
         ┌─────────┐
         │ CLOSED  │ ◄──────────────┐
         └────┬────┘                │
              │                     │
    failure_threshold reached       │
              │                     │
              ▼                     │
         ┌─────────┐         all test calls
         │  OPEN   │         succeed
         └────┬────┘                │
              │                     │
    recovery_timeout elapsed        │
              │                     │
              ▼                     │
         ┌──────────┐               │
         │ HALF_OPEN├───────────────┘
         └──────────┘
              │
    any test call fails
              │
              ▼
         (back to OPEN)
```

## Usage

### Basic Usage

```python
from infrastructure.circuit_breaker import CircuitBreaker

# Create a circuit breaker
cb = CircuitBreaker(
    name="model_server",
    failure_threshold=5,      # Open after 5 consecutive failures
    recovery_timeout=60,      # Wait 60 seconds before testing recovery
    half_open_max_calls=3     # Allow 3 test calls in half-open state
)

# Use the circuit breaker
try:
    result = cb.call(call_model_server, data)
except CircuitBreakerError as e:
    print(f"Circuit breaker is open: {e}")
    # Handle gracefully (return cached data, default response, etc.)
```

### Decorator Usage

```python
from infrastructure.circuit_breaker import circuit_breaker

@circuit_breaker(
    name="external_api",
    failure_threshold=3,
    recovery_timeout=30
)
def call_external_api(url: str):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

# Use the decorated function
try:
    data = call_external_api("https://api.example.com/data")
except CircuitBreakerError:
    # Circuit is open, use fallback
    data = get_cached_data()
```

### Global Registry

Use the global registry to share circuit breakers across the application:

```python
from infrastructure.circuit_breaker import get_circuit_breaker

# Get or create a circuit breaker
cb = get_circuit_breaker("model_server", failure_threshold=5)

# Use it anywhere in the application
result = cb.call(call_model_server, data)

# Get all circuit breakers (useful for monitoring)
from infrastructure.circuit_breaker import get_all_circuit_breakers

breakers = get_all_circuit_breakers()
for name, cb in breakers.items():
    stats = cb.get_stats()
    print(f"{name}: {stats.state.value} - {stats.failure_count} failures")
```

## Configuration

### Parameters

- **name**: Identifier for the circuit breaker (used in logging/monitoring)
- **failure_threshold**: Number of consecutive failures before opening the circuit (default: 5)
- **recovery_timeout**: Seconds to wait before attempting recovery (default: 60)
- **half_open_max_calls**: Number of test calls allowed in half-open state (default: 3)
- **expected_exception**: Exception type to catch (default: Exception)

### Recommended Settings

#### Model Server Calls
```python
cb = CircuitBreaker(
    name="model_server",
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=60,      # Wait 1 minute
    half_open_max_calls=3     # Test with 3 calls
)
```

#### Database Connections
```python
cb = CircuitBreaker(
    name="database",
    failure_threshold=3,      # Open quickly for DB issues
    recovery_timeout=30,      # Shorter recovery time
    half_open_max_calls=2     # Test with 2 calls
)
```

#### External APIs
```python
cb = CircuitBreaker(
    name="external_api",
    failure_threshold=10,     # More tolerant of failures
    recovery_timeout=120,     # Wait longer before retry
    half_open_max_calls=5     # More test calls
)
```

## Monitoring

### Get Circuit State

```python
state = cb.get_state()
print(f"Circuit state: {state.value}")  # "closed", "open", or "half_open"
```

### Get Statistics

```python
stats = cb.get_stats()
print(f"State: {stats.state.value}")
print(f"Failure count: {stats.failure_count}")
print(f"Total calls: {stats.total_calls}")
print(f"Total failures: {stats.total_failures}")
print(f"Total successes: {stats.total_successes}")
print(f"Last failure: {stats.last_failure_time}")
```

### Export Statistics

```python
stats_dict = cb.get_stats().to_dict()
# Returns:
# {
#     "state": "closed",
#     "failure_count": 0,
#     "success_count": 0,
#     "last_failure_time": "2024-01-15T10:30:45",
#     "last_state_change": "2024-01-15T10:00:00",
#     "total_calls": 100,
#     "total_failures": 5,
#     "total_successes": 95
# }
```

## Administrative Operations

### Manual Reset

Force the circuit breaker to CLOSED state:

```python
cb.reset()
```

### Force Open

Force the circuit breaker to OPEN state (useful for maintenance):

```python
cb.force_open()
```

### Reset All Circuit Breakers

```python
from infrastructure.circuit_breaker import reset_all_circuit_breakers

reset_all_circuit_breakers()
```

## Integration with Model Server

Example integration with model server calls:

```python
from infrastructure.circuit_breaker import get_circuit_breaker
from infrastructure.retry_handler import RetryHandler

# Get circuit breaker for model server
model_cb = get_circuit_breaker(
    "model_server",
    failure_threshold=5,
    recovery_timeout=60
)

# Combine with retry handler
retry_handler = RetryHandler(max_retries=3)

def call_model_with_protection(data):
    """Call model server with circuit breaker and retry protection."""
    try:
        # Circuit breaker wraps the retry handler
        return model_cb.call(
            retry_handler.execute_with_retry,
            call_model_server,
            None,  # retryable_exceptions (use classifier)
            data
        )
    except CircuitBreakerError:
        # Circuit is open, return cached result or error
        return get_cached_model_result(data)
```

## Error Handling

### CircuitBreakerError

When the circuit is open, calls raise `CircuitBreakerError`:

```python
from infrastructure.circuit_breaker import CircuitBreakerError, CircuitState

try:
    result = cb.call(risky_operation)
except CircuitBreakerError as e:
    print(f"Circuit '{e.circuit_name}' is {e.state.value}")
    # Handle gracefully:
    # - Return cached data
    # - Return default value
    # - Queue for later processing
    # - Return error response to client
```

### Fallback Strategies

```python
def call_with_fallback(data):
    """Call with multiple fallback strategies."""
    try:
        # Try primary service
        return cb.call(primary_service, data)
    except CircuitBreakerError:
        # Circuit is open, try fallbacks
        try:
            # Fallback 1: Secondary service
            return secondary_service(data)
        except Exception:
            # Fallback 2: Cached data
            cached = get_cached_data(data)
            if cached:
                return cached
            # Fallback 3: Default response
            return get_default_response()
```

## Thread Safety

The circuit breaker is thread-safe and can be used in concurrent environments:

```python
import concurrent.futures

cb = get_circuit_breaker("api")

def make_request(i):
    return cb.call(api_call, i)

# Safe to use from multiple threads
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(make_request, range(100)))
```

## Testing

### Testing Circuit Breaker Behavior

```python
import pytest
from infrastructure.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerError

def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=1)
    
    def failing_func():
        raise Exception("Service unavailable")
    
    # First 3 calls should fail but pass through
    for i in range(3):
        with pytest.raises(Exception):
            cb.call(failing_func)
    
    # Circuit should now be open
    assert cb.get_state() == CircuitState.OPEN
    
    # Next call should raise CircuitBreakerError
    with pytest.raises(CircuitBreakerError):
        cb.call(failing_func)

def test_circuit_breaker_recovers():
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=1, half_open_max_calls=2)
    
    def sometimes_failing_func(should_fail):
        if should_fail:
            raise Exception("Failed")
        return "success"
    
    # Trigger circuit to open
    for i in range(2):
        with pytest.raises(Exception):
            cb.call(sometimes_failing_func, True)
    
    assert cb.get_state() == CircuitState.OPEN
    
    # Wait for recovery timeout
    time.sleep(1.1)
    
    # Next calls should succeed and close the circuit
    result1 = cb.call(sometimes_failing_func, False)
    result2 = cb.call(sometimes_failing_func, False)
    
    assert cb.get_state() == CircuitState.CLOSED
```

## Best Practices

1. **Use descriptive names**: Name circuit breakers after the service they protect
2. **Configure appropriately**: Adjust thresholds based on service characteristics
3. **Monitor state**: Track circuit breaker states in your monitoring system
4. **Implement fallbacks**: Always have a fallback strategy when circuit is open
5. **Log state changes**: Log when circuits open/close for debugging
6. **Test recovery**: Ensure your recovery timeout is appropriate for the service
7. **Combine with retries**: Use circuit breakers with retry handlers for robust error handling
8. **Share instances**: Use the global registry to share circuit breakers across the application

## Performance Considerations

- Circuit breakers add minimal overhead (microseconds per call)
- Thread-safe locking is efficient for high-concurrency scenarios
- State checks are fast (no I/O operations)
- Statistics tracking has negligible performance impact

## Troubleshooting

### Circuit Opens Too Frequently

- Increase `failure_threshold`
- Check if the underlying service is actually failing
- Verify network connectivity and timeouts

### Circuit Stays Open Too Long

- Decrease `recovery_timeout`
- Check if the service has actually recovered
- Consider manual reset if needed

### Circuit Doesn't Open When Expected

- Verify `failure_threshold` is set correctly
- Check that the correct exception type is being caught
- Ensure failures are consecutive (successes reset the counter)

## Related Components

- **RetryHandler**: Combines well with circuit breakers for robust error handling
- **ErrorClassifier**: Used to determine which errors should trigger the circuit breaker
- **Monitoring**: Circuit breaker states should be exposed in metrics
