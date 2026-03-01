# AFIRGen API Documentation

## Overview

The AFIRGen (Automated FIR Generation) API provides endpoints for processing complaints and generating First Information Reports (FIRs) using AWS managed AI services:

- **Amazon Transcribe**: Audio transcription in 10 Indian languages (Hindi, English, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi)
- **Amazon Textract**: Document OCR for extracting text from images
- **Amazon Bedrock (Claude 3 Sonnet)**: Legal text processing, narrative generation, and metadata extraction
- **Amazon Bedrock (Titan Embeddings)**: Vector embeddings for IPC section similarity search
- **Vector Database**: OpenSearch Serverless or Aurora PostgreSQL with pgvector for IPC section retrieval

**Base URL**: `https://api.afirgen.example.com` (replace with your actual domain)

**API Version**: 8.0.0

**Architecture**: AWS Bedrock-based serverless architecture (migrated from GPU-based GGUF models)

## Authentication

All API endpoints (except `/health`) require authentication using an API key.

### Authentication Methods

**Method 1: X-API-Key Header (Recommended)**
```http
X-API-Key: your-api-key-here
```

**Method 2: Authorization Bearer Token**
```http
Authorization: Bearer your-api-key-here
```

### JWT Token Structure (Optional)

For enhanced security, the API supports JWT tokens with the following payload structure:

```json
{
  "sub": "user-id-123",
  "role": "officer",
  "permissions": ["fir:create", "fir:read", "fir:finalize"],
  "iat": 1705315200,
  "exp": 1705401600
}
```

**Supported Roles:**
- `admin`: Full access to all endpoints
- `officer`: Create, read, and finalize FIRs
- `viewer`: Read-only access to FIRs
- `clerk`: Create FIRs only

**JWT Signing Algorithm**: HS256 or RS256

### Authentication Errors

| Status Code | Error | Description |
|-------------|-------|-------------|
| 401 | `missing_api_key` | API key not provided in request headers |
| 401 | `invalid_api_key` | API key is invalid or expired |
| 401 | `invalid_token` | JWT token is invalid or expired |
| 403 | `insufficient_permissions` | User lacks required permissions |
| 500 | `auth_not_configured` | Server authentication not properly configured |

## Rate Limiting

The API implements multi-tier rate limiting to ensure fair usage and system stability.

### Rate Limit Rules

| Tier | Requests per Minute | Requests per Hour | Requests per Day |
|------|---------------------|-------------------|------------------|
| Burst | 10 | - | - |
| Standard | 100 | 6,000 | 100,000 |
| Premium | 1,000 | 60,000 | 1,000,000 |

**Default Tier**: Standard (100 requests/minute)

### Rate Limit Headers

All successful responses include rate limit information:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705315260
X-RateLimit-Window: 60
```

**Header Descriptions:**
- `X-RateLimit-Limit`: Maximum requests allowed in the current window
- `X-RateLimit-Remaining`: Remaining requests in the current window
- `X-RateLimit-Reset`: Unix timestamp when the rate limit resets
- `X-RateLimit-Window`: Time window in seconds

### Rate Limit Exceeded Response

**Status Code**: `429 Too Many Requests`

```json
{
  "detail": "Rate limit exceeded. Maximum 100 requests per minute allowed. Please try again later.",
  "error": "too_many_requests"
}
```

**Headers**:
```http
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1705315260
X-RateLimit-Window: 60
```

### Rate Limiting Best Practices

1. **Implement Exponential Backoff**: When receiving 429 responses, wait progressively longer between retries
2. **Monitor Headers**: Track `X-RateLimit-Remaining` to avoid hitting limits
3. **Batch Requests**: Combine multiple operations when possible
4. **Cache Responses**: Cache FIR data to reduce redundant API calls
5. **Use Webhooks**: Consider webhook notifications instead of polling (if available)

---

## AWS Bedrock Integration

The API leverages AWS managed services for AI-powered processing:

### Amazon Transcribe

**Purpose**: Audio transcription in multiple Indian languages

**Supported Languages:**
- Hindi (hi-IN)
- English (en-IN)
- Tamil (ta-IN)
- Telugu (te-IN)
- Bengali (bn-IN)
- Marathi (mr-IN)
- Gujarati (gu-IN)
- Kannada (kn-IN)
- Malayalam (ml-IN)
- Punjabi (pa-IN)

**Features:**
- Automatic language detection
- Speaker identification
- Timestamp generation
- Retry logic with exponential backoff

**Performance:**
- Typical latency: 30-180 seconds for 5-minute audio
- Max file size: 25MB
- Supported formats: WAV, MP3, MPEG

### Amazon Textract

**Purpose**: Document text extraction and OCR

**Features:**
- Plain text extraction
- Form data extraction
- Table detection
- Handwriting recognition

**Performance:**
- Typical latency: 5-30 seconds per page
- Max file size: 25MB
- Supported formats: JPEG, PNG

### Amazon Bedrock (Claude 3 Sonnet)

**Purpose**: Legal text processing and FIR generation

**Model**: `anthropic.claude-3-sonnet-20240229-v1:0`

**Operations:**
1. **Formal Narrative Generation**
   - Converts raw complaint text to formal legal narrative
   - Max 3 sentences
   - Temperature: 0.3
   - Max tokens: 500

2. **Metadata Extraction**
   - Extracts structured data (incident type, date, location, parties)
   - Temperature: 0.1
   - Max tokens: 300

3. **FIR Generation with RAG**
   - Generates complete FIR using retrieved IPC sections
   - Temperature: 0.5
   - Max tokens: 2048

**Rate Limiting:**
- Max 10 concurrent Bedrock API calls (enforced by semaphore)
- Automatic retry with exponential backoff for throttling
- Circuit breaker protection (failure threshold: 5)

**Token Usage Tracking:**
- Input tokens and output tokens logged to CloudWatch
- Cost estimation based on token usage

### Amazon Bedrock (Titan Embeddings)

**Purpose**: Vector embeddings for IPC section similarity search

**Model**: `amazon.titan-embed-text-v1`

**Features:**
- 1536-dimensional embeddings
- Batch processing (25 texts per batch)
- Cosine similarity search

**Performance:**
- Typical latency: 100-500ms per embedding
- Batch latency: 1-3 seconds for 25 embeddings

### Vector Database

**Purpose**: Store and search IPC section embeddings

**Supported Implementations:**
1. **OpenSearch Serverless**
   - k-NN plugin with HNSW algorithm
   - Cosine similarity metric
   - Automatic scaling

2. **Aurora PostgreSQL with pgvector**
   - IVFFlat index
   - Cosine similarity operator
   - Connection pooling

**Search Performance:**
- Typical latency: 50-200ms for top-5 results
- Index size: ~500 IPC sections

---

## API Endpoints

### 1. Process Complaint

Start FIR processing with audio, image, or text input.

**Endpoint**: `POST /process`

**Content-Type**: `multipart/form-data` (for audio/image) or `application/json` (for text)

**Processing Pipeline:**
1. **Audio Input** → Amazon Transcribe → Text → Bedrock Processing
2. **Image Input** → Amazon Textract → Text → Bedrock Processing
3. **Text Input** → Bedrock Processing

**Bedrock Processing Steps:**
1. Generate formal legal narrative (Claude 3 Sonnet)
2. Extract structured metadata (Claude 3 Sonnet)
3. Generate query embedding (Titan Embeddings)
4. Search for relevant IPC sections (Vector DB)
5. Generate complete FIR with RAG (Claude 3 Sonnet)

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `audio` | File | No* | Audio file (WAV, MP3, MPEG) - max 25MB |
| `image` | File | No* | Image file (JPEG, PNG) - max 25MB |
| `text` | String | No* | Text complaint (10-50,000 characters) |

*Note: Exactly one input type must be provided.

#### Request Examples

**Text Input**:
```bash
curl -X POST https://api.afirgen.example.com/process \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I want to report a theft that occurred yesterday at Central Park. My mobile phone was stolen by two unknown persons around 3 PM."
  }'
