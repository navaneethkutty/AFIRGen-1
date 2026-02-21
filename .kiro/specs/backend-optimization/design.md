# Design Document: Backend Optimization

## Overview

This design document outlines the technical approach for optimizing the AFIRGen backend system. The optimization focuses on improving performance, scalability, and maintainability while maintaining system reliability. The design addresses ten key areas: database optimization, Redis caching, API response optimization, background job processing, resource monitoring, error handling, structured logging, code refactoring, performance testing, and documentation.

The current system handles 15 concurrent requests with 15-20 second average FIR generation times. Our optimization strategy aims to reduce this to under 10 seconds for cached requests and under 15 seconds for uncached requests, while improving system observability and maintainability.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer (FastAPI)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Compression  │  │  Correlation │  │   Rate       │     │
│  │ Middleware   │  │  ID Tracking │  │   Limiting   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ FIR Service  │  │ Violation    │  │ Background   │     │
│  │              │  │ Service      │  │ Task Service │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────┐
│   Cache Layer    │  │  Database    │  │   Model      │
│   (Redis)        │  │  Layer       │  │   Servers    │
│                  │  │  (MySQL)     │  │  (LLM/ASR)   │
└──────────────────┘  └──────────────┘  └──────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Monitoring & Observability Layer                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Prometheus   │  │ Structured   │  │ OpenTelemetry│     │
│  │ Metrics      │  │ Logging      │  │ Tracing      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Component Interactions

1. **API Layer**: Handles HTTP requests, applies middleware (compression, correlation tracking), and routes to service layer
2. **Service Layer**: Contains business logic, orchestrates database/cache/model server interactions
3. **Cache Layer**: Redis-based caching for frequently accessed data with TTL and invalidation strategies
4. **Database Layer**: Optimized MySQL queries with connection pooling, indexing, and query analysis
5. **Background Processor**: Celery-based task queue for asynchronous non-critical operations
6. **Monitoring Layer**: Collects metrics, logs, and traces for observability

## Components and Interfaces

### 1. Database Optimization Layer

**Query Optimizer**:
```python
class QueryOptimizer:
    def analyze_query_plan(query: str) -> QueryPlan
    def suggest_indexes(query_plan: QueryPlan) -> List[IndexSuggestion]
    def optimize_joins(query: str) -> str
```

**Optimized Repository Pattern**:
```python
class FIRRepository:
    def find_by_id(fir_id: str, fields: Optional[List[str]] = None) -> FIR
    def find_paginated(cursor: Optional[str], limit: int, filters: Dict) -> PaginatedResult[FIR]
    def bulk_insert(firs: List[FIR]) -> List[str]
    def execute_with_indexes(query: str, params: Dict) -> List[Dict]
```

**Index Strategy**:
- Primary indexes on `id`, `created_at`, `status` columns
- Composite indexes on frequently queried combinations: `(user_id, created_at)`, `(status, priority)`
- Full-text indexes on `description` and `violation_text` fields for search operations
- Covering indexes for common SELECT queries to avoid table lookups

### 2. Redis Cache Layer

**Cache Manager**:
```python
class CacheManager:
    def get(key: str, namespace: str = "default") -> Optional[Any]
    def set(key: str, value: Any, ttl: int, namespace: str = "default") -> bool
    def delete(key: str, namespace: str = "default") -> bool
    def invalidate_pattern(pattern: str, namespace: str = "default") -> int
    def get_or_fetch(key: str, fetch_fn: Callable, ttl: int) -> Any
```

**Caching Strategy**:
- **FIR Records**: Cache individual FIRs with 1-hour TTL, invalidate on update
- **Violation Checks**: Cache violation check results with 30-minute TTL
- **KB Queries**: Cache knowledge base query results with 2-hour TTL (already implemented, enhance)
- **User Sessions**: Cache user session data with 24-hour TTL
- **Aggregated Stats**: Cache dashboard statistics with 5-minute TTL

