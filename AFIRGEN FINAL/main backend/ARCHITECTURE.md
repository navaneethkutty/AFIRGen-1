# AFIRGen Backend Architecture

## Overview

The AFIRGen (AI-powered FIR Generation) backend is a high-performance, scalable system built with Python FastAPI. The architecture follows a layered design pattern with clear separation of concerns, dependency injection, and comprehensive observability features.

**Key Characteristics**:
- **Layered Architecture**: Clear separation between API, service, repository, and infrastructure layers
- **Async-First**: Built on FastAPI with async/await for high concurrency
- **Microservices-Ready**: Modular design with external AI model servers
- **Observable**: Structured logging, distributed tracing, and Prometheus metrics
- **Resilient**: Circuit breakers, retry mechanisms, and graceful degradation
- **Scalable**: Redis caching, connection pooling, and background job processing

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  (Web Apps, Mobile Apps, CLI Tools, External Systems)           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway / Load Balancer                 │
│                    (Nginx, AWS ALB, etc.)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Middleware Stack                       │  │
│  │  • Correlation ID Tracking                                │  │
│  │  • Request/Response Logging                               │  │
│  │  • Metrics Collection                                     │  │
│  │  • Compression (gzip)                                     │  │
│  │  • Rate Limiting                                          │  │
│  │  • Security Headers                                       │  │
│  │  • Authentication                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                      API Layer                            │  │
│  │  • Route Handlers (api/routes/)                           │  │
│  │  • Request Validation                                     │  │
│  │  • Response Formatting                                    │  │
│  │  • Dependency Injection                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Service Layer                          │  │
│  │  • Business Logic (services/)                             │  │
│  │  • Workflow Orchestration                                 │  │
│  │  • Transaction Management                                 │  │
│  │  • External Service Integration                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Repository Layer                         │  │
│  │  • Data Access (repositories/)                            │  │
│  │  • Query Optimization                                     │  │
│  │  • Cache Integration                                      │  │
│  │  • Database Abstraction                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   MySQL      │      │    Redis     │      │   Celery     │
│   Database   │      │    Cache     │      │   Workers    │
│              │      │              │      │              │
│ • FIR Data   │      │ • Sessions   │      │ • Email      │
│ • Sessions   │      │ • Query      │      │ • Reports    │
│ • Tasks      │      │   Results    │      │ • Analytics  │
└──────────────┘      │ • Task Queue │      └──────────────┘
                      └──────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  GGUF LLM    │      │  ASR/OCR     │      │  Prometheus  │
│  Model       │      │  Server      │      │  Metrics     │
│  Server      │      │              │      │              │
│              │      │ • Whisper    │      │ • Scraping   │
│ • Summary    │      │ • DOTS OCR   │      │ • Alerting   │
│ • Violations │      │              │      │              │
│ • Narrative  │      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
```

---

## Layered Architecture

### 1. API Layer (`api/`)

**Responsibility**: HTTP request handling, routing, and response formatting

**Components**:
- **Route Handlers** (`api/routes/`): Define API endpoints and HTTP methods
- **Dependencies** (`api/dependencies.py`): Dependency injection providers
- **Request/Response Models** (`models/dto/`): Pydantic schemas for validation

**Key Principles**:
- Thin layer - no business logic
- Delegates to service layer
- Handles HTTP-specific concerns (status codes, headers)
- Validates input using Pydantic models
- Injects dependencies (services, repositories)

**Example**:
```python
@router.post("/process", response_model=FIRResp)
async def process_endpoint(
    audio: Optional[UploadFile] = File(None),
    session_service: SessionService = Depends(get_session_service),
):
    # Validate input
    validate_file_upload(audio, ALLOWED_AUDIO_TYPES)
    
    # Delegate to service layer
    result = await session_service.process_input(audio=audio)
    return result
```

---

### 2. Service Layer (`services/`)

**Responsibility**: Business logic, workflow orchestration, and transaction management

**Components**:
- **SessionService**: Manages FIR generation workflow
- **FIRService**: FIR-specific business operations
- **ModelServerService**: AI model server integration with circuit breakers

**Key Principles**:
- Contains all business logic
- Orchestrates multiple repositories
- Manages transactions
- Handles external service calls with resilience patterns
- Independent of HTTP/API concerns

**Example**:
```python
class SessionService:
    def __init__(self, fir_repo: FIRRepository, cache: CacheManager):
        self.fir_repo = fir_repo
        self.cache = cache
    
    async def process_input(self, audio: UploadFile) -> FIRResp:
        # Business logic
        transcript = await self.transcribe_audio(audio)
        summary = await self.generate_summary(transcript)
        
        # Save to database and cache
        session = await self.fir_repo.create_session(...)
        await self.cache.set(f"session:{session.id}", session)
        
        return FIRResp(session_id=session.id, status="processing")
