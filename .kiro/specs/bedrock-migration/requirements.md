# Requirements Document: AFIRGen Bedrock Migration

## Introduction

This document specifies requirements for migrating the AFIRGen (Automated FIR Generation) system from self-hosted GGUF models on GPU instances to AWS managed services using Amazon Bedrock architecture. The migration aims to reduce operational costs from ~$1.21/hour (g5.2xlarge GPU instance) to pay-per-use pricing while maintaining existing functionality, security standards, and role-based access control.

The current system uses self-hosted Whisper for audio transcription, Donut OCR for document processing, custom legal models for FIR generation, and ChromaDB for vector storage. The target architecture replaces these with Amazon Transcribe, Amazon Textract, Amazon Bedrock (Claude 3 Sonnet), and either OpenSearch Serverless or Aurora PostgreSQL with pgvector extension.

## Glossary

- **AFIRGen**: Automated First Information Report Generation system
- **FIR**: First Information Report - official police document in India
- **GGUF**: GPT-Generated Unified Format for model files
- **Bedrock**: Amazon Bedrock - AWS managed service for foundation models
- **Transcribe**: Amazon Transcribe - AWS speech-to-text service
- **Textract**: Amazon Textract - AWS document analysis service
- **Claude**: Anthropic's Claude 3 Sonnet large language model
- **Titan_Embeddings**: Amazon Titan Embeddings model for vector generation
- **OpenSearch_Serverless**: AWS managed OpenSearch service without infrastructure management
- **Aurora_pgvector**: Amazon Aurora PostgreSQL with pgvector extension for vector storage
- **IPC**: Indian Penal Code sections stored in vector database
- **Backend**: FastAPI-based Python backend service
- **RDS**: Amazon Relational Database Service for MySQL
- **S3**: Amazon Simple Storage Service for file storage
- **IAM**: AWS Identity and Access Management
- **KMS**: AWS Key Management Service for encryption
- **VPC**: Virtual Private Cloud for network isolation

## Requirements

### Requirement 1: Audio Transcription Migration

**User Story:** As a police officer, I want to upload audio complaints in Indian languages, so that they are automatically transcribed into text for FIR generation.

#### Acceptance Criteria

1. WHEN an audio file is uploaded, THE Backend SHALL validate the file format against supported formats (WAV, MP3, MPEG)
2. WHEN a valid audio file is received, THE Backend SHALL upload it to S3 with SSE-KMS encryption
3. WHEN the audio file is stored in S3, THE Backend SHALL invoke Transcribe with the S3 file location
4. THE Transcribe SHALL support Hindi, English, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, and Punjabi languages
5. WHEN transcription completes, THE Backend SHALL retrieve the transcript text from Transcribe
6. WHEN transcription fails, THE Backend SHALL retry up to 2 times with exponential backoff
7. WHEN all retries fail, THE Backend SHALL return a descriptive error message to the user
8. THE Backend SHALL delete temporary audio files from S3 after successful transcription
9. THE Backend SHALL record transcription latency and success metrics to CloudWatch

### Requirement 2: Document OCR Migration

**User Story:** As a police officer, I want to upload scanned documents or images containing complaint text, so that the text is automatically extracted for FIR generation.

#### Acceptance Criteria

1. WHEN an image file is uploaded, THE Backend SHALL validate the file format against supported formats (JPEG, PNG)
2. WHEN a valid image file is received, THE Backend SHALL upload it to S3 with SSE-KMS encryption
3. WHEN the image file is stored in S3, THE Backend SHALL invoke Textract with the S3 file location
4. THE Textract SHALL extract both plain text and structured form data from the document
5. WHEN extraction completes, THE Backend SHALL retrieve the extracted text from Textract
6. WHEN extraction fails, THE Backend SHALL retry up to 2 times with exponential backoff
7. WHEN all retries fail, THE Backend SHALL return a descriptive error message to the user
8. THE Backend SHALL delete temporary image files from S3 after successful extraction
9. THE Backend SHALL record OCR latency and success metrics to CloudWatch