**Cache Key Namespacing**:
```
{namespace}:{entity_type}:{identifier}
Examples:
- fir:record:12345
- violation:check:abc-def-ghi
- kb:query:hash_of_query
- stats:dashboard:user_123
```

### 3. API Response Optimization

**Compression Middleware**:
```python
class CompressionMiddleware:
    def __init__(min_size: int = 1024, compression_level: int = 6)
    def should_compress(response: Response) -> bool
    def compress_response(response: Response) -> Response
```

**Pagination Handler**:
```python
class PaginationHandler:
    def paginate_cursor_based(
        query: Query,
        cursor: Optional[str],
        limit: int
    ) -> PaginatedResponse
    
    def encode_cursor(last_item: Dict) -> str
    def decode_cursor(cursor: str) -> Dict
```

**Field Filtering**:
```python
class FieldFilter:
    def filter_fields(data: Dict, fields: List[str]) -> Dict
    def validate_fields(fields: List[str], allowed: List[str]) -> bool
```

### 4. Background Job Processing

**Task Queue Architecture** (using Celery + Redis):
```python
class BackgroundTaskManager:
    def enqueue_task(task_name: str, params: Dict, priority: int = 5) -> str
    def get_task_status(task_id: str) -> TaskStatus
    def cancel_task(task_id: str) -> bool
```

**Task Types**:
- **Email Notifications**: Send FIR confirmation emails (low priority)
- **Report Generation**: Generate PDF reports asynchronously (medium priority)
- **Analytics Processing**: Update analytics dashboards (low priority)
- **Cleanup Jobs**: Archive old records, clear expired cache (low priority)

**Retry Strategy**:
```python
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    retry_backoff=True,
    retry_backoff_max=600,   # 10 minutes
    retry_jitter=True
)
def process_background_task(self, task_data: Dict):
    # Task implementation
    pass
```

### 5. Resource Monitoring System

**Metrics Collector**:
```python
class MetricsCollector:
    def record_request_duration(endpoint: str, duration: float, status: int)
    def record_db_query_duration(query_type: str, duration: float)
    def record_cache_operation(operation: str, hit: bool)
    def record_model_server_latency(server: str, duration: float)
    def get_system_metrics() -> SystemMetrics
```

**Metrics to Track**:
- **API Metrics**: Request count, response time (p50, p95, p99), error rate
- **Database Metrics**: Query count, query duration, connection pool utilization
- **Cache Metrics**: Hit rate, miss rate, eviction count, memory usage
- **Model Server Metrics**: Request count, latency, availability
- **System Metrics**: CPU usage, memory usage, disk I/O, network I/O

**Prometheus Integration**:
```python
from prometheus_client import Counter, Histogram, Gauge

request_count = Counter('api_requests_total', 'Total API requests', ['endpoint', 'method', 'status'])
request_duration = Histogram('api_request_duration_seconds', 'API request duration', ['endpoint'])
cache_hit_rate = Gauge('cache_hit_rate', 'Cache hit rate percentage')
db_pool_size = Gauge('db_connection_pool_size', 'Database connection pool size')
```

### 6. Error Handling and Retry Mechanisms

**Retry Handler**:
```python
class RetryHandler:
    def __init__(
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    )
    
    def execute_with_retry(
        func: Callable,
        retryable_exceptions: Tuple[Type[Exception]],
        *args,
        **kwargs
    ) -> Any
    
    def is_retryable(exception: Exception) -> bool
```

**Circuit Breaker Pattern**:
```python
class CircuitBreaker:
    def __init__(
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    )
    
    def call(func: Callable, *args, **kwargs) -> Any
    def get_state() -> CircuitState  # CLOSED, OPEN, HALF_OPEN
```

**Error Classification**:
- **Retryable**: Network timeouts, temporary database unavailability, rate limits
- **Non-retryable**: Validation errors, authentication failures, resource not found
- **Circuit breaker triggers**: Model server unavailability, database connection failures

### 7. Structured Logging System

