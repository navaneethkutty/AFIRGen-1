# OpenTelemetry Tracing

This module provides distributed tracing capabilities using OpenTelemetry for the AFIRGen backend system.

## Overview

OpenTelemetry tracing enables:
- **Distributed tracing** across services and components
- **Performance monitoring** of critical operations
- **Request flow visualization** through the system
- **Integration with correlation IDs** for linking traces with logs
- **Automatic instrumentation** for FastAPI, HTTP clients, Redis, MySQL, and Celery

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         OpenTelemetry Instrumentation                │  │
│  │  • FastAPI (automatic request tracing)               │  │
│  │  • HTTPX (HTTP client tracing)                       │  │
│  │  • Redis (cache operation tracing)                   │  │
│  │  • MySQL (database query tracing)                    │  │
│  │  • Celery (background task tracing)                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   TracerProvider (SDK)                       │
│  • Span creation and management                             │
│  • Context propagation                                      │
│  • Attribute and event recording                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Span Processors                           │
│  • BatchSpanProcessor (buffering and batching)              │
│  • Exporters (OTLP, Console)                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Tracing Backends (Optional)                     │
│  • Jaeger                                                    │
│  • Tempo                                                     │
│  • Zipkin                                                    │
│  • Cloud providers (AWS X-Ray, GCP Trace, etc.)             │
└─────────────────────────────────────────────────────────────┘
```

## Setup

### Basic Setup

```python
from fastapi import FastAPI
from infrastructure.tracing import setup_tracing

app = FastAPI()

# Setup tracing with console export for development
tracing_manager = setup_tracing(
    app=app,
    service_name="afirgen-backend",
    service_version="1.0.0",
    enable_console_export=True  # For development
)
```

### Production Setup with OTLP Collector

```python
from infrastructure.tracing import setup_tracing

# Setup tracing with OTLP exporter for production
tracing_manager = setup_tracing(
    app=app,
    service_name="afirgen-backend",
    service_version="1.0.0",
    otlp_endpoint="http://localhost:4317",  # Jaeger, Tempo, etc.
    enable_console_export=False,
    instrument_libraries=True
)
```

## Usage

### Automatic Instrumentation

Once setup, the following are automatically traced:

1. **FastAPI Endpoints**: All HTTP requests are automatically traced
2. **HTTP Clients**: HTTPX requests to external services
3. **Redis Operations**: Cache get/set/delete operations
4. **MySQL Queries**: Database queries and transactions
5. **Celery Tasks**: Background task execution

### Manual Tracing for Critical Paths

#### Database Queries

```python
from infrastructure.tracing import trace_operation

async def get_fir_by_id(fir_id: str, correlation_id: str):
    with trace_operation(
        "database.get_fir",
        attributes={"fir_id": fir_id, "operation": "select"},
        correlation_id=correlation_id
    ) as span:
        result = await db.execute(query)
        
        # Add additional attributes
        if span:
            span.set_attribute("rows_returned", len(result))
        
        return result
```

#### Cache Operations

```python
from infrastructure.tracing import trace_operation

async def get_cached_fir(fir_id: str, correlation_id: str):
    with trace_operation(
        "cache.get_fir",
        attributes={"fir_id": fir_id, "cache_key": f"fir:record:{fir_id}"},
        correlation_id=correlation_id
    ) as span:
        result = await cache.get(f"fir:record:{fir_id}")
        
        # Record cache hit/miss
        if span:
            span.set_attribute("cache_hit", result is not None)
        
        return result
```

#### Model Server Calls

```python
from infrastructure.tracing import trace_operation

async def call_llm_model(prompt: str, correlation_id: str):
    with trace_operation(
        "model_server.llm_inference",
        attributes={
            "model": "llama-3",
            "prompt_length": len(prompt)
        },
        correlation_id=correlation_id
    ) as span:
        response = await model_client.generate(prompt)
        
        # Add response metadata
        if span:
            span.set_attribute("response_length", len(response))
            span.set_attribute("tokens_used", response.get("tokens", 0))
        
        return response
```

#### Background Tasks

```python
from infrastructure.tracing import trace_operation

async def process_fir_report(fir_id: str, correlation_id: str):
    with trace_operation(
        "background.generate_report",
        attributes={"fir_id": fir_id, "task_type": "report_generation"},
        correlation_id=correlation_id
    ) as span:
        # Generate report
        report = await generate_pdf_report(fir_id)
        
        # Add result metadata
        if span:
            span.set_attribute("report_size_bytes", len(report))
            span.add_event("report_generated", {"format": "pdf"})
        
        return report
```

### Adding Span Attributes and Events

```python
from infrastructure.tracing import add_trace_attributes, add_trace_event

# Add attributes to current span
add_trace_attributes({
    "user_id": "user_123",
    "fir_status": "completed",
    "processing_time_ms": 1234
})

# Add events to current span
add_trace_event("validation_started", {"validator": "schema_validator"})
add_trace_event("validation_completed", {"errors": 0})
```

### Getting Current Trace ID

```python
from infrastructure.tracing import get_current_trace_id

# Get trace ID for logging or debugging
trace_id = get_current_trace_id()
logger.info("Processing request", trace_id=trace_id)
```

## Integration with Correlation IDs

Traces automatically include correlation IDs when provided:

```python
from fastapi import Request
from infrastructure.tracing import trace_operation

