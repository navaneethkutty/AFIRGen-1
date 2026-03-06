# Implementation Plan: AFIRGen Backend Cleanup for AWS Deployment

## Overview

This plan implements a minimal, production-ready AFIRGen backend using AWS managed services exclusively. The implementation removes broken modules (xray_tracing, reliability, etc.), self-hosted model code (GGUF, ChromaDB), and unused dependencies that are causing deployment failures on EC2.

**IMPORTANT: We KEEP all infrastructure files:**
- Terraform files (terraform/)
- Docker files (Dockerfile, docker-compose.yaml)
- Kubernetes files (k8s/, kubernetes/)
- Working tests and test infrastructure
- Current documentation and specs

**We ONLY REMOVE:**
- Broken Python modules causing import errors
- GGUF model and self-hosted model code
- ChromaDB vector database code
- Unused dependencies (llama-cpp-python, openai-whisper, chromadb, redis, celery, aws-xray-sdk)
- Duplicate or obsolete documentation
- Test artifacts (.pytest_cache/, .hypothesis/tmp/)

The backend processes complaint inputs (text, audio, or image) through a 5-stage workflow to generate complete, legally-valid First Information Reports (FIRs) with all 30 required fields, using AWS Bedrock (Claude 3 Sonnet), Transcribe, Textract, RDS MySQL, and S3.

**Key Implementation Steps:**
1. Remove ONLY broken/unnecessary files (KEEP Terraform, Docker, K8s)
2. Fix broken imports and update dependencies
3. Build clean backend with AWS Bedrock integration
4. Test locally on Windows before EC2 deployment
5. Configure frontend API endpoints for new backend
6. Deploy to EC2 via git clone after successful local testing

**Development Workflow:**
- Local development and testing on Windows
- Git commit and push after local validation
- EC2 deployment via git clone
- Frontend configuration for both local and EC2 environments

## Tasks

- [x] 1. Remove ONLY unnecessary and broken files (KEEP Terraform, Docker, K8s)
  - [x] 1.1 Identify and remove broken Python modules causing import errors
    - Delete infrastructure/xray_tracing.py (broken AWS X-Ray module)
    - Delete infrastructure/reliability.py (broken module)
    - Delete infrastructure/celery_app.py (not using Celery)
    - Delete infrastructure/background_task_manager.py (not using)
    - Delete infrastructure/redis_client.py (not using Redis)
    - Delete infrastructure/cache_manager.py (not using)
    - Delete infrastructure/alerting.py (not using)
    - Delete infrastructure/tracing.py (broken)
    - Delete infrastructure/performance_testing.py (not using)
    - Delete infrastructure/circuit_breaker.py (not using)
    - KEEP any working infrastructure modules that are actually used
  - [x] 1.2 Remove GGUF model and self-hosted model files
    - Delete files related to llama-cpp-python usage
    - Delete files related to openai-whisper usage
    - Delete files related to transformers/torch usage
    - Delete ModelPool class files for GGUF model server
    - Delete whisper_transcribe method files
    - Delete donut_ocr_sync method files
    - KEEP any files needed for AWS Bedrock integration
  - [x] 1.3 Remove ChromaDB vector database files
    - Delete KB class files for ChromaDB operations
    - Delete vector similarity search files
    - Delete embedding generation files for ChromaDB
    - KEEP any files needed for IPC section storage in MySQL
  - [x] 1.4 Remove duplicate or obsolete markdown files
    - Review all .md files and remove duplicates
    - Remove outdated documentation that contradicts current implementation
    - KEEP README.md, deployment guides, and current documentation
    - KEEP all spec files in .kiro/specs/
  - [x] 1.5 Clean up test artifacts (but KEEP test infrastructure)
    - Delete .pytest_cache/ directory
    - Delete .hypothesis/examples/ and .hypothesis/tmp/ (test artifacts)
    - KEEP .hypothesis/constants/ if needed
    - KEEP tests/ directory structure
    - KEEP test files that are working
  - [x] 1.6 Remove old/unused configuration files
    - Delete old .env files (KEEP .env.example template)
    - Delete duplicate config files
    - KEEP all Terraform files (terraform/)
    - KEEP all Docker files (Dockerfile, docker-compose.yaml)
    - KEEP all K8s files (k8s/, kubernetes/)
  - [x] 1.7 Verify no broken imports remain
    - Search for imports of deleted modules
    - Update or remove broken import statements
    - Ensure application starts without import errors
  - _Requirements: 1.1-1.10, 2.1-2.10, 3.1-3.7, 4.1-4.18_