**Logger Configuration**:
```python
class StructuredLogger:
    def __init__(service_name: str, log_level: str = "INFO")
    
    def log(
        level: str,
        message: str,
        correlation_id: Optional[str] = None,
        **context
    )
    
    def with_context(**context) -> StructuredLogger
    def redact_sensitive_fields(data: Dict) -> Dict
```

**Log Format** (JSON):
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "service": "afirgen-backend",
  "correlation_id": "abc-123-def-456",
  "endpoint": "/api/v1/fir",
  "method": "POST",
  "user_id": "user_789",
  "duration_ms": 1234,
  "message": "FIR created successfully",
  "context": {
    "fir_id": "fir_12345",
    "violation_count": 3
  }
}
```

**Sensitive Data Redaction**:
- Redact: passwords, tokens, API keys, PII (phone numbers, addresses)
- Mask: partial credit card numbers, partial IDs
- Hash: user identifiers when needed for correlation

### 8. Code Refactoring Structure

**Layered Architecture**:
```
src/
├── api/
│   ├── routes/          # API endpoint definitions
│   ├── middleware/      # Request/response middleware
│   └── dependencies.py  # Dependency injection
├── services/
│   ├── fir_service.py   # Business logic for FIR operations
│   ├── violation_service.py
│   └── background_service.py
├── repositories/
│   ├── fir_repository.py    # Database access layer
│   ├── cache_repository.py
│   └── base_repository.py
├── models/
│   ├── domain/          # Domain models
│   ├── dto/             # Data transfer objects
│   └── schemas.py       # Pydantic schemas
├── infrastructure/
│   ├── database.py      # Database connection
│   ├── cache.py         # Redis connection
│   ├── monitoring.py    # Metrics and logging
│   └── config.py        # Configuration management
└── utils/
    ├── retry.py         # Retry utilities
    ├── pagination.py    # Pagination helpers
    └── validators.py    # Validation utilities
```

**Dependency Injection Pattern**:
```python
from fastapi import Depends

def get_fir_repository(
    db: Database = Depends(get_database),
    cache: CacheManager = Depends(get_cache)
) -> FIRRepository:
    return FIRRepository(db, cache)

def get_fir_service(
    repo: FIRRepository = Depends(get_fir_repository),
    logger: StructuredLogger = Depends(get_logger)
) -> FIRService:
    return FIRService(repo, logger)

@router.post("/fir")
async def create_fir(
    request: CreateFIRRequest,
    service: FIRService = Depends(get_fir_service)
):
    return await service.create_fir(request)
```

## Data Models

### Cache Entry Model
```python
@dataclass
class CacheEntry:
    key: str
    value: Any
    ttl: int
    namespace: str
    created_at: datetime
    expires_at: datetime
```

### Paginated Response Model
```python
@dataclass
class PaginatedResponse[T]:
    items: List[T]
    total_count: int
    page_size: int
    next_cursor: Optional[str]
    has_more: bool
```

### Task Status Model
```python
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BackgroundTask:
    task_id: str
    task_name: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Any]
    error: Optional[str]
    retry_count: int
```

### Metrics Model
```python
@dataclass
class SystemMetrics:
    cpu_percent: float
    memory_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    timestamp: datetime
```

### Query Plan Model
```python
@dataclass
class QueryPlan:
    query: str
    execution_time_ms: float
    rows_examined: int
    rows_returned: int
    uses_index: bool
    index_names: List[str]
    suggestions: List[str]
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Database Optimization Properties

**Property 1: Query plan analysis identifies missing indexes**
*For any* SQL query executed through the Database_Layer, when the Query_Optimizer analyzes its execution plan, it should correctly identify whether indexes are missing based on full table scans or high row examination counts.
**Validates: Requirements 1.1**

**Property 2: Join queries utilize indexes**
*For any* query involving table joins, the execution plan should show index usage for join conditions, avoiding full table scans on joined tables.
**Validates: Requirements 1.3**

