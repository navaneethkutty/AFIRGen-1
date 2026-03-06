# Requirements Document: AFIRGen Backend Cleanup for AWS Deployment

## Introduction

This document specifies requirements for cleaning up the AFIRGen backend to keep ONLY what is necessary for AWS deployment with Bedrock architecture. The current backend has accumulated unnecessary files, broken imports, and dependencies that are causing deployment failures on EC2. The cleanup will remove all GGUF model code, broken infrastructure modules, and unused dependencies while preserving the complete FIR generation workflow with AWS Bedrock services (Bedrock Claude, Transcribe, Textract, RDS MySQL).

The goal is a minimal, maintainable backend that can be built locally, committed to git, and deployed via git clone on EC2 (98.86.30.145) without import errors or missing dependencies.

## Glossary

- **AFIRGen**: Automated First Information Report Generation system
- **FIR**: First Information Report - official police document in India
- **Bedrock**: Amazon Bedrock - AWS managed service for Claude 3 Sonnet LLM
- **Transcribe**: Amazon Transcribe - AWS speech-to-text service
- **Textract**: Amazon Textract - AWS document OCR service
- **RDS**: Amazon Relational Database Service for MySQL
- **S3**: Amazon Simple Storage Service for file storage
- **EC2**: Amazon Elastic Compute Cloud instance (98.86.30.145)
- **GGUF**: GPT-Generated Unified Format for self-hosted models (to be removed)
- **Backend**: FastAPI-based Python backend service (agentv5.py)
- **ChromaDB**: Vector database for IPC sections (to be removed)
- **IPC**: Indian Penal Code sections
- **Model_Server**: Self-hosted GGUF model server (to be removed)
- **ASR_OCR_Server**: Self-hosted Whisper/Donut server (to be removed)

## Requirements

### Requirement 1: Remove GGUF Model Infrastructure

**User Story:** As a system administrator, I want to remove all GGUF model code and dependencies, so that the backend only uses AWS Bedrock services.

#### Acceptance Criteria

1. THE Backend SHALL NOT import llama-cpp-python library
2. THE Backend SHALL NOT import openai-whisper library
3. THE Backend SHALL NOT import transformers library
4. THE Backend SHALL NOT import torch library
5. THE Backend SHALL NOT contain ModelPool class for GGUF model server communication
6. THE Backend SHALL NOT contain model server health check code
7. THE Backend SHALL NOT contain whisper_transcribe method
8. THE Backend SHALL NOT contain dots_ocr_sync method
9. THE Backend SHALL NOT reference MODEL_SERVER_URL environment variable
10. THE Backend SHALL NOT reference ASR_OCR_SERVER_URL environment variable

### Requirement 2: Remove Broken Infrastructure Modules

**User Story:** As a developer, I want to remove broken infrastructure modules that cause import errors, so that the backend starts without errors.

#### Acceptance Criteria

1. THE Backend SHALL NOT import xray_tracing module
2. THE Backend SHALL NOT import reliability module
3. THE Backend SHALL NOT import celery_app module
4. THE Backend SHALL NOT import background_task_manager module
5. THE Backend SHALL NOT import redis_client module
6. THE Backend SHALL NOT import cache_manager module
7. THE Backend SHALL NOT import alerting module
8. THE Backend SHALL NOT import tracing module
9. THE Backend SHALL NOT import performance_testing module
10. THE Backend SHALL NOT import circuit_breaker module

### Requirement 3: Remove ChromaDB Vector Database

**User Story:** As a system administrator, I want to remove ChromaDB and replace it with direct IPC section storage, so that the backend has no vector database dependencies.

#### Acceptance Criteria

1. THE Backend SHALL NOT import chromadb library
2. THE Backend SHALL NOT contain KB class for ChromaDB operations
3. THE Backend SHALL NOT perform vector similarity search
4. THE Backend SHALL store IPC sections in MySQL RDS as plain text
5. THE Backend SHALL retrieve IPC sections using SQL queries with LIKE operator
6. THE Backend SHALL include all IPC sections in FIR generation prompts
7. THE Backend SHALL NOT generate embeddings for IPC sections

### Requirement 4: Minimal Dependencies List

**User Story:** As a developer, I want a minimal requirements.txt with only essential dependencies, so that the backend installs quickly and has no conflicts.

#### Acceptance Criteria