- [x] 2. Set up minimal project structure and configuration
  - Create or update agentv5.py as main application file (clean implementation)
  - Update requirements.txt to include only essential dependencies (remove broken ones like llama-cpp-python, openai-whisper, chromadb, redis, celery, aws-xray-sdk)
  - Keep core dependencies: fastapi, uvicorn, pydantic, boto3, mysql-connector-python, python-multipart, httpx, Pillow, reportlab
  - Update .env.example template with all required and optional environment variables
  - Update README.md with deployment instructions for both local (Windows) and EC2 (Linux)
  - Ensure logs/ directory exists for application logs
  - KEEP all Terraform, Docker, and K8s files
  - _Requirements: 4.1-4.9, 11.1-11.12, 12.1-12.11, 16.1-16.10_

- [x] 2. Implement configuration and logging infrastructure
  - [x] 2.1 Implement Config class with environment variable loading
    - Load AWS configuration (AWS_REGION, S3_BUCKET_NAME, BEDROCK_MODEL_ID)
    - Load database configuration (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)
    - Load API configuration (API_KEY)
    - Set defaults for optional variables (rate limits, timeouts, file size limits)
    - Implement validate() method to check required variables on startup
    - _Requirements: 12.1-12.11_
  
  - [x] 2.2 Implement structured JSON logging
    - Configure logging to write to logs/main_backend.log
    - Implement JSON formatter with timestamp, level, message, context fields
    - Configure log rotation (10MB max size, keep 5 files)
    - Ensure no sensitive data (passwords, API keys) in logs
    - Support both Windows and Linux file paths
    - _Requirements: 20.1-20.10_
  
  - [x] 2.3 Add local development support for Windows
    - Ensure all file paths work on Windows (use os.path.join or pathlib)
    - Test .env file loading on Windows
    - Ensure logs directory creation works on Windows
    - Add Windows-specific notes to README.md
    - _Requirements: 16.1-16.10_

- [x] 3. Implement AWS service clients
  - [x] 3.1 Implement AWSServiceClients class initialization
    - Initialize boto3 clients for bedrock-runtime, transcribe, textract, s3
    - Configure clients with region from environment
    - _Requirements: 6.1, 7.1, 8.1, 10.1_
  
  - [x] 3.2 Implement invoke_claude method for Bedrock
    - Use model ID "anthropic.claude-3-sonnet-20240229-v1:0"
    - Implement retry logic (up to 2 retries with 2-second delay)
    - Set timeout to 60 seconds
    - Log all Bedrock API calls with request and response
    - _Requirements: 6.1-6.10_
  
  - [x] 3.3 Implement transcribe_audio method for AWS Transcribe
    - Start transcription job with language code (hi-IN or en-IN)
    - Poll job status every 5 seconds (max 180 seconds)
    - Retrieve transcript text from completed job
    - Handle transcription failures with error messages
    - _Requirements: 7.1-7.10_
  
  - [x] 3.4 Implement extract_text_from_image method for AWS Textract
    - Call DetectDocumentText API
    - Extract plain text from Textract response blocks
    - Handle extraction failures with error messages
    - _Requirements: 8.1-8.7_
  
  - [x] 3.5 Implement S3 file operations
    - Implement upload_to_s3 with server-side encryption
    - Generate unique file names using UUID
    - Use prefixes: audio/, images/, pdfs/
    - Implement delete_from_s3 for cleanup
    - _Requirements: 10.1-10.8_

