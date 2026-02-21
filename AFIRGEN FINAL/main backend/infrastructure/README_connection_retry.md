# Connection Retry Logic

This module provides automatic retry logic for database and Redis connections to handle transient connection failures gracefully.

## Overview

The connection retry system implements exponential backoff with jitter to handle temporary network issues, connection timeouts, and other transient failures when connecting to external services.

**Validates: Requirements 6.4**

## Components

### DatabaseConnectionRetry

Handles retry logic for MySQL database connections.

**Features:**
- Exponential backoff with jitter
- Configurable retry attempts and delays
- Automatic error classification
- Detailed logging of connection attempts

**Default Configuration:**
- Max retries: 3
- Base delay: 1.0 seconds
- Max delay: 30.0 seconds
- Exponential base: 2.0

**Usage:**

```python
from infrastructure.connection_retry import DatabaseConnectionRetry

# Create retry handler
retry = DatabaseConnectionRetry(max_retries=3)

# Connect with retry
def connect():
    return mysql.connector.connect(**config)

connection = retry.connect_with_retry(connect, "mysql-main")

# Execute operation with retry
def query():
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

results = retry.execute_with_retry(query, "fetch users")
```

**Decorator Usage:**

```python
from infrastructure.connection_retry import with_db_retry

@with_db_retry(max_retries=3, base_delay=1.0)
def fetch_user(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()
```

### RedisConnectionRetry

Handles retry logic for Redis connections.

**Features:**
- Exponential backoff with jitter
- Redis-specific error handling
- Connection verification with ping
- Automatic reconnection on failure

**Default Configuration:**
- Max retries: 3
- Base delay: 0.5 seconds (faster than DB)
- Max delay: 10.0 seconds
- Exponential base: 2.0

**Usage:**

```python
from infrastructure.connection_retry import RedisConnectionRetry

# Create retry handler
retry = RedisConnectionRetry(max_retries=3)

# Connect with retry
def connect():
    return redis.Redis(host='localhost', port=6379)

client = retry.connect_with_retry(connect, "redis-cache")

# Execute operation with retry
def get_value():
    return client.get("my_key")

value = retry.execute_with_retry(get_value, "get my_key")
```

**Decorator Usage:**

```python
from infrastructure.connection_retry import with_redis_retry

@with_redis_retry(max_retries=3, base_delay=0.5)
def get_cached_value(key: str):
    client = get_redis_client()
    return client.get(key)
```

## Integration

### Database Pool Integration

The `DatabasePool` class automatically uses connection retry:

```python
from infrastructure.database import create_database_pool

config = {
    'pool_name': 'myapp_pool',
    'pool_size': 10,
    'host': 'localhost',
    'database': 'mydb',
    'user': 'user',
    'password': 'pass'
}

# Pool creation and connection acquisition automatically retry on failure
pool = create_database_pool(config)
connection = pool.get_connection()  # Retries automatically
```

### Redis Client Integration

The `RedisClient` class automatically uses connection retry:

```python
from infrastructure.redis_client import get_redis_client

# Client creation and operations automatically retry on failure
client = get_redis_client()  # Retries automatically
client.ping()  # Retries automatically
```

## Error Handling

### Retryable Errors

The following errors are automatically retried:

**Database:**
- `ConnectionError`
- `TimeoutError`
- `OSError`
- Database-specific connection errors

**Redis:**
- `redis.exceptions.ConnectionError`
- `redis.exceptions.TimeoutError`
- `redis.exceptions.BusyLoadingError`
- `ConnectionRefusedError`
- `ConnectionResetError`
- `BrokenPipeError`

### Non-Retryable Errors

The following errors are raised immediately without retry:
- `ValueError` (invalid configuration)
- `TypeError` (incorrect types)
- `KeyError` (missing configuration)
- Authentication errors
- Authorization errors

### Retry Behavior

1. **First attempt**: Immediate execution
2. **Retry 1**: Wait ~1 second (with jitter)
3. **Retry 2**: Wait ~2 seconds (with jitter)
4. **Retry 3**: Wait ~4 seconds (with jitter)
5. **Failure**: Raise the last exception

**Jitter:** Random factor (0.5-1.5x) added to delays to prevent thundering herd

## Configuration

### Environment Variables

Connection retry behavior can be configured via environment variables:

```bash
# Database retry configuration
DB_RETRY_MAX_ATTEMPTS=3
DB_RETRY_BASE_DELAY=1.0
DB_RETRY_MAX_DELAY=30.0

# Redis retry configuration
REDIS_RETRY_MAX_ATTEMPTS=3
REDIS_RETRY_BASE_DELAY=0.5
REDIS_RETRY_MAX_DELAY=10.0
```

### Programmatic Configuration

```python
from infrastructure.connection_retry import (
    get_db_connection_retry,
    get_redis_connection_retry
)

# Custom database retry configuration
db_retry = get_db_connection_retry(
    max_retries=5,
    base_delay=2.0,
    max_delay=60.0
)

# Custom Redis retry configuration
redis_retry = get_redis_connection_retry(
    max_retries=5,
    base_delay=1.0,
    max_delay=20.0
)
```

## Logging

Connection retry operations are logged at appropriate levels:

**INFO:** Successful connections and operations
```
INFO: Attempting to connect to mysql-main
INFO: Successfully connected to mysql-main
```

**ERROR:** Failed attempts and exhausted retries
```
ERROR: Failed to get database connection: Connection refused
ERROR: Failed to connect to mysql-main after 3 retries: Connection refused
```

## Best Practices

1. **Use appropriate retry counts**: 3 retries is usually sufficient for transient failures
2. **Configure timeouts**: Set reasonable socket timeouts to avoid long waits
3. **Monitor retry metrics**: Track retry attempts to identify persistent issues
4. **Use circuit breakers**: Combine with circuit breaker pattern for external services
5. **Log retry attempts**: Enable detailed logging to diagnose connection issues

## Testing

### Unit Tests

Test connection retry behavior:

```python
def test_database_connection_retry():
    retry = DatabaseConnectionRetry(max_retries=3)
    
    # Mock connection that fails twice then succeeds
    attempts = [0]
    def connect():
        attempts[0] += 1
        if attempts[0] < 3:
            raise ConnectionError("Connection failed")
        return MockConnection()
    
    conn = retry.connect_with_retry(connect)
    assert conn is not None
    assert attempts[0] == 3
```

### Integration Tests

Test with real connections:

```python
def test_redis_connection_with_retry():
    retry = RedisConnectionRetry(max_retries=3)
    
    def connect():
        return redis.Redis(host='localhost', port=6379)
    
    client = retry.connect_with_retry(connect)
    assert client.ping() is True
```

## Related Components

- **RetryHandler**: Generic retry mechanism with exponential backoff
- **ErrorClassifier**: Classifies exceptions as retryable or non-retryable
- **CircuitBreaker**: Prevents cascading failures for external services
- **DatabasePool**: Connection pool with metrics and retry
- **RedisClient**: Redis client with connection pooling and retry

## Requirements Validation

This module validates **Requirements 6.4**:

> WHEN database connection fails, THE Retry_Handler SHALL attempt reconnection before failing the request, with retry attempts following the configured retry strategy.

The implementation provides:
- ✅ Automatic retry on database connection failures
- ✅ Automatic retry on Redis connection failures
- ✅ Configurable retry strategy with exponential backoff
- ✅ Graceful failure handling after exhausting retries
- ✅ Detailed logging of connection attempts
- ✅ Integration with existing database and Redis clients