1. THE Backend SHALL require fastapi for API framework
2. THE Backend SHALL require uvicorn for ASGI server
3. THE Backend SHALL require pydantic for data validation
4. THE Backend SHALL require boto3 for AWS SDK
5. THE Backend SHALL require mysql-connector-python for MySQL RDS
6. THE Backend SHALL require python-multipart for file uploads
7. THE Backend SHALL require httpx for HTTP client
8. THE Backend SHALL require Pillow for image validation
9. THE Backend SHALL NOT require chromadb
10. THE Backend SHALL NOT require llama-cpp-python
11. THE Backend SHALL NOT require openai-whisper
12. THE Backend SHALL NOT require transformers
13. THE Backend SHALL NOT require torch
14. THE Backend SHALL NOT require redis
15. THE Backend SHALL NOT require celery
16. THE Backend SHALL NOT require prometheus-client
17. THE Backend SHALL NOT require opentelemetry libraries
18. THE Backend SHALL NOT require aws-xray-sdk

### Requirement 5: Complete FIR Template Fields

**User Story:** As a police officer, I want the generated FIR PDF to contain all required fields, so that it is legally valid and complete.

#### Acceptance Criteria

1. THE Backend SHALL include complainant name field in FIR template
2. THE Backend SHALL include complainant date of birth field in FIR template
3. THE Backend SHALL include complainant nationality field in FIR template
4. THE Backend SHALL include complainant father or husband name field in FIR template
5. THE Backend SHALL include complainant address field in FIR template
6. THE Backend SHALL include complainant contact number field in FIR template
7. THE Backend SHALL include complainant passport number field in FIR template
8. THE Backend SHALL include complainant occupation field in FIR template
9. THE Backend SHALL include incident date from field in FIR template
10. THE Backend SHALL include incident date to field in FIR template
11. THE Backend SHALL include incident time from field in FIR template
12. THE Backend SHALL include incident time to field in FIR template
13. THE Backend SHALL include incident location field in FIR template
14. THE Backend SHALL include incident address field in FIR template
15. THE Backend SHALL include incident description field in FIR template
16. THE Backend SHALL include delayed reporting reasons field in FIR template
17. THE Backend SHALL include incident summary field in FIR template
18. THE Backend SHALL include legal Acts field in FIR template
19. THE Backend SHALL include legal Sections field in FIR template
20. THE Backend SHALL include suspect details field in FIR template
21. THE Backend SHALL include investigating officer name field in FIR template
22. THE Backend SHALL include investigating officer rank field in FIR template
23. THE Backend SHALL include witnesses field in FIR template
24. THE Backend SHALL include action taken field in FIR template
25. THE Backend SHALL include investigation status field in FIR template
26. THE Backend SHALL include date of despatch field in FIR template
27. THE Backend SHALL include investigating officer signature field in FIR template
28. THE Backend SHALL include investigating officer date field in FIR template
29. THE Backend SHALL include complainant signature field in FIR template
30. THE Backend SHALL include complainant date field in FIR template

### Requirement 6: AWS Bedrock Integration

**User Story:** As a system administrator, I want the backend to use AWS Bedrock for all text generation, so that we have no self-hosted model dependencies.

#### Acceptance Criteria

1. THE Backend SHALL use boto3 bedrock-runtime client for Claude 3 Sonnet
2. WHEN generating formal narrative, THE Backend SHALL invoke Claude via Bedrock
3. WHEN extracting metadata, THE Backend SHALL invoke Claude via Bedrock
4. WHEN generating FIR content, THE Backend SHALL invoke Claude via Bedrock
5. THE Backend SHALL use model ID "anthropic.claude-3-sonnet-20240229-v1:0"
6. THE Backend SHALL pass IPC sections as context in Claude prompts
7. THE Backend SHALL extract all 30 FIR template fields from Claude responses
8. THE Backend SHALL validate that Claude responses contain all required fields
9. WHEN Claude API calls fail, THE Backend SHALL retry up to 2 times
10. THE Backend SHALL log all Bedrock API calls with request and response

### Requirement 7: AWS Transcribe Integration

**User Story:** As a police officer, I want to upload audio complaints, so that they are transcribed using AWS Transcribe.

#### Acceptance Criteria

1. THE Backend SHALL use boto3 transcribe client for audio transcription
2. WHEN audio file is uploaded, THE Backend SHALL upload it to S3
3. WHEN audio is in S3, THE Backend SHALL start Transcribe job
4. THE Backend SHALL support Hindi language code "hi-IN"
5. THE Backend SHALL support English language code "en-IN"
6. THE Backend SHALL poll Transcribe job status until completion
7. WHEN transcription completes, THE Backend SHALL retrieve transcript text
8. WHEN transcription fails, THE Backend SHALL return error message
9. THE Backend SHALL delete audio file from S3 after transcription
10. THE Backend SHALL pass transcript to Bedrock for FIR generation