- [x] 4. Implement database management
  - [x] 4.1 Implement DatabaseManager class with MySQL connection pooling
    - Create MySQL connection pool with 5 connections
    - Initialize SQLite connection for sessions.db
    - Implement _initialize_tables method to create tables on startup
    - _Requirements: 9.1-9.5_
  
  - [x] 4.2 Create MySQL RDS table schemas
    - Create fir_records table with all fields (id, fir_number, session_id, complaint_text, fir_content JSON, violations_json JSON, status, created_at, updated_at)
    - Add indexes on fir_number, session_id, status, created_at
    - Create ipc_sections table with fields (id, section_number, title, description, penalty, created_at)
    - Add indexes on section_number and FULLTEXT index on description/title
    - _Requirements: 9.1-9.10, 17.1-17.7_
  
  - [x] 4.3 Create SQLite sessions table schema
    - Create sessions table with fields (session_id, status, transcript, summary, violations, fir_content, fir_number, error, created_at, updated_at)
    - Add index on created_at for cleanup queries
    - _Requirements: 13.1-13.9_
  
  - [x] 4.4 Implement FIR record database operations
    - Implement insert_fir_record method with parameterized queries
    - Implement get_fir_by_number method
    - Implement list_firs method with pagination (limit, offset)
    - Implement update FIR status to "finalized"
    - _Requirements: 9.6-9.10_
  
  - [x] 4.5 Implement IPC sections database operations
    - Implement get_ipc_sections method using SQL LIKE queries
    - Implement load_ipc_sections method to load from JSON file on first startup
    - Query ipc_sections table with keyword matching on description and title
    - _Requirements: 17.1-17.7_
  
  - [x] 4.6 Implement session management operations
    - Implement create_session method
    - Implement update_session method
    - Implement get_session method
    - Implement cleanup_old_sessions method (delete sessions older than 24 hours)
    - _Requirements: 13.1-13.9_

- [x] 5. Implement FIR generation workflow
  - [x] 5.1 Implement FIRGenerator class initialization
    - Accept AWSServiceClients and DatabaseManager as dependencies
    - _Requirements: 18.1-18.10_
  
  - [x] 5.2 Implement Stage 1: Formal narrative generation
    - Implement _generate_formal_narrative method
    - Construct Claude prompt with formal police report instructions
    - Invoke Claude via Bedrock with max_tokens=4096
    - Extract narrative from response
    - _Requirements: 18.1_
  
  - [x] 5.3 Implement Stage 2: Metadata extraction
    - Implement _extract_metadata method
    - Construct Claude prompt requesting JSON metadata (complainant_name, incident_date, incident_time, incident_location, incident_type, keywords)
    - Invoke Claude via Bedrock with max_tokens=2048
    - Parse JSON response and validate required fields
    - _Requirements: 18.2_
  
  - [x] 5.4 Implement Stage 3: IPC section retrieval
    - Implement _retrieve_ipc_sections method
    - Extract keywords from metadata
    - Query MySQL ipc_sections table using LIKE operator
    - Return top 10 matching sections
    - Handle empty results gracefully
    - _Requirements: 17.4-17.6, 18.3_
  
  - [x] 5.5 Implement Stage 4: Complete FIR generation with all 30 fields
    - Implement _generate_complete_fir method
    - Construct comprehensive Claude prompt with narrative, metadata, and IPC sections
    - Include all 30 FIR template field names in prompt
    - Invoke Claude via Bedrock with max_tokens=8192
    - Parse JSON response with all 30 fields
    - _Requirements: 5.1-5.30, 6.6-6.8, 18.4_
  
  - [x] 5.6 Implement FIR field validation
    - Implement _validate_fir_fields method
    - Check that all 30 required fields are present
    - Check that all fields have non-empty values
    - Return validation result
    - _Requirements: 6.8, 18.5_
  
  - [x] 5.7 Implement FIR number generation
    - Generate unique FIR number with format: FIR-YYYYMMDD-XXXXX
    - Use current date and auto-incrementing sequence
    - _Requirements: 18.7_
  
  - [x] 5.8 Implement text input workflow
    - Implement generate_from_text method
    - Execute all 5 stages in sequence
    - Store FIR in MySQL and update session
    - Return fir_number and session data
    - _Requirements: 18.1-18.8_
  
  - [x] 5.9 Implement audio input workflow
    - Implement generate_from_audio method
    - Upload audio to S3, transcribe with AWS Transcribe
    - Delete audio from S3 after transcription
    - Pass transcript to text workflow
    - _Requirements: 7.1-7.10, 18.9_
  
  - [x] 5.10 Implement image input workflow
    - Implement generate_from_image method
    - Upload image to S3, extract text with AWS Textract
    - Delete image from S3 after extraction
    - Pass extracted text to text workflow
    - _Requirements: 8.1-8.7, 18.10_