### Requirement 3: Legal Text Processing with Bedrock

**User Story:** As a system administrator, I want the legal text processing to use Amazon Bedrock Claude 3 Sonnet, so that we eliminate GPU infrastructure costs while maintaining processing quality.

#### Acceptance Criteria

1. THE Backend SHALL initialize a Bedrock client with IAM role-based authentication
2. WHEN raw complaint text is received, THE Backend SHALL invoke Claude via Bedrock to convert it to formal legal narrative
3. THE Claude SHALL generate a formal legal narrative with maximum 3 sentences
4. WHEN formal narrative is generated, THE Backend SHALL invoke Claude via Bedrock to extract structured metadata
5. THE Claude SHALL extract incident type, date, location, accused details, and victim details from the narrative
6. THE Backend SHALL validate that extracted metadata contains all required fields
7. WHEN Bedrock API calls fail, THE Backend SHALL retry up to 2 times with exponential backoff
8. WHEN Bedrock returns rate limit errors, THE Backend SHALL implement exponential backoff with jitter
9. THE Backend SHALL record Bedrock inference latency and token usage metrics to CloudWatch
10. THE Backend SHALL limit concurrent Bedrock API calls to 10 using a semaphore

### Requirement 4: Vector Database Migration

**User Story:** As a system administrator, I want to migrate from ChromaDB to AWS managed vector storage, so that we have a production-ready, scalable vector database solution.

#### Acceptance Criteria

1. THE Backend SHALL support both OpenSearch_Serverless and Aurora_pgvector as vector storage options via configuration
2. WHEN the system initializes, THE Backend SHALL connect to the configured vector database
3. WHEN IPC section text needs to be embedded, THE Backend SHALL invoke Titan_Embeddings via Bedrock
4. THE Titan_Embeddings SHALL generate 1536-dimensional embedding vectors
5. WHEN embeddings are generated, THE Backend SHALL store them in the vector database with associated IPC section metadata
6. WHEN a legal query is received, THE Backend SHALL generate query embeddings using Titan_Embeddings
7. WHEN query embeddings are generated, THE Backend SHALL perform similarity search in the vector database
8. THE Backend SHALL retrieve the top 5 most relevant IPC sections based on cosine similarity
9. WHEN vector database operations fail, THE Backend SHALL retry up to 2 times with exponential backoff
10. THE Backend SHALL record vector database operation latency and success metrics to CloudWatch

### Requirement 5: FIR Generation with RAG

**User Story:** As a police officer, I want the system to generate complete FIRs with relevant IPC sections, so that I can quickly file accurate legal reports.

#### Acceptance Criteria

1. WHEN formal narrative and metadata are available, THE Backend SHALL perform vector similarity search for relevant IPC sections
2. WHEN relevant IPC sections are retrieved, THE Backend SHALL construct a RAG prompt combining narrative and IPC sections
3. WHEN the RAG prompt is constructed, THE Backend SHALL invoke Claude via Bedrock to generate the complete FIR
4. THE Claude SHALL generate a structured FIR in the standard format with all required fields
5. THE Backend SHALL validate that the generated FIR contains complainant details, incident details, legal provisions, and investigation details
6. WHEN FIR generation completes, THE Backend SHALL store the FIR in MySQL RDS
7. THE Backend SHALL enforce role-based access control when storing FIR data
8. WHEN FIR generation fails, THE Backend SHALL return a descriptive error message with the failure reason
9. THE Backend SHALL record end-to-end FIR generation latency to CloudWatch

### Requirement 6: AWS Service Integration

**User Story:** As a system administrator, I want all AWS service integrations to use IAM roles and follow security best practices, so that credentials are never exposed in code or configuration files.

#### Acceptance Criteria