```

---

### 3. Repository Layer (`repositories/`)

**Responsibility**: Data access, query optimization, and cache integration

**Components**:
- **BaseRepository**: Abstract base with common CRUD operations
- **FIRRepository**: FIR-specific data access with caching
- **Query Optimizer**: Analyzes and optimizes database queries

**Key Principles**:
- Abstracts database implementation
- Integrates caching transparently
- Optimizes queries (indexes, selective columns, cursor pagination)
- Handles database-specific concerns
- Returns domain models, not raw database records

**Example**:
```python
class FIRRepository(BaseRepository):
    async def find_by_id(self, fir_id: str) -> Optional[FIR]:
        # Check cache first
        cached = await self.cache.get(f"fir:record:{fir_id}")
        if cached:
            return FIR(**cached)
        
        # Query database with optimized query
        query = "SELECT id, fir_number, status, created_at FROM fir_records WHERE id = %s"
        result = await self.db.fetch_one(query, [fir_id])
        
        if result:
            fir = FIR(**result)
            await self.cache.set(f"fir:record:{fir_id}", fir.dict(), ttl=3600)
            return fir
        
        return None
```

---

### 4. Infrastructure Layer (`infrastructure/`)

**Responsibility**: Cross-cutting concerns and external integrations

**Components**:
- **Database** (`database.py`): Connection pooling and query execution
- **Cache Manager** (`cache_manager.py`): Redis caching with TTL and invalidation
- **Retry Handler** (`retry_handler.py`): Exponential backoff retry logic
- **Circuit Breaker** (`circuit_breaker.py`): Failure detection and recovery
- **Structured Logger** (`logging.py`): JSON logging with correlation IDs
- **Metrics Collector** (`metrics.py`): Prometheus metrics collection
- **Tracing** (`tracing.py`): OpenTelemetry distributed tracing
- **Background Task Manager** (`background_task_manager.py`): Celery task queue

**Key Principles**:
- Reusable across layers
- Configuration-driven
- Observable (logging, metrics, tracing)
- Resilient (retries, circuit breakers)

---

## Data Flow

### FIR Generation Flow

```
1. Client Request
   │
   ▼
2. Middleware Stack
   │ • Generate correlation ID
   │ • Log request
   │ • Check rate limit
   │ • Authenticate
   ▼
3. API Layer (Route Handler)
   │ • Validate input
   │ • Inject dependencies
   ▼
4. Service Layer (SessionService)
   │ • Transcribe audio (ASR server)
   │ • Generate summary (LLM server)
   │ • Detect violations (LLM + KB)
   │ • Generate narrative (LLM server)
   ▼
5. Repository Layer (FIRRepository)
   │ • Check cache
   │ • Query database
   │ • Update cache
   ▼
6. Database/Cache
   │ • Store session data
   │ • Store FIR record
   ▼
7. Response
   │ • Format response
   │ • Log response
   │ • Record metrics
   ▼
8. Client Response
```

---

## Component Interactions

### Request Processing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    Incoming Request                          │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Correlation ID Middleware                       │
│  • Generate unique correlation ID                            │
│  • Add to request context                                    │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Metrics Middleware                              │
│  • Record request start time                                 │
│  • Track endpoint and method                                 │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Compression Middleware                          │
│  • Check Accept-Encoding header                              │
│  • Prepare for response compression                          │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Rate Limit Middleware                           │
│  • Check client request count                                │
│  • Return 429 if limit exceeded                              │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Authentication Middleware                       │
│  • Validate API key                                          │
│  • Return 401 if invalid                                     │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Route Handler (API Layer)                       │
│  • Validate request body/params                              │
│  • Inject dependencies                                       │
│  • Call service layer                                        │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Service Layer                                   │
│  • Execute business logic                                    │
│  • Call repositories                                         │
│  • Call external services                                    │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Repository Layer                                │
│  • Check cache                                               │
│  • Query database                                            │
│  • Update cache                                              │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Response Processing                             │
│  • Format response                                           │
│  • Compress if needed                                        │
│  • Add headers (correlation ID, cache, etc.)                 │
│  • Log response                                              │
│  • Record metrics                                            │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Client Response                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Caching Strategy

### Cache Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  • In-memory caching for hot data                            │
│  • Request-scoped caching                                    │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Redis Cache Layer                         │
│  • Distributed caching                                       │
│  • Session data                                              │
│  • Query results                                             │
│  • KB query results                                          │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Database Layer                            │
│  • Persistent storage                                        │
│  • Source of truth                                           │
└─────────────────────────────────────────────────────────────┘
```