- [x] 6. Implement PDF generation
  - [x] 6.1 Implement PDFGenerator class
    - Initialize reportlab canvas for PDF generation
    - _Requirements: 19.1-19.10_
  
  - [x] 6.2 Implement generate_fir_pdf method with all 30 fields
    - Create PDF document with proper formatting
    - Add header section with FIR number
    - Add complainant details section (8 fields: name, DOB, nationality, father/husband name, address, contact, passport, occupation)
    - Add incident details section (10 fields: date from/to, time from/to, location, address, description, delayed reasons, summary)
    - Add legal provisions section (3 fields: acts, sections, suspect details)
    - Add investigation section (6 fields: officer name, rank, witnesses, action taken, status, date of despatch)
    - Add signature section (4 fields: officer signature, officer date, complainant signature, complainant date)
    - Return PDF as bytes
    - _Requirements: 5.1-5.30, 19.1-19.10_

- [x] 7. Implement API endpoints
  - [x] 7.1 Initialize FastAPI application
    - Create FastAPI app with title and version
    - Add CORS middleware
    - Initialize global instances (config, aws_clients, db_manager, rate_limiter, fir_generator, pdf_generator)
    - _Requirements: 15.1-15.10_
  
  - [x] 7.2 Implement POST /process endpoint
    - Define ProcessRequest model (input_type: text/audio/image, text: optional, language: optional)
    - Validate input based on input_type
    - Create session with unique session_id
    - Start async FIR generation workflow
    - Return session_id and status "processing"
    - _Requirements: 15.1-15.3_
  
  - [x] 7.3 Implement GET /session/{session_id} endpoint
    - Define SessionResponse model (session_id, status, transcript, summary, violations, fir_content, fir_number, error)
    - Retrieve session data from SQLite
    - Return current session status and data
    - _Requirements: 15.4-15.5_
  
  - [x] 7.4 Implement POST /authenticate endpoint
    - Define AuthenticateRequest model (session_id, complainant_signature, officer_signature)
    - Retrieve FIR from session
    - Generate PDF with signatures
    - Upload PDF to S3
    - Update FIR status to "finalized" in MySQL
    - Return fir_number and pdf_url
    - _Requirements: 15.6_
  
  - [x] 7.5 Implement GET /fir/{fir_number} endpoint
    - Define FIRResponse model (fir_number, session_id, complaint_text, fir_content, violations_json, status, created_at)
    - Retrieve FIR from MySQL by fir_number
    - Return FIR data
    - _Requirements: 15.7_
  
  - [x] 7.6 Implement GET /firs endpoint with pagination
    - Accept query parameters: limit (default 20, max 100), offset (default 0)
    - Define FIRListResponse model (firs, total, limit, offset)
    - Query MySQL with pagination
    - Return list of FIRs
    - _Requirements: 15.9_
  
  - [x] 7.7 Implement GET /health endpoint
    - Define HealthResponse model (status, checks, timestamp)
    - Check MySQL RDS connection
    - Check AWS Bedrock access
    - Return "healthy" if all checks pass, "unhealthy" otherwise
    - Include check details in response
    - _Requirements: 24.1-24.8_