```

**Audio Input**:
```bash
curl -X POST https://api.afirgen.example.com/process \
  -H "X-API-Key: your-api-key" \
  -F "audio=@complaint.mp3"
```

**Image Input**:
```bash
curl -X POST https://api.afirgen.example.com/process \
  -H "X-API-Key: your-api-key" \
  -F "image=@complaint_document.jpg"
```

#### Response Schema

**Status Code**: `200 OK`

```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "steps": ["asr_done"],
  "requires_validation": true,
  "current_step": "transcript_review",
  "content_for_validation": {
    "transcript": "I want to report a theft..."
  }
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | Boolean | Whether processing started successfully |
| `session_id` | String | Unique session identifier (UUID format) |
| `steps` | Array | Processing steps completed |
| `requires_validation` | Boolean | Whether user validation is required |
| `current_step` | String | Current validation step |
| `content_for_validation` | Object | Content to be validated by user |
| `error` | String | Error message (only if success=false) |

#### Error Responses

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | `no_input` | No input provided |
| 400 | `multiple_inputs` | Multiple input types provided |
| 400 | `text_too_short` | Text input less than 10 characters |
| 400 | `dangerous_content` | Input contains potentially dangerous content (XSS/injection) |
| 413 | `text_too_long` | Text input exceeds 50,000 characters |
| 413 | `file_too_large` | File exceeds 25MB limit |
| 415 | `unsupported_format` | Unsupported file format |
| 429 | `rate_limit_exceeded` | Too many requests |
| 500 | `processing_error` | Internal processing error |
| 500 | `transcribe_error` | Amazon Transcribe service error |
| 500 | `textract_error` | Amazon Textract service error |
| 500 | `bedrock_error` | Amazon Bedrock service error |
| 503 | `service_unavailable` | Circuit breaker open - service temporarily unavailable |
| 504 | `timeout` | Processing timeout |

---

### 2. Validate Step

Validate and approve processing steps in the FIR generation workflow.

**Endpoint**: `POST /validate`

**Content-Type**: `application/json`

**Bedrock Integration:**
- When `regenerate=true`, uses Claude 3 Sonnet to regenerate content with user feedback
- Incorporates user input into prompts for improved accuracy
- Implements retry logic for Bedrock API failures

#### Request Schema

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "approved": true,
  "user_input": "Additional context or corrections",
  "regenerate": false
}
```

#### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | String | Yes | Session ID from /process response (UUID format) |
| `approved` | Boolean | Yes | Whether to approve current step |
| `user_input` | String | No | Additional input or corrections (max 10,000 chars) |
| `regenerate` | Boolean | No | Whether to regenerate content (default: false) |

#### Request Example

```bash
curl -X POST https://api.afirgen.example.com/validate \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "approved": true,
    "user_input": "The incident occurred at 3 PM, not 2 PM"
  }'