1. THE Backend SHALL use IAM roles for all AWS service authentication
2. THE Backend SHALL NOT contain hardcoded AWS credentials in source code or configuration files
3. WHEN the Backend initializes, THE Backend SHALL verify IAM role permissions for Bedrock, Transcribe, Textract, S3, and the vector database
4. THE Backend SHALL use boto3 SDK for all AWS service interactions
5. WHEN AWS API calls fail with permission errors, THE Backend SHALL log detailed error messages with the missing permission
6. THE Backend SHALL configure AWS SDK retry behavior with exponential backoff and jitter
7. THE Backend SHALL set appropriate timeouts for all AWS service calls
8. THE Backend SHALL enable AWS X-Ray tracing for all AWS service calls

### Requirement 7: Cost Optimization

**User Story:** As a system administrator, I want the migration to minimize costs, so that the demo environment is affordable to operate.

#### Acceptance Criteria

1. THE Backend SHALL run on t3.small or t3.medium EC2 instances instead of GPU instances
2. THE Backend SHALL delete temporary files from S3 after processing to minimize storage costs
3. THE Backend SHALL implement request batching where possible to reduce API call costs
4. THE Backend SHALL use S3 lifecycle policies to automatically delete files older than 7 days
5. THE Backend SHALL configure OpenSearch_Serverless with minimum OCU capacity if used
6. THE Backend SHALL use Aurora_Serverless v2 with minimum ACU capacity if Aurora_pgvector is used
7. THE Backend SHALL implement caching for frequently accessed IPC sections to reduce embedding API calls
8. THE Backend SHALL log cost-related metrics to CloudWatch for monitoring

### Requirement 8: Backward Compatibility

**User Story:** As a developer, I want the migration to maintain the existing FastAPI backend structure and API contracts, so that frontend applications continue to work without changes.

#### Acceptance Criteria

1. THE Backend SHALL maintain all existing API endpoint paths and HTTP methods
2. THE Backend SHALL maintain all existing request and response schemas
3. THE Backend SHALL maintain all existing error response formats
4. THE Backend SHALL maintain the existing session management mechanism
5. THE Backend SHALL maintain the existing role-based access control implementation
6. THE Backend SHALL maintain the existing MySQL RDS schema for FIR storage
7. THE Backend SHALL maintain the existing S3 bucket structure for file storage
8. THE Backend SHALL maintain the existing CloudWatch metrics and logging structure

### Requirement 9: Error Handling and Resilience

**User Story:** As a system administrator, I want robust error handling for all AWS service integrations, so that transient failures do not cause data loss or system crashes.

#### Acceptance Criteria

1. WHEN Transcribe returns a throttling error, THE Backend SHALL implement exponential backoff with jitter
2. WHEN Textract returns a throttling error, THE Backend SHALL implement exponential backoff with jitter
3. WHEN Bedrock returns a throttling error, THE Backend SHALL implement exponential backoff with jitter
4. WHEN any AWS service returns a 5xx error, THE Backend SHALL retry up to 2 times
5. WHEN vector database operations fail, THE Backend SHALL retry up to 2 times
6. THE Backend SHALL implement circuit breakers for each AWS service with failure threshold of 5
7. WHEN a circuit breaker opens, THE Backend SHALL return a service unavailable error
8. WHEN a circuit breaker is half-open, THE Backend SHALL allow 3 test requests
9. THE Backend SHALL log all AWS service errors with correlation IDs for debugging

### Requirement 10: Migration Testing

**User Story:** As a developer, I want comprehensive tests for the Bedrock migration, so that I can verify functionality before deploying to production.

#### Acceptance Criteria