- [x] 8. Implement middleware and security
  - [x] 8.1 Implement API key authentication middleware
    - Verify X-API-Key header matches configured API_KEY
    - Exclude /health endpoint from authentication
    - Return HTTP 401 for invalid or missing API key
    - _Requirements: 15.10_
  
  - [x] 8.2 Implement rate limiting middleware
    - Create RateLimiter class with in-memory storage
    - Track requests per IP address (100 per minute)
    - Return HTTP 429 when rate limit exceeded
    - Include Retry-After header in 429 responses
    - Exclude /health endpoint from rate limiting
    - _Requirements: 21.1-21.7_
  
  - [x] 8.3 Implement security headers middleware
    - Add X-Content-Type-Options: nosniff header
    - Add X-Frame-Options: DENY header
    - Add X-XSS-Protection: 1; mode=block header
    - Add Strict-Transport-Security header for HTTPS
    - Add Content-Security-Policy header
    - _Requirements: 22.1-22.6_
  
  - [x] 8.4 Implement file validation
    - Validate audio file extensions (.wav, .mp3, .mpeg)
    - Validate image file extensions (.jpg, .jpeg, .png)
    - Validate file size < 10MB
    - Validate file content matches declared content type using Pillow
    - Return HTTP 400 for validation failures
    - _Requirements: 23.1-23.6_

- [x] 9. Implement error handling and retry logic
  - [x] 9.1 Implement error response models
    - Create standardized error response format (error, detail, status_code)
    - Implement error handlers for HTTP 400, 401, 429, 500
    - _Requirements: 14.1-14.8_
  
  - [x] 9.2 Implement retry logic for AWS service calls
    - Retry Bedrock invocations up to 2 times with 2-second delay
    - Retry Transcribe job start up to 2 times
    - Retry S3 operations up to 2 times
    - Use exponential backoff for retries
    - _Requirements: 6.9_
  
  - [x] 9.3 Implement error logging
    - Log all AWS service errors with service name, operation, error code, message
    - Log all database errors with SQL query and error message
    - Log all validation errors with details
    - Include stack traces for debugging
    - Ensure no sensitive data in error messages to clients
    - _Requirements: 14.1-14.8_
  
  - [x] 9.4 Implement graceful error recovery
    - Continue workflow with empty IPC sections if retrieval fails
    - Use basic defaults if metadata extraction fails
    - Clean up S3 files even on failure
    - Mark session as failed and store error message
    - _Requirements: 14.1-14.8_

- [x] 10. Implement startup and shutdown handlers
  - [x] 10.1 Implement startup event handler
    - Validate configuration on startup
    - Initialize database tables (MySQL and SQLite)
    - Load IPC sections from JSON file if table is empty
    - Log startup messages
    - _Requirements: 16.1-16.10_
  
  - [x] 10.2 Implement graceful shutdown handler
    - Stop accepting new requests on SIGTERM
    - Wait for in-flight requests to complete (max 30 seconds)
    - Close database connections
    - Close AWS service clients
    - Flush logs to disk
    - Exit with status code 0
    - _Requirements: 25.1-25.7_

