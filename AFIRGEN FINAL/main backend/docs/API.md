# AFIRGen Backend API Documentation

## Overview

The AFIRGen (AI-powered FIR Generation) backend provides a RESTful API for generating First Information Reports (FIRs) from audio, image, or text inputs. The system uses AI models for transcription, OCR, summarization, violation detection, and narrative generation.

**Base URL**: `http://localhost:8000`

**API Version**: v1

**API Prefix**: `/api/v1`

## Authentication

Currently, the API uses API key authentication for certain endpoints. Include the API key in the request headers:

```
X-API-Key: your-api-key-here
```

## Rate Limiting

- **Default Limit**: 100 requests per 60 seconds per client
- **Rate Limit Headers**: Response includes rate limit information
- **429 Response**: Returned when rate limit is exceeded

## Core Endpoints

### 1. Process Input (Start FIR Generation)

**Endpoint**: `POST /api/v1/process`

**Description**: Initiates FIR generation from audio, image, or text input. Only one input type should be provided per request.

**Request**:
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `audio` (file, optional): Audio file (WAV, MP3, M4A, OGG, FLAC)
  - `image` (file, optional): Image file (PNG, JPG, JPEG, WEBP)
  - `text` (string, optional): Text complaint (min 10 chars, max 10,000 chars)

**Validation Rules**:
- Exactly one input type must be provided
- Audio files: Max 50MB, allowed formats: WAV, MP3, M4A, OGG, FLAC
- Image files: Max 10MB, allowed formats: PNG, JPG, JPEG, WEBP
- Text: Min 10 characters, max 10,000 characters

**Response** (200 OK):
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Processing started",
  "current_step": "transcription",
  "created_at": "2024-01-15T10:30:45.123Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid input or validation failure
- `413 Payload Too Large`: File or text exceeds size limits
- `500 Internal Server Error`: Processing error

**Example Request (cURL)**:
```bash
# Audio input
curl -X POST http://localhost:8000/api/v1/process \
  -F "audio=@complaint.mp3" \
  -H "X-API-Key: your-api-key"

# Text input
curl -X POST http://localhost:8000/api/v1/process \
  -F "text=My complaint is about a theft incident..." \
  -H "X-API-Key: your-api-key"
```

---

### 2. Validate Step

**Endpoint**: `POST /api/v1/validate`

**Description**: Validates and approves/rejects a processing step (summary, violations, or narrative). The system progresses through validation steps sequentially.

**Request**:
- **Content-Type**: `application/json`
- **Body**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "approved": true,
  "user_input": "Optional feedback or corrections"
}
```

**Fields**:
- `session_id` (string, required): Session identifier from `/process` response
- `approved` (boolean, required): Whether to approve the current step
- `user_input` (string, optional): User feedback for regeneration (max 5,000 chars)

**Response** (200 OK):
```json
{
  "status": "success",
  "next_step": "violations",
  "message": "Summary approved, proceeding to violation detection",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Validation Steps Flow**:
1. **summary**: Review and approve the generated summary
2. **violations**: Review detected IPC violations
3. **narrative**: Review the final FIR narrative
4. **complete**: FIR generation complete, ready for authentication

**Error Responses**:
- `400 Bad Request`: Invalid session ID or validation state
- `404 Not Found`: Session not found
- `500 Internal Server Error`: Validation processing error

**Example Request (cURL)**:
```bash
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "approved": true
  }'
```

---

### 3. Get Session Status

**Endpoint**: `GET /api/v1/session/{session_id}/status`

**Description**: Retrieves the current status and progress of a FIR generation session.

**Path Parameters**:
- `session_id` (string, required): Session identifier

**Response** (200 OK):
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "awaiting_validation",
  "current_step": "summary",
  "created_at": "2024-01-15T10:30:45.123Z",
  "updated_at": "2024-01-15T10:31:12.456Z",
  "data": {
    "transcript": "My complaint is about...",
    "summary": "Brief summary of the complaint...",
    "violations": [],
    "narrative": null
  },
  "validation_history": [
    {
      "step": "summary",
      "timestamp": "2024-01-15T10:31:00.000Z",
      "approved": true
    }
  ]
}
```

**Status Values**:
- `processing`: Initial processing in progress
- `awaiting_validation`: Waiting for user validation
- `generating`: Generating next step
- `complete`: FIR generation complete
- `error`: Processing error occurred

**Error Responses**:
- `400 Bad Request`: Invalid session ID format
- `404 Not Found`: Session not found
- `500 Internal Server Error`: Status retrieval error

**Example Request (cURL)**:
```bash
curl -X GET http://localhost:8000/api/v1/session/550e8400-e29b-41d4-a716-446655440000/status \
  -H "X-API-Key: your-api-key"