### Requirement 8: AWS Textract Integration

**User Story:** As a police officer, I want to upload document images, so that text is extracted using AWS Textract.

#### Acceptance Criteria

1. THE Backend SHALL use boto3 textract client for document OCR
2. WHEN image file is uploaded, THE Backend SHALL upload it to S3
3. WHEN image is in S3, THE Backend SHALL call Textract DetectDocumentText
4. THE Backend SHALL extract plain text from Textract response
5. WHEN extraction fails, THE Backend SHALL return error message
6. THE Backend SHALL delete image file from S3 after extraction
7. THE Backend SHALL pass extracted text to Bedrock for FIR generation

### Requirement 9: MySQL RDS Storage

**User Story:** As a system administrator, I want FIR records stored in MySQL RDS, so that data persists across deployments.

#### Acceptance Criteria

1. THE Backend SHALL connect to MySQL RDS at afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com:3306
2. THE Backend SHALL use database name "afirgen_db"
3. THE Backend SHALL use username "admin"
4. THE Backend SHALL read password from environment variable DB_PASSWORD
5. THE Backend SHALL create fir_records table if not exists
6. WHEN FIR is generated, THE Backend SHALL insert record into fir_records table
7. THE Backend SHALL store fir_number, session_id, complaint_text, fir_content, violations_json, status, created_at
8. WHEN FIR is finalized, THE Backend SHALL update status to "finalized"
9. THE Backend SHALL retrieve FIR by fir_number using SELECT query
10. THE Backend SHALL list all FIRs using SELECT query with pagination

### Requirement 10: S3 File Storage

**User Story:** As a system administrator, I want temporary files stored in S3, so that EC2 instance has no local file storage.

#### Acceptance Criteria

1. THE Backend SHALL use boto3 s3 client for file operations
2. THE Backend SHALL upload audio files to S3 bucket with prefix "audio/"
3. THE Backend SHALL upload image files to S3 bucket with prefix "images/"
4. THE Backend SHALL generate unique file names using UUID
5. THE Backend SHALL use server-side encryption for all S3 uploads
6. THE Backend SHALL delete files from S3 after processing
7. THE Backend SHALL read S3_BUCKET_NAME from environment variable
8. WHEN S3 operations fail, THE Backend SHALL return error message

### Requirement 11: Simplified File Structure

**User Story:** As a developer, I want a simple file structure with only essential files, so that the codebase is easy to navigate.

#### Acceptance Criteria

1. THE Backend SHALL have agentv5.py as main application file
2. THE Backend SHALL have requirements.txt with minimal dependencies
3. THE Backend SHALL have .env file for environment variables
4. THE Backend SHALL have README.md with deployment instructions
5. THE Backend SHALL NOT have infrastructure/ directory
6. THE Backend SHALL NOT have services/ directory with model server code
7. THE Backend SHALL NOT have middleware/ directory with unused middleware
8. THE Backend SHALL NOT have tests/ directory with broken tests
9. THE Backend SHALL NOT have migrations/ directory
10. THE Backend SHALL NOT have docker-compose.yaml
11. THE Backend SHALL NOT have Dockerfile
12. THE Backend SHALL NOT have celery configuration files

### Requirement 12: Environment Configuration

**User Story:** As a system administrator, I want all configuration in environment variables, so that deployment is simple.

#### Acceptance Criteria

1. THE Backend SHALL read AWS_REGION from environment variable with default "us-east-1"
2. THE Backend SHALL read DB_HOST from environment variable
3. THE Backend SHALL read DB_PORT from environment variable with default "3306"
4. THE Backend SHALL read DB_USER from environment variable with default "admin"
5. THE Backend SHALL read DB_PASSWORD from environment variable
6. THE Backend SHALL read DB_NAME from environment variable with default "afirgen_db"
7. THE Backend SHALL read S3_BUCKET_NAME from environment variable
8. THE Backend SHALL read BEDROCK_MODEL_ID from environment variable with default "anthropic.claude-3-sonnet-20240229-v1:0"
9. THE Backend SHALL read API_KEY from environment variable for authentication
10. THE Backend SHALL validate all required environment variables on startup
11. WHEN required environment variables are missing, THE Backend SHALL log error and exit

### Requirement 13: Session Management

**User Story:** As a police officer, I want to track FIR generation progress, so that I can see status updates.

#### Acceptance Criteria