```

#### Response Schema

**Status Code**: `200 OK`

```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_step": "summary_review",
  "content": {
    "summary": "Theft of mobile phone reported at Central Park at 3 PM by two unknown persons.",
    "original_transcript": "I want to report a theft..."
  },
  "message": "Summary generated. Please review and validate.",
  "requires_validation": true,
  "completed": false
}
```

#### Validation Steps

The validation workflow consists of the following steps:

1. **transcript_review** - Review transcribed/extracted text
2. **summary_review** - Review generated summary
3. **violations_review** - Review identified legal violations
4. **fir_narrative_review** - Review FIR narrative
5. **final_review** - Final FIR review before completion

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | Boolean | Whether validation succeeded |
| `session_id` | String | Session identifier |
| `current_step` | String | Current validation step |
| `content` | Object | Content for current step |
| `message` | String | User-friendly message |
| `requires_validation` | Boolean | Whether more validation is needed |
| `completed` | Boolean | Whether FIR generation is complete |

#### Error Responses

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | `invalid_session_id` | Invalid session ID format |
| 400 | `not_awaiting_validation` | Session not in validation state |
| 400 | `dangerous_content` | User input contains potentially dangerous content |
| 404 | `session_not_found` | Session not found or expired |
| 429 | `rate_limit_exceeded` | Too many requests |
| 500 | `validation_failed` | Internal validation error |
| 500 | `bedrock_error` | Amazon Bedrock service error |
| 503 | `service_unavailable` | Circuit breaker open |
| 504 | `processing_timeout` | Processing timeout - retry |

---

### 3. Get Session Status

Retrieve the current status of a processing session.

**Endpoint**: `GET /session/{session_id}/status`

**Path Parameters**:
- `session_id` (String, Required): Session UUID

#### Request Example

```bash
curl -X GET https://api.afirgen.example.com/session/550e8400-e29b-41d4-a716-446655440000/status \
  -H "X-API-Key: your-api-key"
```

#### Response Schema

**Status Code**: `200 OK`

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "awaiting_validation",
  "current_step": "summary_review",
  "awaiting_validation": true,
  "validation_history": [
    {
      "step": "transcript_review",
      "content": {...},
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "created_at": "2024-01-15T10:25:00Z",
  "last_activity": "2024-01-15T10:30:00Z"
}
```

#### Session Status Values

| Status | Description |
|--------|-------------|
| `processing` | Initial processing in progress |
| `awaiting_validation` | Waiting for user validation |
| `completed` | FIR generation completed |
| `expired` | Session expired (after 1 hour of inactivity) |
| `error` | Processing error occurred |

#### Error Responses

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | `invalid_session_id` | Invalid session ID format |
| 404 | `session_not_found` | Session not found or expired |

---

### 4. Regenerate Step

Regenerate content for a specific validation step with additional user input.

**Endpoint**: `POST /regenerate/{session_id}`

**Path Parameters**:
- `session_id` (String, Required): Session UUID

**Content-Type**: `application/json`

#### Request Schema

```json
{
  "step": "summary_review",
  "user_input": "Please include more details about the suspect's appearance"
}
```

#### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `step` | String | Yes | Validation step to regenerate |
| `user_input` | String | No | Additional context (max 10,000 chars) |

#### Valid Step Values

- `summary_review`
- `violations_review`
- `fir_narrative_review`

#### Request Example

```bash
curl -X POST https://api.afirgen.example.com/regenerate/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "step": "summary_review",
    "user_input": "Include suspect description"
  }'
```

#### Response Schema

**Status Code**: `200 OK`

```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "step": "summary_review",
  "content": {
    "summary": "Updated summary with additional details..."
  },
  "message": "Content regenerated for summary_review"
}
```

#### Error Responses

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | `invalid_session_id` | Invalid session ID format |
| 400 | `invalid_step` | Invalid step for regeneration |
| 404 | `session_not_found` | Session not found or expired |
| 500 | `regeneration_failed` | Regeneration error |

---

### 5. Get FIR Status

Retrieve FIR status and content by FIR number.

**Endpoint**: `GET /fir/{fir_number}`

**Path Parameters**:
- `fir_number` (String, Required): FIR number (format: `FIR-{8hex}-{14digits}`)

#### Request Example

```bash
curl -X GET https://api.afirgen.example.com/fir/FIR-12345678-20240115103000 \
  -H "X-API-Key: your-api-key"
```

#### Response Schema

**Status Code**: `200 OK`

```json
{
  "fir_number": "FIR-12345678-20240115103000",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "finalized_at": null,
  "fir_content": "FIRST INFORMATION REPORT\n\n..."
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `fir_number` | String | FIR identifier |
| `status` | String | FIR status (`pending` or `finalized`) |
| `created_at` | String | Creation timestamp (ISO 8601) |
| `finalized_at` | String | Finalization timestamp (ISO 8601, null if pending) |
| `fir_content` | String | Complete FIR document text |

#### Error Responses

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | `invalid_fir_number` | Invalid FIR number format |
| 404 | `fir_not_found` | FIR not found |
| 500 | `retrieval_failed` | Failed to retrieve FIR |

---

### 6. List FIRs

List FIR records with pagination and field filtering.

**Endpoint**: `GET /list_firs`

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cursor` | String | No | Pagination cursor from previous response |
| `limit` | Integer | No | Number of records per page (default: 20, max: 100) |
| `fields` | String | No | Comma-separated list of fields to return |

#### Available Fields

- `fir_number` - FIR identifier
- `status` - FIR status
- `created_at` - Creation timestamp
- `id` - Internal database ID

#### Request Example

```bash
# Basic request
curl -X GET "https://api.afirgen.example.com/list_firs?limit=20" \
  -H "X-API-Key: your-api-key"

# With field filtering
curl -X GET "https://api.afirgen.example.com/list_firs?limit=20&fields=fir_number,status,created_at" \
  -H "X-API-Key: your-api-key"

# With pagination cursor
curl -X GET "https://api.afirgen.example.com/list_firs?cursor=eyJsYXN0X3ZhbHVlIjoi...&limit=20" \
  -H "X-API-Key: your-api-key"
```

#### Response Schema

**Status Code**: `200 OK`