```

---

### 4. Regenerate Step

**Endpoint**: `POST /api/v1/regenerate/{session_id}`

**Description**: Regenerates a specific validation step with optional user feedback.

**Path Parameters**:
- `session_id` (string, required): Session identifier

**Query Parameters**:
- `step` (string, required): Step to regenerate (`summary`, `violations`, `narrative`)
- `user_input` (string, optional): User feedback for regeneration (max 5,000 chars)

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Summary regenerated successfully",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "regenerated_content": {
    "summary": "Updated summary based on user feedback..."
  }
}
```

**Error Responses**:
- `400 Bad Request`: Invalid session ID or step
- `404 Not Found`: Session not found
- `500 Internal Server Error`: Regeneration error

**Example Request (cURL)**:
```bash
curl -X POST "http://localhost:8000/api/v1/regenerate/550e8400-e29b-41d4-a716-446655440000?step=summary&user_input=Please%20include%20more%20details" \
  -H "X-API-Key: your-api-key"
```

---

### 5. Authenticate FIR

**Endpoint**: `POST /api/v1/authenticate`

**Description**: Authenticates and finalizes a completed FIR, making it official and immutable.

**Request**:
- **Content-Type**: `application/json`
- **Body**:
```json
{
  "fir_number": "FIR-2024-001234",
  "auth_key": "authentication-key-from-session"
}
```

**Fields**:
- `fir_number` (string, required): FIR number to authenticate
- `auth_key` (string, required): Authentication key provided during FIR generation

**Response** (200 OK):
```json
{
  "status": "authenticated",
  "fir_number": "FIR-2024-001234",
  "finalized_at": "2024-01-15T10:35:00.000Z",
  "message": "FIR authenticated and finalized successfully"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid FIR number or auth key
- `401 Unauthorized`: Authentication failed
- `404 Not Found`: FIR not found
- `500 Internal Server Error`: Authentication error

**Example Request (cURL)**:
```bash
curl -X POST http://localhost:8000/api/v1/authenticate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "fir_number": "FIR-2024-001234",
    "auth_key": "auth-key-here"
  }'
```

---

### 6. Get FIR Status

**Endpoint**: `GET /api/v1/fir/{fir_number}`

**Description**: Retrieves the status and metadata of a finalized FIR.

**Path Parameters**:
- `fir_number` (string, required): FIR number

**Response** (200 OK):
```json
{
  "fir_number": "FIR-2024-001234",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "finalized",
  "created_at": "2024-01-15T10:30:45.123Z",
  "finalized_at": "2024-01-15T10:35:00.000Z",
  "violations_count": 3
}
```

**Error Responses**:
- `400 Bad Request`: Invalid FIR number format
- `404 Not Found`: FIR not found
- `500 Internal Server Error`: Retrieval error

**Example Request (cURL)**:
```bash
curl -X GET http://localhost:8000/api/v1/fir/FIR-2024-001234 \
  -H "X-API-Key: your-api-key"