1. THE Backend SHALL create session with unique session_id for each FIR generation request
2. THE Backend SHALL store session state in SQLite database sessions.db
3. THE Backend SHALL update session status to "processing" when generation starts
4. THE Backend SHALL update session status to "completed" when generation finishes
5. THE Backend SHALL update session status to "failed" when generation fails
6. THE Backend SHALL store transcript, summary, violations, and fir_content in session
7. WHEN client polls session status, THE Backend SHALL return current status and data
8. THE Backend SHALL clean up sessions older than 24 hours
9. THE Backend SHALL NOT use Redis for session storage

### Requirement 14: Error Handling

**User Story:** As a developer, I want clear error messages, so that I can troubleshoot issues quickly.

#### Acceptance Criteria

1. WHEN AWS service calls fail, THE Backend SHALL log error with service name and error message
2. WHEN database operations fail, THE Backend SHALL log error with SQL query and error message
3. WHEN file uploads fail, THE Backend SHALL return HTTP 400 with error message
4. WHEN authentication fails, THE Backend SHALL return HTTP 401 with error message
5. WHEN rate limit is exceeded, THE Backend SHALL return HTTP 429 with error message
6. WHEN internal errors occur, THE Backend SHALL return HTTP 500 with generic error message
7. THE Backend SHALL NOT expose sensitive information in error messages
8. THE Backend SHALL log all errors to logs/main_backend.log file

### Requirement 15: API Endpoints

**User Story:** As a frontend developer, I want simple API endpoints, so that integration is straightforward.

#### Acceptance Criteria

1. THE Backend SHALL expose POST /process endpoint for FIR generation
2. THE Backend SHALL accept text, audio, or image files in /process endpoint
3. THE Backend SHALL return session_id in /process response
4. THE Backend SHALL expose GET /session/{session_id} endpoint for status polling
5. THE Backend SHALL return status, transcript, summary, violations, fir_content in /session response
6. THE Backend SHALL expose POST /authenticate endpoint for FIR finalization
7. THE Backend SHALL expose GET /fir/{fir_number} endpoint for FIR retrieval
8. THE Backend SHALL expose GET /health endpoint for health checks
9. THE Backend SHALL expose GET /firs endpoint for listing all FIRs with pagination
10. THE Backend SHALL require API key authentication for all endpoints except /health

### Requirement 16: Deployment Process

**User Story:** As a system administrator, I want simple deployment via git clone, so that I can deploy quickly.

#### Acceptance Criteria

1. THE Backend SHALL be deployable by cloning git repository
2. THE Backend SHALL install dependencies using "pip install -r requirements.txt"
3. THE Backend SHALL start using "uvicorn agentv5:app --host 0.0.0.0 --port 8000"
4. THE Backend SHALL read configuration from .env file
5. THE Backend SHALL create database tables on first startup
6. THE Backend SHALL NOT require Docker
7. THE Backend SHALL NOT require Redis server
8. THE Backend SHALL NOT require Celery worker
9. THE Backend SHALL NOT require model server
10. THE Backend SHALL log startup messages to console and log file

### Requirement 17: IPC Sections Storage

**User Story:** As a system administrator, I want IPC sections stored in MySQL, so that they are available for FIR generation.

#### Acceptance Criteria

1. THE Backend SHALL create ipc_sections table in MySQL RDS
2. THE Backend SHALL store section_number, title, description, penalty in ipc_sections table
3. THE Backend SHALL load IPC sections from JSON file on first startup
4. THE Backend SHALL retrieve all IPC sections using SELECT query
5. THE Backend SHALL pass IPC sections as context to Claude prompts
6. THE Backend SHALL NOT use vector similarity search
7. THE Backend SHALL NOT generate embeddings for IPC sections

### Requirement 18: FIR Generation Workflow

**User Story:** As a police officer, I want complete FIR generation from complaint text, so that I can file reports quickly.

#### Acceptance Criteria

1. WHEN complaint text is provided, THE Backend SHALL generate formal narrative using Claude
2. WHEN formal narrative is generated, THE Backend SHALL extract metadata using Claude
3. WHEN metadata is extracted, THE Backend SHALL retrieve relevant IPC sections from MySQL
4. WHEN IPC sections are retrieved, THE Backend SHALL generate complete FIR using Claude
5. THE Backend SHALL validate that FIR contains all 30 required fields
6. WHEN FIR is generated, THE Backend SHALL store it in MySQL RDS
7. WHEN FIR is stored, THE Backend SHALL return fir_number to client
8. THE Backend SHALL complete workflow within 60 seconds for text input
9. THE Backend SHALL complete workflow within 180 seconds for audio input
10. THE Backend SHALL complete workflow within 90 seconds for image input

### Requirement 19: PDF Generation