- [x] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Write property-based tests for correctness properties
  - [x] 12.1 Write property test for FIR field completeness
    - **Property 1: FIR field completeness**
    - **Validates: Requirements 5.1-5.30, 6.7, 18.5**
    - For any valid complaint text, generated FIR contains all 30 required fields with non-empty values
  
  - [x] 12.2 Write property test for FIR generation workflow completeness
    - **Property 2: FIR generation workflow completeness**
    - **Validates: Requirements 18.1-18.4, 18.7**
    - For any valid complaint text, workflow executes all 5 stages and returns fir_number
  
  - [x] 12.3 Write property test for audio transcription
    - **Property 3: Audio transcription**
    - **Validates: Requirements 7.7**
    - For any valid audio file, transcription produces non-empty transcript text
  
  - [x] 12.4 Write property test for image text extraction
    - **Property 4: Image text extraction**
    - **Validates: Requirements 8.4**
    - For any valid image file, OCR produces non-empty extracted text
  
  - [x] 12.5 Write property test for FIR storage persistence
    - **Property 5: FIR storage persistence**
    - **Validates: Requirements 9.6-9.7, 18.6**
    - For any generated FIR, record is inserted into fir_records table with all required fields
  
  - [x] 12.6 Write property test for FIR storage round trip
    - **Property 6: FIR storage round trip**
    - **Validates: Requirements 9.9**
    - For any generated FIR, storing and retrieving by fir_number returns equivalent content
  
  - [x] 12.7 Write property test for FIR listing pagination
    - **Property 7: FIR listing pagination**
    - **Validates: Requirements 9.10**
    - For any valid limit/offset, /firs endpoint returns at most limit FIRs with non-overlapping pages
  
  - [x] 12.8 Write property test for status finalization
    - **Property 8: Status finalization**
    - **Validates: Requirements 9.8**
    - For any FIR in "draft" status, authenticate endpoint updates status to "finalized"
  
  - [x] 12.9 Write property test for unique file names
    - **Property 9: Unique file names**
    - **Validates: Requirements 10.4**
    - For any two file uploads, generated S3 keys are unique
  
  - [x] 12.10 Write property test for unique session IDs
    - **Property 10: Unique session IDs**
    - **Validates: Requirements 13.1**
    - For any two FIR generation requests, created session IDs are unique
  
  - [x] 12.11 Write property test for session data completeness
    - **Property 11: Session data completeness**
    - **Validates: Requirements 13.6**
    - For any completed session, session data contains all required fields
  
  - [x] 12.12 Write property test for session round trip
    - **Property 12: Session round trip**
    - **Validates: Requirements 13.7**
    - For any created session, polling session endpoint returns current session data
  
  - [x] 12.13 Write property test for error message security
    - **Property 13: Error message security**
    - **Validates: Requirements 14.7**
    - For any error response, error message does not contain sensitive information
  
  - [x] 12.14 Write property test for process response format
    - **Property 14: Process response format**
    - **Validates: Requirements 15.3**
    - For any valid /process request, response contains session_id field
  
  - [x] 12.15 Write property test for session response format
    - **Property 15: Session response format**
    - **Validates: Requirements 15.5**
    - For any valid /session request, response contains all required fields
  
  - [x] 12.16 Write property test for API authentication
    - **Property 16: API authentication**
    - **Validates: Requirements 15.10**
    - For any endpoint except /health, requests without valid API key are rejected with HTTP 401
  
  - [x] 12.17 Write property test for IPC section schema
    - **Property 17: IPC section schema**
    - **Validates: Requirements 17.2**
    - For any IPC section in database, record contains all required fields
  
  - [x] 12.18 Write property test for PDF generation
    - **Property 18: PDF generation**
    - **Validates: Requirements 19.1**
    - For any valid FIR content, PDF generation produces non-empty PDF document
  
  - [x] 12.19 Write property test for PDF field completeness
    - **Property 19: PDF field completeness**
    - **Validates: Requirements 19.2, 19.4-19.5**
    - For any generated PDF, document includes all 30 FIR template fields
  
  - [x] 12.20 Write property test for PDF URL response
    - **Property 20: PDF URL response**
    - **Validates: Requirements 19.9**
    - For any successful authenticate request, response contains valid pdf_url
  
  - [x] 12.21 Write property test for security headers
    - **Property 21: Security headers**
    - **Validates: Requirements 22.1-22.3**
    - For any API response, headers include required security headers
  
  - [x] 12.22 Write property test for audio file validation
    - **Property 22: Audio file validation**
    - **Validates: Requirements 23.1**
    - For any audio file with invalid extension, request is rejected with HTTP 400
  
  - [x] 12.23 Write property test for image file validation
    - **Property 23: Image file validation**
    - **Validates: Requirements 23.2**
    - For any image file with invalid extension, request is rejected with HTTP 400
  
  - [x] 12.24 Write property test for file size validation
    - **Property 24: File size validation**
    - **Validates: Requirements 23.3**
    - For any file larger than 10MB, request is rejected with HTTP 400
  
  - [x] 12.25 Write property test for content type validation
    - **Property 25: Content type validation**
    - **Validates: Requirements 23.4**
    - For any file with mismatched content type, request is rejected with HTTP 400
  
  - [x] 12.26 Write property test for invalid file rejection
    - **Property 26: Invalid file rejection**
    - **Validates: Requirements 23.6**
    - For any file that fails validation, system does not process file or generate FIR
  
  - [x] 12.27 Write property test for health check response format
    - **Property 27: Health check response format**
    - **Validates: Requirements 24.7**
    - For any /health request, response contains status field and checks dictionary