```json
{
  "items": [
    {
      "fir_number": "FIR-12345678-20240115103000",
      "status": "finalized",
      "created_at": "2024-01-15T10:30:00Z",
      "id": 1
    },
    {
      "fir_number": "FIR-87654321-20240115093000",
      "status": "pending",
      "created_at": "2024-01-15T09:30:00Z",
      "id": 2
    }
  ],
  "pagination": {
    "total_count": 150,
    "limit": 20,
    "has_more": true,
    "next_cursor": "eyJsYXN0X3ZhbHVlIjoiMjAyNC0wMS0xNVQwOTozMDowMFoiLCJsYXN0X2lkIjoyfQ=="
  }
}
```

#### Error Responses

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | `invalid_limit` | Limit must be between 1 and 100 |
| 400 | `invalid_fields` | Invalid field names requested |
| 500 | `list_failed` | Failed to retrieve FIR list |

---

### 7. Finalize FIR

Authenticate and finalize a pending FIR.

**Endpoint**: `POST /authenticate`

**Content-Type**: `application/json`

#### Request Schema

```json
{
  "fir_number": "FIR-12345678-20240115103000",
  "auth_key": "your-secret-auth-key"
}
```

#### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `fir_number` | String | Yes | FIR number to finalize |
| `auth_key` | String | Yes | Authentication key (min 8 characters) |

#### Request Example

```bash
curl -X POST https://api.afirgen.example.com/authenticate \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "fir_number": "FIR-12345678-20240115103000",
    "auth_key": "secure-auth-key-123"
  }'
```

#### Response Schema

**Status Code**: `200 OK`

```json
{
  "success": true,
  "message": "FIR successfully finalized",
  "fir_number": "FIR-12345678-20240115103000"
}
```

#### Error Responses

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | `invalid_fir_number` | Invalid FIR number format |
| 400 | `already_finalized` | FIR already finalized |
| 401 | `invalid_auth_key` | Invalid authentication key |
| 404 | `fir_not_found` | FIR not found |
| 500 | `auth_not_configured` | Authentication not configured |
| 500 | `authentication_failed` | Internal authentication error |

---

### 8. Health Check

Check API and dependent service health status.

**Endpoint**: `GET /health`

**Authentication**: Not required

**Health Checks:**
- **Model Server**: Bedrock service connectivity and model availability
- **ASR/OCR Server**: Transcribe and Textract service connectivity
- **Database**: MySQL RDS connection status
- **Vector Database**: OpenSearch/Aurora pgvector connection status
- **Knowledge Base**: IPC section collections and cache status
- **Circuit Breakers**: Status of all circuit breakers
- **Graceful Shutdown**: Active request count
- **Health Monitor**: Background health monitoring status

#### Request Example

```bash
curl -X GET https://api.afirgen.example.com/health
```

#### Response Schema

**Status Code**: `200 OK`

```json
{
  "status": "healthy",
  "model_server": {
    "status": "healthy",
    "message": "Bedrock services operational",
    "bedrock_models": {
      "claude": "anthropic.claude-3-sonnet-20240229-v1:0",
      "embeddings": "amazon.titan-embed-text-v1"
    }
  },
  "asr_ocr_server": {
    "status": "healthy",
    "message": "Transcribe and Textract operational",
    "services": {
      "transcribe": "available",
      "textract": "available"
    }
  },
  "database": "connected",
  "vector_database": {
    "type": "opensearch",
    "status": "connected",
    "index_count": 1,
    "document_count": 500
  },
  "kb_collections": 5,
  "kb_cache_size": 42,
  "session_persistence": "sqlite",
  "magic_available": true,
  "concurrency": {
    "max_concurrent_requests": 15,
    "max_concurrent_model_calls": 10,
    "http_pool_size": 20
  },
  "reliability": {
    "circuit_breakers": {
      "model_server": {
        "state": "closed",
        "failure_count": 0,
        "last_failure": null
      },
      "asr_ocr_server": {
        "state": "closed",
        "failure_count": 0,
        "last_failure": null
      },
      "database": {
        "state": "closed",
        "failure_count": 0,
        "last_failure": null
      }
    },
    "graceful_shutdown": {
      "active_requests": 3,
      "shutdown_initiated": false
    },
    "health_monitor": {
      "status": "running",
      "last_check": "2024-01-15T10:30:00Z"
    }
  },
  "aws_services": {
    "region": "us-east-1",
    "bedrock_available": true,
    "transcribe_available": true,
    "textract_available": true,
    "s3_available": true
  }
}
```

#### Health Status Values

| Status | Description |
|--------|-------------|
| `healthy` | All services operational |
| `degraded` | Some services experiencing issues |
| `unhealthy` | Critical services unavailable |

---

## Error Response Format

All error responses follow a consistent format:

```json
{
  "detail": "Human-readable error message",
  "error": "machine_readable_error_code",
  "timestamp": "2024-01-15T10:30:00Z",
  "trace_id": "1-5f8a1234-abcd1234efgh5678ijkl9012"
}
```

### Common Error Codes