@app.post("/api/fir")
async def create_fir(request: Request, data: FIRRequest):
    correlation_id = request.state.correlation_id
    
    with trace_operation(
        "fir.create",
        correlation_id=correlation_id
    ) as span:
        # Process FIR creation
        result = await fir_service.create(data)
        return result
```

This links traces with structured logs that also include the correlation ID.

## Trace Context Propagation

### Outgoing HTTP Requests

```python
from infrastructure.tracing import get_tracing_manager

# Inject trace context into HTTP headers
manager = get_tracing_manager()
headers = {}
manager.inject_context(headers)

# Make request with propagated context
response = await httpx_client.get(url, headers=headers)
```

### Incoming HTTP Requests

```python
from infrastructure.tracing import get_tracing_manager

# Extract trace context from incoming headers
manager = get_tracing_manager()
manager.extract_context(request.headers)
```

## Configuration

### Environment Variables

```bash
# OTLP endpoint for trace export
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Service name
OTEL_SERVICE_NAME=afirgen-backend

# Enable console export for debugging
OTEL_CONSOLE_EXPORT=true
```

### Tracing Manager Configuration

```python
tracing_manager = TracingManager(
    service_name="afirgen-backend",
    service_version="1.0.0",
    otlp_endpoint="http://localhost:4317",
    enable_console_export=False
)
```

## Span Attributes

### Standard Attributes

- `correlation_id`: Links trace with logs
- `service.name`: Service name
- `service.version`: Service version
- `http.method`: HTTP method (automatic)
- `http.url`: Request URL (automatic)
- `http.status_code`: Response status (automatic)

### Custom Attributes

Add domain-specific attributes:

```python
span.set_attribute("fir_id", fir_id)
span.set_attribute("user_id", user_id)
span.set_attribute("operation_type", "create")
span.set_attribute("cache_hit", True)
span.set_attribute("rows_affected", 5)
```

## Span Events

Events mark significant points in a span's lifecycle:

```python
span.add_event("cache_miss", {"key": cache_key})
span.add_event("database_query_started", {"query_type": "SELECT"})
span.add_event("validation_failed", {"errors": error_list})
span.add_event("retry_attempted", {"attempt": 2, "max_retries": 3})
```

## Error Handling

Exceptions are automatically recorded in spans:

```python
with trace_operation("risky_operation") as span:
    try:
        result = perform_operation()
    except Exception as e:
        # Exception is automatically recorded in span
        # Span status is set to ERROR
        raise
```

## Performance Considerations

1. **Sampling**: Configure sampling to reduce overhead in high-traffic scenarios
2. **Batch Processing**: Spans are batched before export to reduce network overhead
3. **Async Export**: Span export is asynchronous and doesn't block request processing
4. **Minimal Overhead**: OpenTelemetry is designed for production use with minimal performance impact

## Tracing Backends

### Jaeger

```bash
# Run Jaeger all-in-one
docker run -d --name jaeger \
  -p 4317:4317 \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest

# Configure endpoint
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

Access UI at: http://localhost:16686

### Grafana Tempo

```bash
# Run Tempo
docker run -d --name tempo \
  -p 4317:4317 \
  grafana/tempo:latest

# Configure endpoint
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

### AWS X-Ray

```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Use AWS X-Ray compatible exporter
exporter = OTLPSpanExporter(endpoint="xray-collector:4317")
provider.add_span_processor(BatchSpanProcessor(exporter))
```

## Best Practices

1. **Use Meaningful Span Names**: Use descriptive names like "database.get_fir" instead of "query"
2. **Add Relevant Attributes**: Include attributes that help with debugging and analysis
3. **Link with Correlation IDs**: Always pass correlation IDs to link traces with logs
4. **Trace Critical Paths**: Focus on database queries, cache operations, external API calls, and background tasks
5. **Don't Over-Trace**: Avoid tracing trivial operations that add noise
6. **Use Events for Milestones**: Mark important points in operation lifecycle
7. **Handle Errors Properly**: Let exceptions propagate to be recorded in spans

## Troubleshooting

### Traces Not Appearing

1. Check OTLP endpoint is reachable
2. Verify tracing is initialized before app starts
3. Enable console export to see traces locally
4. Check span processor is configured

### High Overhead

1. Reduce sampling rate
2. Increase batch size
3. Reduce number of attributes
4. Avoid tracing high-frequency operations

### Missing Context

1. Ensure context propagation is configured
2. Check correlation ID middleware is active
3. Verify trace context is injected in outgoing requests

## Testing

### Unit Tests

```python
from infrastructure.tracing import TracingManager

def test_tracing_manager():
    manager = TracingManager(
        service_name="test-service",
        enable_console_export=True
    )
    manager.setup()
    
    with manager.trace_operation("test_operation") as span:
        assert span is not None
        assert span.is_recording()
```

### Integration Tests

```python
from fastapi.testclient import TestClient

def test_traced_endpoint():
    client = TestClient(app)
    response = client.get("/api/fir/123")
    
    # Verify trace ID in response headers
    assert "traceparent" in response.headers
```

## Requirements

Requirement 7.7: The Logger SHALL integrate with distributed tracing systems using OpenTelemetry standards

This implementation satisfies the requirement by:
- Configuring OpenTelemetry SDK with trace providers
- Enabling automatic instrumentation for FastAPI and libraries
- Providing manual tracing for critical paths
- Integrating correlation IDs with traces
- Supporting trace context propagation
- Exporting traces to OTLP-compatible backends