- [x] 13. Write unit tests for critical components
  - [x] 13.1 Write unit tests for configuration validation
    - Test missing required environment variables
    - Test default values for optional variables
    - Test configuration validation on startup
  
  - [x] 13.2 Write unit tests for file validation
    - Test valid audio file extensions
    - Test valid image file extensions
    - Test file size limits
    - Test content type validation
    - Test validation error messages
  
  - [x] 13.3 Write unit tests for FIR number generation
    - Test FIR number format (FIR-YYYYMMDD-XXXXX)
    - Test uniqueness of generated FIR numbers
  
  - [x] 13.4 Write unit tests for session management
    - Test session creation
    - Test session updates
    - Test session retrieval
    - Test session cleanup (older than 24 hours)
  
  - [x] 13.5 Write unit tests for error handling
    - Test AWS service error handling
    - Test database error handling
    - Test validation error handling
    - Test error message security (no sensitive data)
  
  - [x] 13.6 Write unit tests for rate limiting
    - Test rate limit enforcement (100 requests per minute)
    - Test rate limit reset after 1 minute
    - Test Retry-After header in 429 responses
    - Test /health endpoint exclusion from rate limiting

- [x] 14. Create deployment documentation
  - [x] 14.1 Create systemd service file for production deployment
    - Create afirgen.service file with proper configuration
    - Include restart policy and environment file path
    - _Requirements: 16.1-16.10_
  
  - [x] 14.2 Create IPC sections JSON file
    - Create ipc_sections.json with sample IPC sections
    - Include section_number, title, description, penalty fields
    - _Requirements: 17.3_
  
  - [x] 14.3 Update README.md with complete deployment guide
    - Add prerequisites section for both Windows (local) and Linux (EC2)
    - Add step-by-step local development instructions for Windows
    - Add step-by-step EC2 deployment instructions for Linux
    - Add production deployment with systemd
    - Add health check verification
    - Add troubleshooting section for both environments
    - _Requirements: 16.1-16.10_

