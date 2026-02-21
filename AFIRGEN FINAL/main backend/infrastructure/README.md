# Backend Optimization Infrastructure

This directory contains the infrastructure components for backend optimization, including Redis caching, Celery background task processing, Prometheus metrics, and structured logging.

## Components

### 1. Configuration (`config.py`)
Centralized configuration management for all infrastructure components. Configuration is loaded from environment variables with sensible defaults.

**Environment Variables:**
- `REDIS_HOST`: Redis server host (default: localhost)
- `REDIS_PORT`: Redis server port (default: 6379)
- `REDIS_DB`: Redis database number (default: 0)
- `REDIS_PASSWORD`: Redis password (optional)
- `REDIS_MAX_CONNECTIONS`: Maximum connection pool size (default: 50)
- `CELERY_BROKER_URL`: Celery broker URL (default: redis://localhost:6379/1)
- `CELERY_RESULT_BACKEND`: Celery result backend URL (default: redis://localhost:6379/2)
- `PROMETHEUS_ENABLED`: Enable Prometheus metrics (default: true)
- `PROMETHEUS_PORT`: Prometheus metrics port (default: 9090)
- `LOG_LEVEL`: Logging level (default: INFO)
- `LOG_FORMAT`: Log format - json or console (default: json)
- `SERVICE_NAME`: Service name for logs (default: afirgen-backend)

### 2. Redis Client (`redis_client.py`)
Redis connection management with connection pooling.

**Usage:**
```python
from infrastructure.redis_client import get_redis_client

redis_client = get_redis_client()
redis_client.set("key", "value", ex=3600)
value = redis_client.get("key")
```

### 3. Celery Application (`celery_app.py`)
Celery application setup for background task processing.

**Task Queues:**
- `email`: Email notifications (priority: 3)
- `reports`: Report generation (priority: 5)
- `analytics`: Analytics processing (priority: 2)
- `cleanup`: Cleanup jobs (priority: 1)

**Starting Celery Worker:**
```bash
celery -A infrastructure.celery_app worker --loglevel=info --queues=email,reports,analytics,cleanup
```

### 4. Structured Logging (`logging.py`)
Structured logging with JSON output and sensitive data redaction.

**Usage:**
```python
from infrastructure.logging import get_logger

logger = get_logger(__name__)
logger.info("User logged in", user_id="123", correlation_id="abc-def")

# With context
logger_with_context = logger.with_context(correlation_id="abc-def")
logger_with_context.info("Processing request")
```

**Sensitive Fields (automatically redacted):**
- password, token, api_key, secret, authorization
- credit_card, ssn, phone, email

### 5. Prometheus Metrics (`metrics.py`)
Metrics collection for monitoring and observability.

**Metrics Categories:**
- **API Metrics**: Request count, duration, in-progress requests
- **Database Metrics**: Query count, duration, connection pool stats
- **Cache Metrics**: Hit/miss rates, operation duration, memory usage
- **Model Server Metrics**: Request count, latency, availability
- **Background Task Metrics**: Queue size, processing duration, status
- **System Metrics**: CPU, memory, disk I/O, network I/O

**Usage:**
```python
from infrastructure.metrics import MetricsCollector, track_request_duration

# Track API request
with track_request_duration("/api/fir", "POST") as tracker:
    # Process request
    tracker.set_status(200)

# Record cache operation
MetricsCollector.record_cache_operation("get", hit=True, duration=0.005)

# Record database query
MetricsCollector.record_db_query_duration("SELECT", "fir_records", 0.025)
```

**Metrics Endpoint:**
Metrics are exposed at `/metrics` endpoint in Prometheus exposition format.

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Redis
```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or using docker-compose (see docker-compose.yaml)
docker-compose up -d redis
```

### 3. Configure Environment
Create a `.env` file with your configuration:
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 4. Start Celery Worker
```bash
celery -A infrastructure.celery_app worker --loglevel=info
```

### 5. Verify Setup
```python
from infrastructure.redis_client import RedisClient
from infrastructure.logging import get_logger

# Test Redis connection
assert RedisClient.ping(), "Redis connection failed"

# Test logging
logger = get_logger("test")
logger.info("Infrastructure setup complete")
```

## Testing

Run tests for infrastructure components:
```bash
pytest tests/test_infrastructure.py -v
```

## Monitoring

### Prometheus Metrics
Access metrics at: `http://localhost:8000/metrics`

### Celery Monitoring
Use Flower for Celery monitoring:
```bash
pip install flower
celery -A infrastructure.celery_app flower
```
Access Flower UI at: `http://localhost:5555`

### Redis Monitoring
Use Redis CLI to monitor:
```bash
redis-cli INFO
redis-cli MONITOR
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────┐
│   Redis Cache    │  │    Celery    │  │  Prometheus  │
│   (Port 6379)    │  │   Workers    │  │   Metrics    │
└──────────────────┘  └──────────────┘  └──────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Structured Logs  │
                    │   (JSON/stdout)  │
                    └──────────────────┘
```

## Troubleshooting

### Redis Connection Issues
- Verify Redis is running: `redis-cli ping`
- Check Redis host/port configuration
- Verify network connectivity

### Celery Worker Issues
- Check broker URL is correct
- Verify Redis is accessible
- Check worker logs for errors

### Metrics Not Appearing
- Verify Prometheus is enabled in config
- Check `/metrics` endpoint is accessible
- Verify metrics are being recorded

### Logging Issues
- Check LOG_LEVEL environment variable
- Verify LOG_FORMAT is set correctly
- Check stdout for log output