```

---

### 7. Get FIR Content

**Endpoint**: `GET /api/v1/fir/{fir_number}/content`

**Description**: Retrieves the complete content of a finalized FIR including narrative and violations.

**Path Parameters**:
- `fir_number` (string, required): FIR number

**Response** (200 OK):
```json
{
  "fir_number": "FIR-2024-001234",
  "complaint_text": "Original complaint text...",
  "summary": "Brief summary...",
  "violations": [
    {
      "section": "IPC 379",
      "description": "Theft",
      "reference": "Whoever intends to take dishonestly..."
    }
  ],
  "narrative": "Complete FIR narrative...",
  "created_at": "2024-01-15T10:30:45.123Z",
  "finalized_at": "2024-01-15T10:35:00.000Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid FIR number format
- `404 Not Found`: FIR not found
- `500 Internal Server Error`: Retrieval error

**Example Request (cURL)**:
```bash
curl -X GET http://localhost:8000/api/v1/fir/FIR-2024-001234/content \
  -H "X-API-Key: your-api-key"
```

---

## Monitoring & Health Endpoints

### 8. Health Check

**Endpoint**: `GET /health`

**Description**: Returns the health status of the API and its dependencies.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "version": "1.0.0",
  "dependencies": {
    "database": "healthy",
    "redis": "healthy",
    "model_server": "healthy",
    "asr_ocr_server": "healthy"
  }
}
```

**Example Request (cURL)**:
```bash
curl -X GET http://localhost:8000/health
```

---

### 9. Metrics

**Endpoint**: `GET /metrics`

**Description**: Returns application metrics in JSON format.

**Response** (200 OK):
```json
{
  "requests": {
    "total": 1234,
    "success": 1200,
    "errors": 34
  },
  "response_times": {
    "p50": 250,
    "p95": 1200,
    "p99": 2500
  },
  "cache": {
    "hit_rate": 0.85,
    "total_hits": 5000,
    "total_misses": 882
  },
  "database": {
    "connections": 10,
    "pool_size": 20,
    "query_count": 15000
  }
}
```

**Example Request (cURL)**:
```bash
curl -X GET http://localhost:8000/metrics
```

---

### 10. Prometheus Metrics

**Endpoint**: `GET /metrics/prometheus`

**Description**: Returns metrics in Prometheus exposition format for scraping.

**Response** (200 OK):
```
# HELP api_requests_total Total API requests
# TYPE api_requests_total counter
api_requests_total{endpoint="/api/v1/process",method="POST",status="200"} 1234

# HELP api_request_duration_seconds API request duration
# TYPE api_request_duration_seconds histogram
api_request_duration_seconds_bucket{endpoint="/api/v1/process",le="0.1"} 500
api_request_duration_seconds_bucket{endpoint="/api/v1/process",le="0.5"} 1000
...
```

**Example Request (cURL)**:
```bash
curl -X GET http://localhost:8000/metrics/prometheus
```

---

## Background Task Endpoints

### 11. Get Task Status

**Endpoint**: `GET /api/v1/tasks/{task_id}`

**Description**: Retrieves the status of a background task.

**Path Parameters**:
- `task_id` (string, required): Task identifier

**Response** (200 OK):
```json
{
  "task_id": "task-123-456",
  "task_name": "generate_report",
  "status": "completed",
  "created_at": "2024-01-15T10:30:00.000Z",
  "started_at": "2024-01-15T10:30:05.000Z",
  "completed_at": "2024-01-15T10:32:00.000Z",
  "result": {
    "report_url": "https://example.com/reports/123.pdf"
  },
  "error": null,
  "retry_count": 0
}
```

**Task Status Values**:
- `pending`: Task queued, not started
- `running`: Task currently executing
- `completed`: Task completed successfully
- `failed`: Task failed after retries
- `cancelled`: Task was cancelled

---

## Error Handling

### Standard Error Response Format

All error responses follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "correlation_id": "abc-123-def-456",
    "timestamp": "2024-01-15T10:30:45.123Z",
    "details": {
      "field": "Additional error context"
    }
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_INPUT` | 400 | Invalid request parameters or body |
| `VALIDATION_ERROR` | 400 | Input validation failed |
| `UNAUTHORIZED` | 401 | Authentication required or failed |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `PAYLOAD_TOO_LARGE` | 413 | Request payload exceeds limits |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