| HTTP Status | Error Code | Description | Retry Strategy |
|-------------|------------|-------------|----------------|
| 400 | `bad_request` | Invalid request parameters | Fix request, do not retry |
| 400 | `validation_error` | Request validation failed | Fix request, do not retry |
| 400 | `dangerous_content` | Input contains XSS/injection patterns | Sanitize input, do not retry |
| 401 | `unauthorized` | Authentication required or failed | Check API key, do not retry |
| 401 | `invalid_token` | JWT token invalid or expired | Refresh token, retry once |
| 403 | `insufficient_permissions` | User lacks required permissions | Check role, do not retry |
| 404 | `not_found` | Resource not found | Check resource ID, do not retry |
| 413 | `payload_too_large` | Request body or file too large | Reduce size, do not retry |
| 415 | `unsupported_media_type` | Unsupported file format | Use supported format, do not retry |
| 429 | `too_many_requests` | Rate limit exceeded | Wait and retry with backoff |
| 500 | `internal_server_error` | Internal server error | Retry with exponential backoff |
| 500 | `transcribe_error` | Amazon Transcribe error | Retry with exponential backoff |
| 500 | `textract_error` | Amazon Textract error | Retry with exponential backoff |
| 500 | `bedrock_error` | Amazon Bedrock error | Retry with exponential backoff |
| 500 | `bedrock_throttling` | Bedrock rate limit exceeded | Retry with exponential backoff + jitter |
| 500 | `vector_db_error` | Vector database error | Retry with exponential backoff |
| 503 | `service_unavailable` | Service temporarily unavailable | Wait for circuit breaker recovery |
| 504 | `gateway_timeout` | Request timeout | Retry with longer timeout |

### AWS Service Error Codes

#### Amazon Transcribe Errors

| Error Code | Description | Action |
|------------|-------------|--------|
| `transcribe_throttling` | API rate limit exceeded | Retry with exponential backoff |
| `transcribe_invalid_audio` | Invalid audio format or corrupted file | Check file format and integrity |
| `transcribe_language_not_supported` | Language not supported | Use supported language code |
| `transcribe_timeout` | Transcription job timeout | Retry with smaller file |

#### Amazon Textract Errors

| Error Code | Description | Action |
|------------|-------------|--------|
| `textract_throttling` | API rate limit exceeded | Retry with exponential backoff |
| `textract_invalid_image` | Invalid image format or corrupted file | Check file format and integrity |
| `textract_no_text_found` | No text detected in image | Verify image quality |
| `textract_timeout` | Text extraction timeout | Retry with smaller file |

#### Amazon Bedrock Errors

| Error Code | Description | Action |
|------------|-------------|--------|
| `bedrock_throttling` | Model invocation rate limit exceeded | Retry with exponential backoff + jitter |
| `bedrock_model_error` | Model inference error | Retry with different prompt |
| `bedrock_token_limit` | Input/output token limit exceeded | Reduce prompt size |
| `bedrock_content_filter` | Content filtered by safety guardrails | Modify input content |
| `bedrock_timeout` | Model invocation timeout | Retry with shorter prompt |

#### Vector Database Errors

| Error Code | Description | Action |
|------------|-------------|--------|
| `vector_db_connection_error` | Database connection failed | Retry with exponential backoff |
| `vector_db_query_error` | Query execution failed | Retry with exponential backoff |
| `vector_db_timeout` | Query timeout | Retry with optimized query |

### Error Response Examples

**Validation Error**:
```json
{
  "detail": "Text input too short. Minimum length: 10 characters",
  "error": "validation_error"
}
```

**Authentication Error**:
```json
{
  "detail": "Invalid API key",
  "error": "unauthorized"
}
```

**Rate Limit Error**:
```json
{
  "detail": "Rate limit exceeded. Maximum 100 requests per minute allowed. Please try again later.",
  "error": "too_many_requests",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Bedrock Throttling Error**:
```json
{
  "detail": "Amazon Bedrock rate limit exceeded. Please retry with exponential backoff.",
  "error": "bedrock_throttling",
  "timestamp": "2024-01-15T10:30:00Z",
  "trace_id": "1-5f8a1234-abcd1234efgh5678ijkl9012"
}
```

**Circuit Breaker Open Error**:
```json
{
  "detail": "Service temporarily unavailable due to repeated failures. Circuit breaker is open.",
  "error": "service_unavailable",
  "timestamp": "2024-01-15T10:30:00Z",
  "retry_after": 60
}
```

---

## Request/Response Examples

### Complete FIR Generation Workflow

#### Step 1: Submit Complaint

```bash
curl -X POST https://api.afirgen.example.com/process \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I want to report a theft. Yesterday at 3 PM, two unknown persons stole my mobile phone at Central Park."
  }'
```

**Response**:
```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "steps": [],
  "requires_validation": true,
  "current_step": "transcript_review",
  "content_for_validation": {
    "transcript": "I want to report a theft. Yesterday at 3 PM..."
  }
}
```

#### Step 2: Validate Transcript

```bash
curl -X POST https://api.afirgen.example.com/validate \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "approved": true
  }'
```

**Response**:
```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_step": "summary_review",
  "content": {
    "summary": "Theft of mobile phone at Central Park by two unknown persons at 3 PM.",
    "original_transcript": "I want to report a theft..."
  },
  "message": "Summary generated. Please review and validate.",
  "requires_validation": true,
  "completed": false
}
```

#### Step 3: Validate Summary

```bash
curl -X POST https://api.afirgen.example.com/validate \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "approved": true
  }'
```

**Response**:
```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_step": "violations_review",
  "content": {
    "violations": [
      {
        "section": "IPC 379",
        "text": "Theft - Whoever intends to take dishonestly...",
        "db": "ipc_sections"
      },
      {
        "section": "IPC 34",
        "text": "Acts done by several persons in furtherance of common intention",
        "db": "ipc_sections"
      }
    ],
    "summary": "Theft of mobile phone at Central Park..."
  },
  "message": "Legal violations identified. Please review and validate.",
  "requires_validation": true,
  "completed": false
}
```

#### Step 4: Validate Violations

```bash
curl -X POST https://api.afirgen.example.com/validate \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "approved": true
  }'