**Property 3: No SELECT * in generated queries**
*For any* database query generated by the system, the SQL should explicitly specify column names rather than using SELECT *.
**Validates: Requirements 1.4**

**Property 4: Cursor-based pagination for large result sets**
*For any* paginated query request, the Database_Layer should use cursor-based pagination (using a unique sortable column) rather than OFFSET-based pagination.
**Validates: Requirements 1.5**

**Property 5: Database-level aggregation**
*For any* aggregate operation (COUNT, SUM, AVG, MAX, MIN), the query should use SQL aggregate functions rather than fetching all rows and computing in application code.
**Validates: Requirements 1.6**

### Caching Properties

**Property 6: Cache entries have TTL values**
*For any* data stored in the Cache_Layer, the cache entry should have a TTL (time-to-live) value set, ensuring automatic expiration.
**Validates: Requirements 2.1**

**Property 7: Cache hit returns cached value**
*For any* cache key that exists and is not expired, requesting that key should return the cached value without querying the database.
**Validates: Requirements 2.2**

**Property 8: Cache miss triggers fetch and populate**
*For any* cache key that does not exist, requesting that key should trigger a database fetch and populate the cache with the result.
**Validates: Requirements 2.3**

**Property 9: Data modification invalidates cache**
*For any* data modification operation (create, update, delete), the corresponding cache entries should be invalidated or updated to maintain consistency.
**Validates: Requirements 2.4**

**Property 10: Cache failure fallback**
*For any* cache operation that fails (connection error, timeout), the system should fall back to database queries and continue serving requests without error.
**Validates: Requirements 2.5**

**Property 11: Cache key namespacing**
*For any* cache entry, the cache key should follow the namespacing pattern `{namespace}:{entity_type}:{identifier}` to prevent key collisions across different data types.
**Validates: Requirements 2.6**

### API Response Properties

**Property 12: Compression for large responses**
*For any* API response with body size larger than 1KB, the Response_Compressor should apply gzip compression and set the Content-Encoding header.
**Validates: Requirements 3.1**

**Property 13: Pagination support for list endpoints**
*For any* list endpoint request, the API should accept pagination parameters (cursor, limit) and return a paginated response.
**Validates: Requirements 3.2**

**Property 14: Pagination metadata completeness**
*For any* paginated API response, the response should include metadata fields: total_count, page_size, next_cursor, and has_more.
**Validates: Requirements 3.3**

**Property 15: Field filtering**
*For any* API request with a fields parameter, the response should include only the requested fields and exclude all others.
**Validates: Requirements 3.4**

**Property 16: Cache headers for cacheable responses**
*For any* cacheable API response (GET requests for immutable or slowly-changing data), the response should include appropriate Cache-Control headers.
**Validates: Requirements 3.6**

### Background Processing Properties

**Property 17: Async task queuing**
*For any* non-critical task submitted to the Background_Processor, the task should be added to the queue and return immediately without blocking, and the task should execute asynchronously.
**Validates: Requirements 4.1**

**Property 18: Task retry with exponential backoff**
*For any* background task that fails with a retryable error, the Retry_Handler should retry the task with exponentially increasing delays between attempts.
**Validates: Requirements 4.3**

**Property 19: Task status tracking**
*For any* background task that completes (successfully or with failure), the task status in the database should be updated to reflect the final state.
**Validates: Requirements 4.4**

**Property 20: Task prioritization**
*For any* set of queued background tasks with different priorities, higher priority tasks should be processed before lower priority tasks when workers are available.
**Validates: Requirements 4.5**

### Monitoring Properties

**Property 21: API request tracking**
*For any* API request, the Monitoring_System should record the request with endpoint, method, status code, and response time.
**Validates: Requirements 5.2**

**Property 22: Cache operation tracking**
*For any* cache operation (get, set, delete), the Monitoring_System should track whether it was a hit or miss and record the operation latency.
**Validates: Requirements 5.4**