1. THE Backend SHALL include unit tests for Transcribe integration with mocked AWS responses
2. THE Backend SHALL include unit tests for Textract integration with mocked AWS responses
3. THE Backend SHALL include unit tests for Bedrock Claude integration with mocked AWS responses
4. THE Backend SHALL include unit tests for Titan_Embeddings integration with mocked AWS responses
5. THE Backend SHALL include unit tests for vector database operations with mocked database responses
6. THE Backend SHALL include integration tests for end-to-end FIR generation with real AWS services
7. THE Backend SHALL include property-based tests for round-trip embedding generation and retrieval
8. THE Backend SHALL include performance tests comparing latency against the GGUF baseline
9. THE Backend SHALL include cost estimation tests to validate pay-per-use pricing assumptions

### Requirement 11: Configuration Management

**User Story:** As a system administrator, I want all AWS service endpoints and parameters to be configurable, so that I can easily switch between development, staging, and production environments.

#### Acceptance Criteria

1. THE Backend SHALL read AWS region from environment variable AWS_REGION
2. THE Backend SHALL read Bedrock model ID from environment variable BEDROCK_MODEL_ID with default "anthropic.claude-3-sonnet-20240229-v1:0"
3. THE Backend SHALL read Titan Embeddings model ID from environment variable BEDROCK_EMBEDDINGS_MODEL_ID with default "amazon.titan-embed-text-v1"
4. THE Backend SHALL read vector database type from environment variable VECTOR_DB_TYPE with options "opensearch" or "aurora_pgvector"
5. THE Backend SHALL read S3 bucket name from environment variable S3_BUCKET_NAME
6. THE Backend SHALL read Transcribe language codes from environment variable TRANSCRIBE_LANGUAGES with default "hi-IN,en-IN"
7. THE Backend SHALL validate all required environment variables on startup
8. WHEN required environment variables are missing, THE Backend SHALL log an error and exit with non-zero status code

### Requirement 12: Monitoring and Observability

**User Story:** As a system administrator, I want detailed monitoring of all AWS service interactions, so that I can troubleshoot issues and optimize performance.

#### Acceptance Criteria

1. THE Backend SHALL emit CloudWatch metrics for Transcribe request count, latency, and error rate
2. THE Backend SHALL emit CloudWatch metrics for Textract request count, latency, and error rate
3. THE Backend SHALL emit CloudWatch metrics for Bedrock request count, latency, token usage, and error rate
4. THE Backend SHALL emit CloudWatch metrics for vector database operation count, latency, and error rate
5. THE Backend SHALL emit CloudWatch metrics for S3 upload and download operations
6. THE Backend SHALL create X-Ray traces for all FIR generation requests
7. THE Backend SHALL include AWS service call details in X-Ray subsegments
8. THE Backend SHALL log all AWS service requests and responses in structured JSON format
9. THE Backend SHALL include correlation IDs in all log messages for request tracing

### Requirement 13: Security and Compliance

**User Story:** As a security officer, I want the migration to maintain existing security standards, so that sensitive FIR data remains protected.

#### Acceptance Criteria

1. THE Backend SHALL encrypt all S3 uploads using SSE-KMS with customer-managed keys
2. THE Backend SHALL encrypt all data in transit using TLS 1.2 or higher
3. THE Backend SHALL encrypt vector database connections using TLS
4. THE Backend SHALL NOT log sensitive data such as complainant details or incident descriptions
5. THE Backend SHALL enforce IAM policies with least privilege access for all AWS services
6. THE Backend SHALL run in private subnets with no direct internet access
7. THE Backend SHALL access AWS services via VPC endpoints where available
8. THE Backend SHALL maintain existing MySQL RDS encryption at rest
9. THE Backend SHALL maintain existing role-based access control for FIR data

### Requirement 14: Data Migration

**User Story:** As a system administrator, I want to migrate existing IPC section embeddings from ChromaDB to the new vector database, so that the system has complete legal reference data on launch.

#### Acceptance Criteria