### Cache Key Namespacing

```
{namespace}:{entity_type}:{identifier}

Examples:
- fir:record:FIR-2024-001234
- session:data:550e8400-e29b-41d4-a716-446655440000
- kb:query:hash_of_query_text
- violation:check:abc-def-ghi
- stats:dashboard:user_123
```

### Cache TTL Strategy

| Data Type | TTL | Invalidation Strategy |
|-----------|-----|----------------------|
| FIR Records | 1 hour | On update/delete |
| Session Data | 24 hours | On completion |
| KB Query Results | 2 hours | Time-based only |
| Violation Checks | 30 minutes | Time-based only |
| Dashboard Stats | 5 minutes | Time-based only |

---

## Database Design

### Schema Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    fir_records                               │
├─────────────────────────────────────────────────────────────┤
│ id (PK)                                                      │
│ fir_number (UNIQUE)                                          │
│ session_id                                                   │
│ user_id                                                      │
│ complaint_text (TEXT)                                        │
│ fir_content (TEXT)                                           │
│ violations_json (JSON)                                       │
│ status (ENUM)                                                │
│ created_at (TIMESTAMP)                                       │
│ finalized_at (TIMESTAMP)                                     │
│                                                              │
│ Indexes:                                                     │
│ • idx_fir_number (fir_number)                                │
│ • idx_user_id (user_id)                                      │
│ • idx_status (status)                                        │
│ • idx_user_created (user_id, created_at)                     │
│ • idx_status_created (status, created_at)                    │
│ • ft_complaint_text (FULLTEXT on complaint_text)             │
│ • ft_fir_content (FULLTEXT on fir_content)                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    sessions                                  │
├─────────────────────────────────────────────────────────────┤
│ session_id (PK)                                              │
│ status (ENUM)                                                │
│ current_step (VARCHAR)                                       │
│ data (JSON)                                                  │
│ created_at (TIMESTAMP)                                       │
│ updated_at (TIMESTAMP)                                       │
│                                                              │
│ Indexes:                                                     │
│ • idx_status (status)                                        │
│ • idx_created_at (created_at)                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    background_tasks                          │
├─────────────────────────────────────────────────────────────┤
│ task_id (PK)                                                 │
│ task_name (VARCHAR)                                          │
│ status (ENUM)                                                │
│ priority (INT)                                               │
│ params (JSON)                                                │
│ result (JSON)                                                │
│ error (TEXT)                                                 │
│ retry_count (INT)                                            │
│ created_at (TIMESTAMP)                                       │
│ started_at (TIMESTAMP)                                       │
│ completed_at (TIMESTAMP)                                     │
│                                                              │
│ Indexes:                                                     │
│ • idx_status (status)                                        │
│ • idx_priority (priority)                                    │
│ • idx_created_at (created_at)                                │
└─────────────────────────────────────────────────────────────┘
```

### Query Optimization

**Principles**:
1. **Selective Column Retrieval**: Avoid `SELECT *`, specify needed columns
2. **Index Usage**: All frequently queried columns have indexes
3. **Composite Indexes**: For multi-column WHERE clauses
4. **Covering Indexes**: Include all columns needed for query
5. **Cursor-Based Pagination**: For large result sets
6. **Database-Level Aggregation**: Use SQL aggregate functions

---

## Background Job Processing

### Celery Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  • Enqueues tasks to Redis                                   │
│  • Returns task ID immediately                               │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Redis (Message Broker)                    │
│  • Task queue                                                │
│  • Result backend                                            │
│  • Priority queues                                           │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Celery Workers                            │
│  • Process tasks asynchronously                              │
│  • Retry on failure                                          │
│  • Update task status                                        │
└─────────────────────────────────────────────────────────────┘
```

### Task Types

| Task | Priority | Retry | Timeout |
|------|----------|-------|---------|
| Email Notifications | Low | 3 | 60s |
| Report Generation | Medium | 3 | 300s |
| Analytics Processing | Low | 2 | 120s |
| Cleanup Jobs | Low | 1 | 600s |

---

## Observability

### Structured Logging