**User Story:** As a police officer, I want to download FIR as PDF, so that I can print and file it.

#### Acceptance Criteria

1. THE Backend SHALL generate PDF from FIR content
2. THE Backend SHALL include all 30 FIR template fields in PDF
3. THE Backend SHALL format PDF with proper sections and headings
4. THE Backend SHALL include complainant signature field in PDF
5. THE Backend SHALL include investigating officer signature field in PDF
6. THE Backend SHALL return PDF as downloadable file
7. THE Backend SHALL use reportlab library for PDF generation
8. THE Backend SHALL store PDF in S3 with prefix "pdfs/"
9. THE Backend SHALL return S3 URL for PDF download
10. THE Backend SHALL delete PDF from S3 after 7 days

### Requirement 20: Logging

**User Story:** As a system administrator, I want detailed logs, so that I can monitor and troubleshoot the backend.

#### Acceptance Criteria

1. THE Backend SHALL log all API requests with method, path, status code, duration
2. THE Backend SHALL log all AWS service calls with service name, operation, duration
3. THE Backend SHALL log all database queries with SQL and duration
4. THE Backend SHALL log all errors with stack trace
5. THE Backend SHALL write logs to logs/main_backend.log file
6. THE Backend SHALL rotate log files when size exceeds 10MB
7. THE Backend SHALL keep last 5 log files
8. THE Backend SHALL use JSON format for structured logging
9. THE Backend SHALL include timestamp, level, message, context in each log entry
10. THE Backend SHALL NOT log sensitive data like passwords or API keys

### Requirement 21: Rate Limiting

**User Story:** As a system administrator, I want rate limiting on API endpoints, so that the backend is protected from abuse.

#### Acceptance Criteria

1. THE Backend SHALL limit requests to 100 per minute per IP address
2. WHEN rate limit is exceeded, THE Backend SHALL return HTTP 429 status code
3. THE Backend SHALL include Retry-After header in 429 responses
4. THE Backend SHALL use in-memory storage for rate limit tracking
5. THE Backend SHALL NOT use Redis for rate limiting
6. THE Backend SHALL reset rate limit counters every minute
7. THE Backend SHALL exclude /health endpoint from rate limiting

### Requirement 22: Security Headers

**User Story:** As a security officer, I want security headers on all responses, so that the backend follows security best practices.

#### Acceptance Criteria

1. THE Backend SHALL include X-Content-Type-Options: nosniff header
2. THE Backend SHALL include X-Frame-Options: DENY header
3. THE Backend SHALL include X-XSS-Protection: 1; mode=block header
4. THE Backend SHALL include Strict-Transport-Security header for HTTPS
5. THE Backend SHALL include Content-Security-Policy header
6. THE Backend SHALL NOT expose server version in headers

### Requirement 23: File Validation

**User Story:** As a security officer, I want uploaded files validated, so that malicious files are rejected.

#### Acceptance Criteria

1. WHEN audio file is uploaded, THE Backend SHALL validate file extension is .wav, .mp3, or .mpeg
2. WHEN image file is uploaded, THE Backend SHALL validate file extension is .jpg, .jpeg, or .png
3. THE Backend SHALL validate file size is less than 10MB
4. THE Backend SHALL validate file content matches declared content type
5. WHEN validation fails, THE Backend SHALL return HTTP 400 with error message
6. THE Backend SHALL NOT process files that fail validation

### Requirement 24: Health Check

**User Story:** As a system administrator, I want health check endpoint, so that I can monitor backend status.

#### Acceptance Criteria

1. THE Backend SHALL expose GET /health endpoint
2. THE Backend SHALL return HTTP 200 when healthy
3. THE Backend SHALL check MySQL RDS connection in health check
4. THE Backend SHALL check AWS Bedrock access in health check
5. THE Backend SHALL return status "healthy" when all checks pass
6. THE Backend SHALL return status "unhealthy" when any check fails
7. THE Backend SHALL include check details in health response
8. THE Backend SHALL NOT require authentication for /health endpoint

### Requirement 25: Graceful Shutdown

**User Story:** As a system administrator, I want graceful shutdown, so that in-flight requests complete before shutdown.

#### Acceptance Criteria

1. WHEN SIGTERM signal is received, THE Backend SHALL stop accepting new requests
2. THE Backend SHALL wait for in-flight requests to complete
3. THE Backend SHALL close database connections
4. THE Backend SHALL close AWS service clients
5. THE Backend SHALL flush logs to disk
6. THE Backend SHALL exit with status code 0 after graceful shutdown
7. THE Backend SHALL force shutdown after 30 seconds if requests do not complete