**Property 23: Model server latency tracking**
*For any* request to a Model_Server, the Monitoring_System should record the server name, request latency, and success/failure status.
**Validates: Requirements 5.5**

**Property 24: Threshold alerting**
*For any* monitored metric that exceeds its configured threshold, the Monitoring_System should emit an alert with the metric name, current value, and threshold value.
**Validates: Requirements 5.6**

### Error Handling Properties

**Property 25: Retry with exponential backoff**
*For any* operation that fails with a transient error, the Retry_Handler should retry the operation with delays that increase exponentially (base_delay * exponential_base^retry_count).
**Validates: Requirements 6.1**

**Property 26: Error response after retry exhaustion**
*For any* operation that fails after exhausting all retry attempts, the system should return an error response with a descriptive message indicating the failure and retry count.
**Validates: Requirements 6.2**

**Property 27: Circuit breaker pattern**
*For any* external service (Model_Server) that experiences repeated failures exceeding the failure threshold, the circuit breaker should open and reject subsequent requests without attempting them until the recovery timeout expires.
**Validates: Requirements 6.3**

**Property 28: Connection retry**
*For any* database connection failure, the Retry_Handler should attempt to reconnect before failing the request, with retry attempts following the configured retry strategy.
**Validates: Requirements 6.4**

**Property 29: Error classification**
*For any* exception raised in the system, the error handler should correctly classify it as either retryable (network errors, timeouts) or non-retryable (validation errors, not found).
**Validates: Requirements 6.5**

**Property 30: Error logging completeness**
*For any* error that occurs, the log entry should include correlation_id, timestamp, error type, error message, and stack trace.
**Validates: Requirements 6.6**

### Logging Properties

**Property 31: Unique correlation ID generation**
*For any* incoming API request, the Logger should generate a unique correlation ID that is different from all other concurrent request correlation IDs.
**Validates: Requirements 7.1**

**Property 32: Correlation ID propagation**
*For any* request with a correlation ID, all log entries generated during that request's processing should include the same correlation ID.
**Validates: Requirements 7.2**

**Property 33: JSON log format**
*For any* log entry output by the Logger, the output should be valid JSON that can be parsed without errors.
**Validates: Requirements 7.3**

**Property 34: Required log fields**
*For any* log entry, the JSON should include the required fields: timestamp, level, service, and message.
**Validates: Requirements 7.4**

**Property 35: Sensitive data redaction**
*For any* log entry containing sensitive fields (password, token, api_key, credit_card), those fields should be redacted or masked in the log output.
**Validates: Requirements 7.5**

### Deployment Properties

**Property 36: Database migration reversibility**
*For any* database migration script, applying the migration and then reverting it should return the database schema to its original state (round-trip property).
**Validates: Requirements 10.4**

## Error Handling

### Error Categories

1. **Transient Errors** (retryable):
   - Network timeouts
   - Database connection failures
   - Model server temporary unavailability
   - Rate limit errors (429)
   - Service temporarily unavailable (503)

2. **Permanent Errors** (non-retryable):
   - Validation errors (400)
   - Authentication failures (401)
   - Authorization failures (403)
   - Resource not found (404)
   - Malformed requests (422)

3. **Critical Errors** (require immediate attention):
   - Database corruption
   - Configuration errors
   - Out of memory errors
   - Disk full errors

### Error Response Format

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "FIR with ID 'fir_12345' not found",
    "correlation_id": "abc-123-def-456",
    "timestamp": "2024-01-15T10:30:45.123Z",
    "details": {
      "resource_type": "FIR",
      "resource_id": "fir_12345"
    }
  }
}
```

### Retry Configuration

```python
RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay": 1.0,  # seconds
    "max_delay": 60.0,  # seconds
    "exponential_base": 2.0,
    "jitter": True  # Add random jitter to prevent thundering herd
}

CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 5,  # Open circuit after 5 consecutive failures
    "recovery_timeout": 60,  # Try again after 60 seconds
    "half_open_max_calls": 3  # Allow 3 test calls in half-open state
}
```

### Error Handling Flow

```
Request → Try Operation
            ↓
         Success? → Return Result
            ↓ No
         Classify Error
            ↓
    ┌──────┴──────┐
    ↓             ↓
Retryable?    Non-retryable
    ↓             ↓
Retry with    Return Error
Backoff       Response
    ↓
Max Retries?
    ↓ Yes
Return Error
Response
```

## Testing Strategy

### Dual Testing Approach

The testing strategy employs both unit tests and property-based tests to ensure comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property-based tests**: Verify universal properties across all inputs using randomized test data

Both approaches are complementary and necessary. Unit tests catch concrete bugs in specific scenarios, while property-based tests verify general correctness across a wide range of inputs.

### Property-Based Testing Configuration

We will use **Hypothesis** (Python's property-based testing library) for implementing property tests.

**Configuration**:
- Minimum 100 iterations per property test (due to randomization)
- Each property test must reference its design document property
- Tag format: `# Feature: backend-optimization, Property {number}: {property_text}`

**Example Property Test**:
```python
from hypothesis import given, strategies as st
import pytest

# Feature: backend-optimization, Property 11: Cache key namespacing
@given(
    namespace=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    entity_type=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    identifier=st.text(min_size=1, max_size=50)
)
@pytest.mark.property_test
def test_cache_key_namespacing(namespace, entity_type, identifier):
    """Property 11: For any cache entry, the key should follow namespacing pattern"""
    cache_manager = CacheManager()
    
    # Generate cache key
    key = cache_manager.generate_key(namespace, entity_type, identifier)
    
    # Verify format
    expected_pattern = f"{namespace}:{entity_type}:{identifier}"
    assert key == expected_pattern
    
    # Verify key components can be extracted
    parts = key.split(':')
    assert len(parts) == 3
    assert parts[0] == namespace
    assert parts[1] == entity_type
    assert parts[2] == identifier
```

### Unit Testing Focus

Unit tests should focus on:
- Specific examples demonstrating correct behavior
- Edge cases (empty inputs, boundary values, special characters)
- Error conditions (invalid inputs, service failures)
- Integration points between components

**Example Unit Test**:
```python
def test_cache_fallback_on_redis_failure():
    """Test that cache failures fall back to database"""
    # Arrange
    mock_redis = Mock(side_effect=ConnectionError("Redis unavailable"))
    mock_db = Mock(return_value={"id": "fir_123", "status": "pending"})
    cache_manager = CacheManager(redis=mock_redis, db=mock_db)
    
    # Act
    result = cache_manager.get_or_fetch("fir:record:123", fetch_fn=mock_db)
    
    # Assert
    assert result == {"id": "fir_123", "status": "pending"}
    mock_db.assert_called_once()
```

### Performance Testing

Performance tests should measure:
- API endpoint response times (p50, p95, p99)
- Database query execution times
- Cache hit rates and latency improvements
- Concurrent request handling capacity
- Memory and CPU usage under load

**Performance Test Configuration**:
```python
PERFORMANCE_THRESHOLDS = {
    "api_response_time_p95": 2000,  # ms
    "api_response_time_p99": 5000,  # ms
    "db_query_time_p95": 100,  # ms
    "cache_hit_rate_min": 0.80,  # 80%
    "concurrent_requests": 50,
    "error_rate_max": 0.01  # 1%
}
```

### Test Coverage Goals

- Unit test coverage: Minimum 80% code coverage
- Property test coverage: All 36 correctness properties implemented
- Integration test coverage: All API endpoints and critical paths
- Performance test coverage: All optimized components benchmarked

### Continuous Integration

All tests should run in CI/CD pipeline:
1. Unit tests (fast feedback)
2. Property-based tests (comprehensive validation)
3. Integration tests (component interaction)
4. Performance tests (regression detection)

Tests should fail the build if:
- Any test fails
- Code coverage drops below threshold
- Performance metrics exceed SLA thresholds