---

## Request/Response Headers

### Common Request Headers

- `Content-Type`: `application/json` or `multipart/form-data`
- `X-API-Key`: API authentication key
- `X-Request-ID`: Optional request tracking ID

### Common Response Headers

- `Content-Type`: `application/json`
- `X-Correlation-ID`: Request correlation ID for tracing
- `X-RateLimit-Limit`: Rate limit maximum
- `X-RateLimit-Remaining`: Remaining requests in window
- `X-RateLimit-Reset`: Time when rate limit resets (Unix timestamp)

---

## Pagination

List endpoints support cursor-based pagination:

**Query Parameters**:
- `cursor` (string, optional): Pagination cursor from previous response
- `limit` (integer, optional): Number of items per page (default: 20, max: 100)

**Response Format**:
```json
{
  "items": [...],
  "pagination": {
    "total_count": 1000,
    "page_size": 20,
    "next_cursor": "eyJpZCI6MTIzfQ==",
    "has_more": true
  }
}
```

---

## Field Filtering

Some endpoints support field filtering to reduce response size:

**Query Parameter**:
- `fields` (string, optional): Comma-separated list of fields to include

**Example**:
```bash
curl -X GET "http://localhost:8000/api/v1/fir/FIR-2024-001234?fields=fir_number,status,created_at"
```

---

## Compression

Responses larger than 1KB are automatically compressed with gzip when the client supports it.

**Request Header**:
```
Accept-Encoding: gzip
```

**Response Header**:
```
Content-Encoding: gzip
```

---

## Caching

Cacheable responses include appropriate cache headers:

**Response Headers**:
- `Cache-Control`: Cache directives (e.g., `public, max-age=3600`)
- `ETag`: Entity tag for conditional requests
- `Last-Modified`: Last modification timestamp

**Conditional Requests**:
```bash
curl -X GET http://localhost:8000/api/v1/fir/FIR-2024-001234 \
  -H "If-None-Match: \"etag-value\""
```

Returns `304 Not Modified` if content hasn't changed.

---

## Workflow Example

Complete FIR generation workflow:

```bash
# 1. Start processing with audio input
RESPONSE=$(curl -X POST http://localhost:8000/api/v1/process \
  -F "audio=@complaint.mp3" \
  -H "X-API-Key: your-api-key")

SESSION_ID=$(echo $RESPONSE | jq -r '.session_id')

# 2. Check session status
curl -X GET http://localhost:8000/api/v1/session/$SESSION_ID/status \
  -H "X-API-Key: your-api-key"

# 3. Validate summary step
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d "{\"session_id\": \"$SESSION_ID\", \"approved\": true}"

# 4. Validate violations step
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d "{\"session_id\": \"$SESSION_ID\", \"approved\": true}"

# 5. Validate narrative step
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d "{\"session_id\": \"$SESSION_ID\", \"approved\": true}"

# 6. Authenticate and finalize FIR
curl -X POST http://localhost:8000/api/v1/authenticate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d "{\"fir_number\": \"FIR-2024-001234\", \"auth_key\": \"auth-key\"}"

# 7. Retrieve finalized FIR
curl -X GET http://localhost:8000/api/v1/fir/FIR-2024-001234/content \
  -H "X-API-Key: your-api-key"
```

---

## OpenAPI/Swagger Documentation

Interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

These provide interactive testing capabilities and auto-generated documentation from the FastAPI application.

---

## Support & Contact

For API support, issues, or questions:
- **GitHub Issues**: [Repository Issues Page]
- **Email**: support@afirgen.example.com
- **Documentation**: [Full Documentation Site]

---

## Changelog

### Version 1.0.0 (2024-01-15)
- Initial API release
- Core FIR generation endpoints
- Validation workflow
- Background task processing
- Monitoring and metrics endpoints
- Comprehensive error handling
- Rate limiting and security features