```

**Response**:
```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_step": "fir_narrative_review",
  "content": {
    "fir_narrative": "On 14th January 2024 at approximately 3 PM, the complainant's mobile phone was stolen by two unidentified individuals at Central Park..."
  },
  "message": "FIR narrative generated. Please review and validate.",
  "requires_validation": true,
  "completed": false
}
```

#### Step 5: Validate Narrative

```bash
curl -X POST https://api.afirgen.example.com/validate \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "approved": true
  }'
```

**Response**:
```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_step": "final_review",
  "content": {
    "fir_content": "FIRST INFORMATION REPORT\n\nFIR No.: FIR-550e8400-20240115150000...",
    "fir_number": "FIR-550e8400-20240115150000"
  },
  "message": "FIR generated successfully. Final review required.",
  "requires_validation": true,
  "completed": false
}
```

#### Step 6: Final Approval

```bash
curl -X POST https://api.afirgen.example.com/validate \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "approved": true
  }'
```

**Response**:
```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_step": "final_review",
  "content": {
    "fir_content": "FIRST INFORMATION REPORT\n\n...",
    "fir_number": "FIR-550e8400-20240115150000"
  },
  "message": "FIR processing completed successfully!",
  "requires_validation": false,
  "completed": true
}
```

#### Step 7: Finalize FIR

```bash
curl -X POST https://api.afirgen.example.com/authenticate \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "fir_number": "FIR-550e8400-20240115150000",
    "auth_key": "secure-auth-key-123"
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "FIR successfully finalized",
  "fir_number": "FIR-550e8400-20240115150000"
}
```

---

## Performance & Latency

### Expected Latency by Operation

| Operation | Typical Latency | Max Latency | Notes |
|-----------|----------------|-------------|-------|
| Audio Transcription (5 min) | 30-180 seconds | 300 seconds | Depends on audio length and quality |
| Document OCR | 5-30 seconds | 60 seconds | Depends on image size and complexity |
| Legal Narrative Generation | 2-5 seconds | 10 seconds | Claude 3 Sonnet inference |
| Metadata Extraction | 1-3 seconds | 10 seconds | Claude 3 Sonnet inference |
| Vector Embedding | 100-500ms | 2 seconds | Titan Embeddings |
| IPC Section Search | 50-200ms | 2 seconds | Vector database query |
| Complete FIR Generation | 5-10 seconds | 30 seconds | Claude 3 Sonnet with RAG |
| End-to-End (Text Input) | 10-20 seconds | 60 seconds | All processing steps |
| End-to-End (Audio Input) | 40-200 seconds | 360 seconds | Includes transcription |
| End-to-End (Image Input) | 15-40 seconds | 90 seconds | Includes OCR |

### Performance Optimization

**Client-Side:**
1. **Compress Files**: Compress audio/image files before upload
2. **Use Appropriate Formats**: WAV for audio, JPEG for images
3. **Implement Timeouts**: Set appropriate client timeouts (5 minutes for audio)
4. **Show Progress**: Display progress indicators for long operations
5. **Cache Results**: Cache FIR data to avoid redundant requests

**Server-Side (Automatic):**
1. **Connection Pooling**: HTTP connection pooling for AWS services
2. **Concurrent Processing**: Up to 10 concurrent Bedrock API calls
3. **Retry Logic**: Automatic retry with exponential backoff
4. **Circuit Breakers**: Fail-fast when services are down
5. **IPC Section Caching**: In-memory LRU cache for frequently accessed sections

### Concurrency Limits

| Resource | Limit | Description |
|----------|-------|-------------|
| Concurrent FIR Requests | 15 | Max simultaneous FIR generation requests |
| Concurrent Bedrock Calls | 10 | Max simultaneous Bedrock API calls |
| HTTP Connection Pool | 20 | Max HTTP connections per host |
| Session Timeout | 3600s | Session expires after 1 hour of inactivity |

---

## Security

### Transport Security

- All API endpoints use HTTPS/TLS 1.2+ encryption
- HTTP requests are automatically redirected to HTTPS

### Security Headers

All responses include security headers:

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

### Input Validation

- All text inputs are sanitized to prevent XSS attacks
- File uploads are validated for type and size
- Request body size limited to 10MB
- JSON nesting depth limited to 10 levels
- Dangerous patterns (script tags, event handlers) are blocked

### Data Protection

- Files uploaded to S3 use SSE-KMS encryption
- Database connections use TLS encryption
- Sensitive data is never logged
- Temporary files are automatically cleaned up

---

## Best Practices

### 1. Error Handling

Always check the `success` field in responses:

```javascript
const response = await fetch('/process', {
  method: 'POST',
  headers: {
    'X-API-Key': apiKey,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ text: complaint })
});

const data = await response.json();

if (!data.success) {
  console.error('Error:', data.error);
  // Handle error
}
```

### 2. Session Management

- Store `session_id` for the entire workflow
- Sessions expire after 1 hour of inactivity
- Check session status before continuing workflow

### 3. Rate Limiting

- Implement exponential backoff for 429 responses
- Monitor `X-RateLimit-*` headers
- Cache responses when appropriate

### 4. File Uploads

- Validate file size client-side before upload
- Use appropriate MIME types
- Handle upload progress for large files

### 5. Pagination

- Use cursor-based pagination for large result sets
- Store `next_cursor` for subsequent requests
- Implement infinite scroll or "Load More" patterns

---

## Support

For API support, please contact:
- Email: api-support@afirgen.example.com
- Documentation: https://docs.afirgen.example.com
- Status Page: https://status.afirgen.example.com
- OpenAPI Spec: See `openapi.yaml` in the project root

### OpenAPI/Swagger Specification

A complete OpenAPI 3.0.3 specification is available in `openapi.yaml`. You can use this with:

**Swagger UI:**
```bash
# Using Docker
docker run -p 8080:8080 -e SWAGGER_JSON=/openapi.yaml -v $(pwd)/openapi.yaml:/openapi.yaml swaggerapi/swagger-ui