**Format**: JSON with correlation IDs

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "service": "afirgen-backend",
  "correlation_id": "abc-123-def-456",
  "endpoint": "/api/v1/process",
  "method": "POST",
  "user_id": "user_789",
  "duration_ms": 1234,
  "message": "FIR processing completed",
  "context": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "fir_number": "FIR-2024-001234"
  }
}
```

### Distributed Tracing

**OpenTelemetry Integration**:
- Trace context propagation across services
- Span creation for critical operations
- Trace sampling for performance
- Export to Jaeger/Zipkin

### Metrics Collection

**Prometheus Metrics**:
- **Counters**: Request counts, error counts
- **Histograms**: Response times, query durations
- **Gauges**: Active connections, cache size, queue depth

---

## Resilience Patterns

### Circuit Breaker

```
States:
┌─────────┐  Failures < Threshold  ┌─────────┐
│ CLOSED  │ ─────────────────────> │ CLOSED  │
└─────────┘                        └─────────┘
     │                                   │
     │ Failures >= Threshold             │
     ▼                                   │
┌─────────┐                              │
│  OPEN   │ <────────────────────────────┘
└─────────┘
     │
     │ After Recovery Timeout
     ▼
┌─────────┐  Success  ┌─────────┐
│ HALF-   │ ────────> │ CLOSED  │
│ OPEN    │           └─────────┘
└─────────┘
     │
     │ Failure
     ▼
┌─────────┐
│  OPEN   │
└─────────┘
```

### Retry Strategy

**Exponential Backoff**:
```
Delay = base_delay * (exponential_base ^ retry_count) + jitter

Example:
- Retry 1: 1s + jitter
- Retry 2: 2s + jitter
- Retry 3: 4s + jitter
- Max: 60s
```

### Error Classification

- **Retryable**: Network timeouts, temporary unavailability, rate limits
- **Non-retryable**: Validation errors, authentication failures, not found

---

## Security

### Authentication & Authorization

- **API Key Authentication**: X-API-Key header
- **Rate Limiting**: Per-client request limits
- **Input Validation**: Pydantic models and custom validators
- **SQL Injection Prevention**: Parameterized queries
- **XSS Prevention**: Input sanitization

### Security Headers

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

---

## Scalability

### Horizontal Scaling

- **Stateless API**: No server-side session state
- **Load Balancing**: Round-robin or least-connections
- **Shared Cache**: Redis for distributed caching
- **Database Connection Pooling**: Reuse connections across requests

### Vertical Scaling

- **Async I/O**: Non-blocking operations with asyncio
- **Connection Pooling**: Database and Redis connection pools
- **Worker Processes**: Multiple Celery workers
- **Resource Limits**: Configurable timeouts and limits

---

## Deployment Architecture

### Production Deployment

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer (AWS ALB)                   │
└─────────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  FastAPI     │  │  FastAPI     │  │  FastAPI     │
│  Instance 1  │  │  Instance 2  │  │  Instance 3  │
└──────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  MySQL RDS   │  │  Redis       │  │  Celery      │
│  (Primary)   │  │  ElastiCache │  │  Workers     │
│              │  │              │  │              │
│  MySQL RDS   │  │              │  │              │
│  (Replica)   │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API Framework** | FastAPI | Async web framework |
| **Language** | Python 3.11+ | Application code |
| **Database** | MySQL 8.0+ | Persistent storage |
| **Cache** | Redis 7.0+ | Distributed caching |
| **Task Queue** | Celery + Redis | Background jobs |
| **Logging** | structlog | Structured logging |
| **Tracing** | OpenTelemetry | Distributed tracing |
| **Metrics** | Prometheus | Metrics collection |
| **Validation** | Pydantic | Request/response validation |
| **Testing** | pytest + Hypothesis | Unit and property tests |
| **Type Checking** | mypy | Static type checking |

---

## Performance Characteristics

### Target Metrics

| Metric | Target | Current |
|--------|--------|---------|
| API Response Time (p95) | < 2000ms | ~1800ms |
| API Response Time (p99) | < 5000ms | ~4500ms |
| Cache Hit Rate | > 80% | ~85% |
| Database Query Time (p95) | < 100ms | ~80ms |
| Concurrent Requests | 50+ | 50 |
| FIR Generation Time (cached) | < 10s | ~8s |
| FIR Generation Time (uncached) | < 15s | ~12s |

---

## Future Enhancements

1. **GraphQL API**: Alternative to REST for flexible queries
2. **WebSocket Support**: Real-time updates for FIR generation progress
3. **Multi-tenancy**: Support for multiple organizations
4. **Advanced Analytics**: ML-based insights and predictions
5. **Audit Logging**: Comprehensive audit trail for compliance
6. **API Versioning**: Support for multiple API versions
7. **Auto-scaling**: Kubernetes-based auto-scaling
8. **CDN Integration**: Static asset caching and delivery

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [MySQL Documentation](https://dev.mysql.com/doc/)