- [x] 15. Configure frontend API endpoints
  - [x] 15.1 Identify frontend API configuration files
    - Locate frontend configuration files (config.js, .env, constants.js, etc.)
    - Identify all API endpoint references in frontend code
  
  - [x] 15.2 Update API base URL configuration
    - Update API base URL to support both local (http://localhost:8000) and EC2 (http://98.86.30.145:8000) environments
    - Add environment variable or configuration toggle for API URL
    - Ensure all API endpoints use the configured base URL
  
  - [x] 15.3 Verify endpoint compatibility
    - Ensure frontend endpoints match new backend structure:
      - POST /process (for FIR generation)
      - GET /session/{session_id} (for status polling)
      - POST /authenticate (for FIR finalization)
      - GET /fir/{fir_number} (for FIR retrieval)
      - GET /firs (for listing FIRs)
      - GET /health (for health checks)
    - Update any endpoint paths that don't match
    - Update request/response models if needed
  
  - [x] 15.4 Update API authentication
    - Ensure frontend sends X-API-Key header with all requests (except /health)
    - Update authentication configuration to use new API key
  
  - [x] 15.5 Test frontend-backend connectivity
    - Test all API endpoints from frontend
    - Verify request/response formats match
    - Test error handling and error messages
    - Test file uploads (audio and image)
  
  - [x] 15.6 Document frontend configuration changes
    - Add frontend configuration instructions to README.md
    - Document how to switch between local and EC2 environments
    - _Requirements: 15.1-15.10_

- [x] 16. Local testing on Windows (SKIPPED - ISP blocks MySQL port 3306)
  - [x] 16.1 Set up local development environment
    - Install Python 3.11+ on Windows
    - Create virtual environment
    - Install dependencies from requirements.txt
    - Configure .env file with local/test AWS credentials
  
  - [ ] 16.2 Test database connectivity
    - Test MySQL RDS connection from Windows
    - Verify SQLite sessions.db creation
    - Test database table initialization
  
  - [ ] 16.3 Test AWS service access
    - Test AWS Bedrock access from Windows
    - Test AWS Transcribe access from Windows
    - Test AWS Textract access from Windows
    - Test S3 bucket access from Windows
  
  - [ ] 16.4 Run local backend server
    - Start backend with: uvicorn agentv5:app --host 0.0.0.0 --port 8000
    - Verify health check: curl http://localhost:8000/health
    - Check logs for any errors
  
  - [ ] 16.5 Test FIR generation workflow locally
    - Test text input FIR generation
    - Test audio input FIR generation (if AWS Transcribe accessible)
    - Test image input FIR generation (if AWS Textract accessible)
    - Verify all 30 FIR fields are generated
    - Verify PDF generation works
  
  - [ ] 16.6 Test frontend integration locally
    - Run frontend application
    - Configure frontend to use http://localhost:8000
    - Test all frontend features with local backend
    - Verify end-to-end workflow
  
  - [ ] 16.7 Document local testing results
    - Document any Windows-specific issues encountered
    - Document solutions or workarounds
    - Update README.md with Windows testing notes

- [x] 17. Deploy to EC2 after successful local testing
  - [x] 17.1 Commit and push changes to git
    - Commit all changes to git repository
    - Push to remote repository
    - Verify all files are committed (agentv5.py, requirements.txt, .env.example, README.md, ipc_sections.json)
  
  - [x] 17.2 Deploy to EC2 via git clone
    - SSH into EC2 instance (18.206.148.182)
    - Navigate to deployment directory (/opt/afirgen-backend)
    - Clone or pull latest code from git repository
    - Create virtual environment if not exists
    - Install dependencies: pip install -r requirements.txt
  
  - [x] 17.3 Configure EC2 environment
    - Create .env file with production configuration
    - Set AWS_REGION=us-east-1
    - Set S3_BUCKET_NAME to production bucket
    - Set DB_HOST to RDS endpoint (afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com)
    - Set DB_PASSWORD=Prathiush12.
    - Set API_KEY to production key
    - Verify all required environment variables are set
  
  - [x] 17.4 Initialize EC2 database
    - Run backend once to create database tables
    - Verify fir_records and ipc_sections tables created in MySQL
    - Verify sessions.db created in application directory
    - Load IPC sections from JSON file
  
  - [x] 17.5 Start backend service on EC2
    - Start backend with: uvicorn agentv5:app --host 0.0.0.0 --port 8000
    - Or configure systemd service and start with: sudo systemctl start afirgen
    - Verify health check: curl http://localhost:8000/health
    - Check logs for any errors
  
  - [x] 17.6 Test EC2 deployment
    - Test health check from external: curl http://18.206.148.182:8000/health
    - Test FIR generation from external
    - Verify all AWS services accessible (Bedrock, Transcribe, Textract, S3, RDS)
  
  - [x] 17.7 Configure frontend for EC2
    - Update frontend API base URL to http://18.206.148.182:8000
    - Test frontend with EC2 backend
    - Verify end-to-end workflow
  
  - [x] 17.8 Monitor EC2 deployment
    - Monitor logs: tail -f logs/main_backend.log
    - Monitor systemd service: sudo journalctl -u afirgen -f
    - Check for any errors or issues
    - Verify FIR generation success rate

- [ ] 18. Final checkpoint - Verify deployment readiness
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The implementation uses Python with FastAPI framework
- All AWS operations use boto3 SDK
- Database operations use mysql-connector-python for MySQL and sqlite3 for sessions
- PDF generation uses reportlab library