1. THE Backend SHALL include a migration script to export IPC sections from ChromaDB
2. THE Backend SHALL generate new embeddings for all IPC sections using Titan_Embeddings
3. THE Backend SHALL import IPC sections and embeddings into the target vector database
4. THE Backend SHALL verify embedding count matches between source and target databases
5. THE Backend SHALL perform sample similarity searches to validate migration correctness
6. WHEN migration fails, THE Backend SHALL rollback partial imports
7. THE Backend SHALL log migration progress and completion status
8. THE Backend SHALL support incremental migration for large datasets

### Requirement 15: Indian Language Support

**User Story:** As a police officer in a regional station, I want to file complaints in my local language, so that language barriers do not prevent accurate reporting.

#### Acceptance Criteria

1. THE Transcribe SHALL support Hindi language with language code "hi-IN"
2. THE Transcribe SHALL support Tamil language with language code "ta-IN"
3. THE Transcribe SHALL support Telugu language with language code "te-IN"
4. THE Transcribe SHALL support Bengali language with language code "bn-IN"
5. THE Transcribe SHALL support Marathi language with language code "mr-IN"
6. THE Transcribe SHALL support Gujarati language with language code "gu-IN"
7. THE Transcribe SHALL support Kannada language with language code "kn-IN"
8. THE Transcribe SHALL support Malayalam language with language code "ml-IN"
9. THE Transcribe SHALL support Punjabi language with language code "pa-IN"
10. THE Backend SHALL auto-detect language from audio metadata when language is not specified
11. WHEN language detection fails, THE Backend SHALL default to Hindi ("hi-IN")

### Requirement 16: Rollback Strategy

**User Story:** As a system administrator, I want a clear rollback strategy, so that I can quickly revert to GGUF models if the Bedrock migration encounters critical issues.

#### Acceptance Criteria

1. THE Backend SHALL support a feature flag ENABLE_BEDROCK to toggle between GGUF and Bedrock implementations
2. WHEN ENABLE_BEDROCK is false, THE Backend SHALL use existing GGUF model servers
3. WHEN ENABLE_BEDROCK is true, THE Backend SHALL use Bedrock services
4. THE Backend SHALL maintain both GGUF and Bedrock code paths during migration period
5. THE Backend SHALL log which implementation is active on startup
6. THE Backend SHALL support runtime switching between implementations without restart
7. THE Backend SHALL maintain identical API contracts for both implementations
8. THE Backend SHALL include deployment scripts for both architectures

### Requirement 17: Performance Requirements

**User Story:** As a police officer, I want FIR generation to complete within reasonable time, so that I can efficiently process multiple complaints.

#### Acceptance Criteria

1. WHEN processing audio files, THE Backend SHALL complete transcription within 3 minutes for files up to 5 minutes long
2. WHEN processing image files, THE Backend SHALL complete OCR within 30 seconds for standard document images
3. WHEN generating legal narratives, THE Backend SHALL complete Claude inference within 10 seconds
4. WHEN performing vector similarity search, THE Backend SHALL return results within 2 seconds
5. WHEN generating complete FIRs, THE Backend SHALL complete end-to-end processing within 5 minutes
6. THE Backend SHALL support 10 concurrent FIR generation requests without degradation
7. THE Backend SHALL maintain 99% success rate for FIR generation under normal load

### Requirement 18: Documentation Requirements

**User Story:** As a developer, I want comprehensive documentation for the Bedrock migration, so that I can understand, maintain, and extend the system.

#### Acceptance Criteria

1. THE Backend SHALL include README documentation describing the Bedrock architecture
2. THE Backend SHALL include API documentation for all modified endpoints
3. THE Backend SHALL include deployment guide for Bedrock-based infrastructure
4. THE Backend SHALL include configuration guide for all environment variables
5. THE Backend SHALL include troubleshooting guide for common AWS service errors
6. THE Backend SHALL include cost estimation guide with example calculations
7. THE Backend SHALL include migration guide for transitioning from GGUF to Bedrock
8. THE Backend SHALL include code comments explaining AWS service integration patterns