# Access at http://localhost:8080
```

**Postman:**
1. Import `openapi.yaml` into Postman
2. Collection will be auto-generated with all endpoints
3. Configure environment variables for API key and base URL

**Code Generation:**
```bash
# Generate Python client
openapi-generator-cli generate -i openapi.yaml -g python -o ./client

# Generate TypeScript client
openapi-generator-cli generate -i openapi.yaml -g typescript-axios -o ./client
```

---

## AWS Service Error Codes Reference

### Amazon Transcribe Error Codes

| Error Code | HTTP Status | Description | Retry Strategy | Expected Recovery Time |
|------------|-------------|-------------|----------------|----------------------|
| `transcribe_throttling` | 500 | API rate limit exceeded | Exponential backoff (1s, 2s, 4s) | 1-5 seconds |
| `transcribe_invalid_audio` | 400 | Invalid audio format or corrupted file | Fix file format, do not retry | N/A |
| `transcribe_language_not_supported` | 400 | Language not supported | Use supported language code | N/A |
| `transcribe_timeout` | 504 | Transcription job timeout | Retry with smaller file | N/A |
| `transcribe_service_error` | 500 | Internal Transcribe service error | Retry with exponential backoff | 5-30 seconds |

**Supported Languages:** hi-IN, en-IN, ta-IN, te-IN, bn-IN, mr-IN, gu-IN, kn-IN, ml-IN, pa-IN

**Typical Latency:** 30-180 seconds for 5-minute audio files

### Amazon Textract Error Codes

| Error Code | HTTP Status | Description | Retry Strategy | Expected Recovery Time |
|------------|-------------|-------------|----------------|----------------------|
| `textract_throttling` | 500 | API rate limit exceeded | Exponential backoff (1s, 2s, 4s) | 1-5 seconds |
| `textract_invalid_image` | 400 | Invalid image format or corrupted file | Fix file format, do not retry | N/A |
| `textract_no_text_found` | 400 | No text detected in image | Verify image quality, do not retry | N/A |
| `textract_timeout` | 504 | Text extraction timeout | Retry with smaller file | N/A |
| `textract_service_error` | 500 | Internal Textract service error | Retry with exponential backoff | 5-30 seconds |

**Supported Formats:** JPEG, PNG (max 25MB)

**Typical Latency:** 5-30 seconds per page

### Amazon Bedrock Error Codes

| Error Code | HTTP Status | Description | Retry Strategy | Expected Recovery Time |
|------------|-------------|-------------|----------------|----------------------|
| `bedrock_throttling` | 500 | Model invocation rate limit exceeded | Exponential backoff with jitter (1s, 2s, 4s) | 1-10 seconds |
| `bedrock_model_error` | 500 | Model inference error | Retry with different prompt | 5-30 seconds |
| `bedrock_token_limit` | 400 | Input/output token limit exceeded | Reduce prompt size, do not retry | N/A |
| `bedrock_content_filter` | 400 | Content filtered by safety guardrails | Modify input content, do not retry | N/A |
| `bedrock_timeout` | 504 | Model invocation timeout | Retry with shorter prompt | N/A |
| `bedrock_service_error` | 500 | Internal Bedrock service error | Retry with exponential backoff | 5-30 seconds |

**Models Used:**
- Claude 3 Sonnet: `anthropic.claude-3-sonnet-20240229-v1:0`
- Titan Embeddings: `amazon.titan-embed-text-v1`

**Typical Latency:**
- Legal narrative generation: 2-5 seconds
- Metadata extraction: 1-3 seconds
- Complete FIR generation: 5-10 seconds
- Vector embedding: 100-500ms

**Concurrency Limits:**
- Max 10 concurrent Bedrock API calls (enforced by semaphore)
- Circuit breaker threshold: 5 consecutive failures

### Vector Database Error Codes

| Error Code | HTTP Status | Description | Retry Strategy | Expected Recovery Time |
|------------|-------------|-------------|----------------|----------------------|
| `vector_db_connection_error` | 500 | Database connection failed | Retry with exponential backoff | 5-30 seconds |
| `vector_db_query_error` | 500 | Query execution failed | Retry with exponential backoff | 1-10 seconds |
| `vector_db_timeout` | 504 | Query timeout | Retry with optimized query | N/A |
| `vector_db_index_error` | 500 | Index not found or corrupted | Contact support | N/A |

**Supported Implementations:**
- OpenSearch Serverless (k-NN with HNSW algorithm)
- Aurora PostgreSQL with pgvector (IVFFlat index)

**Typical Latency:** 50-200ms for top-5 similarity search

### Circuit Breaker Behavior

The API implements circuit breakers for all AWS services to prevent cascading failures:

**States:**
- **Closed** (Normal): All requests pass through, failures are tracked
- **Open** (Failing): Requests fail immediately with 503 error, no AWS calls made
- **Half-Open** (Testing): Limited test requests (3) allowed to check recovery

**Configuration:**
- Failure threshold: 5 consecutive failures
- Recovery timeout: 60 seconds
- Half-open test requests: 3

**Error Response (Circuit Breaker Open):**
```json
{
  "detail": "Service temporarily unavailable due to repeated failures. Circuit breaker is open.",
  "error": "service_unavailable",
  "timestamp": "2024-01-15T10:30:00Z",
  "retry_after": 60
}
```

---

## Performance Benchmarks

### End-to-End Latency by Input Type

| Input Type | Typical Latency | P95 Latency | P99 Latency | Max Latency |
|------------|----------------|-------------|-------------|-------------|
| Text (short, <1000 chars) | 10-15 seconds | 20 seconds | 30 seconds | 60 seconds |
| Text (long, >5000 chars) | 15-20 seconds | 25 seconds | 40 seconds | 60 seconds |
| Audio (1 minute) | 40-60 seconds | 90 seconds | 120 seconds | 180 seconds |
| Audio (5 minutes) | 120-180 seconds | 240 seconds | 300 seconds | 360 seconds |
| Image (single page) | 15-25 seconds | 40 seconds | 60 seconds | 90 seconds |
| Image (multi-page) | 30-40 seconds | 60 seconds | 90 seconds | 120 seconds |

### Component-Level Latency

| Component | Operation | Typical Latency | Notes |
|-----------|-----------|----------------|-------|
| Amazon Transcribe | 1-minute audio | 30-45 seconds | Varies by language and audio quality |
| Amazon Transcribe | 5-minute audio | 120-180 seconds | Linear scaling with audio length |
| Amazon Textract | Single page OCR | 5-10 seconds | Depends on image complexity |
| Amazon Textract | Multi-page OCR | 15-30 seconds | Parallel processing where possible |
| Bedrock (Claude) | Narrative generation | 2-5 seconds | Temperature: 0.3, Max tokens: 500 |
| Bedrock (Claude) | Metadata extraction | 1-3 seconds | Temperature: 0.1, Max tokens: 300 |
| Bedrock (Claude) | FIR generation | 5-10 seconds | Temperature: 0.5, Max tokens: 2048 |
| Bedrock (Titan) | Single embedding | 100-300ms | 1536-dimensional vector |
| Bedrock (Titan) | Batch embeddings (25) | 1-3 seconds | Batch processing optimization |
| Vector Database | Similarity search | 50-200ms | Top-5 results, cosine similarity |
| IPC Cache | Cache hit | <1ms | In-memory LRU cache |
| S3 | File upload | 500ms-2s | Depends on file size |
| S3 | File download | 200ms-1s | Depends on file size |

### Throughput and Concurrency

| Metric | Value | Notes |
|--------|-------|-------|
| Max concurrent FIR requests | 15 | Enforced by semaphore |
| Max concurrent Bedrock calls | 10 | Prevents rate limiting |
| HTTP connection pool size | 20 | Per AWS service |
| Session timeout | 3600 seconds | 1 hour of inactivity |
| Request timeout | 300 seconds | 5 minutes for long operations |

### Cost Estimates (AWS Bedrock)

**Per FIR Generation (Text Input):**
- Claude 3 Sonnet invocations: 3 calls
  - Narrative generation: ~200 input tokens, ~150 output tokens
  - Metadata extraction: ~150 input tokens, ~50 output tokens
  - FIR generation: ~800 input tokens, ~1000 output tokens
  - **Total**: ~1150 input tokens, ~1200 output tokens
  - **Cost**: ~$0.004 per FIR (at $0.003/1K input, $0.015/1K output)
- Titan Embeddings: 1 call (~100 tokens)
  - **Cost**: ~$0.00001 per embedding
- **Total per FIR**: ~$0.004

**Per FIR Generation (Audio Input, 5 minutes):**
- Amazon Transcribe: 5 minutes
  - **Cost**: ~$0.024 (at $0.024/minute)
- Bedrock costs (same as text): ~$0.004
- **Total per FIR**: ~$0.028

**Per FIR Generation (Image Input):**
- Amazon Textract: 1 page
  - **Cost**: ~$0.0015 (at $0.0015/page)
- Bedrock costs (same as text): ~$0.004
- **Total per FIR**: ~$0.0055

**Monthly Cost Estimates:**
- 1,000 FIRs/month (text): ~$4
- 1,000 FIRs/month (audio): ~$28
- 1,000 FIRs/month (image): ~$5.50

*Note: Costs exclude S3 storage, data transfer, and vector database costs. Actual costs may vary based on usage patterns.*

---

## Changelog

### Version 8.0.0 (Current - Bedrock Migration)
- **BREAKING**: Migrated from GPU-based GGUF models to AWS Bedrock architecture
- Added Amazon Transcribe integration for audio transcription (10 Indian languages)
- Added Amazon Textract integration for document OCR
- Added Amazon Bedrock (Claude 3 Sonnet) for legal text processing
- Added Amazon Bedrock (Titan Embeddings) for vector embeddings
- Added support for OpenSearch Serverless and Aurora pgvector
- Enhanced rate limiting with multi-tier support (10/100/1000 req/min)
- Added JWT token authentication support
- Improved error responses with AWS service-specific error codes
- Added circuit breaker protection for AWS services
- Added X-Ray distributed tracing
- Added CloudWatch metrics for all AWS service operations
- Enhanced security with input sanitization and XSS prevention
- Added comprehensive OpenAPI 3.0.3 specification
- Improved performance with connection pooling and caching
- Added retry logic with exponential backoff for all AWS services
- Enhanced documentation with Bedrock integration details
- **Performance Characteristics:**
  - Audio transcription: 30-180 seconds for 5-minute files
  - Document OCR: 5-30 seconds per page
  - Legal narrative generation: 2-5 seconds
  - Vector search: 50-200ms
  - End-to-end FIR generation: 10-60 seconds (text), 40-360 seconds (audio)
- **Cost Optimization:**
  - ~$0.004 per text FIR
  - ~$0.028 per audio FIR (5 minutes)
  - ~$0.0055 per image FIR
  - Eliminated GPU instance costs (~$1.21/hour → pay-per-use)

### Version 7.0.0
- Added cursor-based pagination
- Added field filtering for list endpoints
- Enhanced security headers
- Added circuit breaker status to health endpoint

---

*Last Updated: January 2024*
*OpenAPI Specification: See `openapi.yaml` in project root*
