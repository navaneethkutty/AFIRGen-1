# AFIRGen Bedrock Environment Configuration Guide

This guide explains how to configure environment variables for the AFIRGen Bedrock migration.

## Overview

The Bedrock migration introduces AWS managed services (Bedrock, Transcribe, Textract, OpenSearch/Aurora) to replace self-hosted GGUF models. This requires additional environment variables for AWS service configuration.

## Files

- `.env.bedrock` - Complete environment configuration for Bedrock architecture
- `scripts/validate-env.py` - Validation script to verify all required variables are present

## Quick Start

### 1. Copy the Bedrock Environment File

```bash
cp .env.bedrock .env
```

### 2. Update Required Variables

Edit `.env` and update the following placeholder values:

#### AWS Configuration
```bash
AWS_REGION=us-east-1                    # Your AWS region
S3_BUCKET_NAME=your-bucket-name         # S3 bucket for temporary files
```

#### Vector Database (OpenSearch)
If using OpenSearch Serverless:
```bash
VECTOR_DB_TYPE=opensearch
OPENSEARCH_ENDPOINT=https://your-collection-id.region.aoss.amazonaws.com
```

#### Vector Database (Aurora PostgreSQL)
If using Aurora with pgvector:
```bash
VECTOR_DB_TYPE=aurora_pgvector
AURORA_HOST=your-cluster.cluster-xxxxx.region.rds.amazonaws.com
AURORA_PASSWORD=your-secure-password
```

#### Security
```bash
API_KEY=your-secure-32-character-api-key-here
FIR_AUTH_KEY=your-secure-auth-key-here
```

### 3. Validate Configuration

Run the validation script to ensure all required variables are properly configured:

```bash
python scripts/validate-env.py --env-file .env
```

The script will:
- ✓ Check all required variables are present
- ✓ Validate variable formats and values
- ✓ Verify AWS region format
- ✓ Check vector database configuration
- ⚠ Warn about placeholder values
- ✗ Report errors for missing or invalid values

### 4. Strict Validation (Optional)

To treat warnings as errors (recommended for production):

```bash
python scripts/validate-env.py --env-file .env --strict
```

## Configuration Sections

### Feature Flag

```bash
ENABLE_BEDROCK=true
```

Set to `true` to use Bedrock services, `false` to use GGUF models. This allows easy rollback if needed.

### AWS Services

#### Amazon Bedrock
- `BEDROCK_MODEL_ID` - Claude 3 Sonnet model ID for legal text processing
- `BEDROCK_EMBEDDINGS_MODEL_ID` - Titan Embeddings model ID for vector generation
- `BEDROCK_MAX_CONCURRENT_CALLS` - Maximum concurrent API calls (default: 10)
- `BEDROCK_TIMEOUT` - API timeout in seconds (default: 60)

#### Amazon Transcribe
- `TRANSCRIBE_LANGUAGES` - Comma-separated list of supported language codes
- `TRANSCRIBE_DEFAULT_LANGUAGE` - Default language when auto-detection fails
- `TRANSCRIBE_TIMEOUT` - Job timeout in seconds (default: 300)

Supported languages:
- `hi-IN` - Hindi
- `en-IN` - English (India)
- `ta-IN` - Tamil
- `te-IN` - Telugu
- `bn-IN` - Bengali
- `mr-IN` - Marathi
- `gu-IN` - Gujarati
- `kn-IN` - Kannada
- `ml-IN` - Malayalam
- `pa-IN` - Punjabi

#### Amazon Textract
- `TEXTRACT_TIMEOUT` - API timeout in seconds (default: 60)
- `TEXTRACT_EXTRACT_FORMS` - Enable form data extraction (true/false)

### Vector Database

#### Common Settings
- `VECTOR_DB_TYPE` - Database type: `opensearch` or `aurora_pgvector`
- `VECTOR_DB_INDEX_NAME` - Index/table name for IPC sections
- `VECTOR_DB_EMBEDDING_DIMENSION` - Embedding dimension (1536 for Titan)
- `VECTOR_DB_TOP_K` - Number of results to return from similarity search

#### OpenSearch Serverless
- `OPENSEARCH_ENDPOINT` - OpenSearch Serverless collection endpoint
- `OPENSEARCH_INDEX_NAME` - Index name
- `OPENSEARCH_TIMEOUT` - Connection timeout in seconds

#### Aurora PostgreSQL with pgvector
- `AURORA_HOST` - Aurora cluster endpoint
- `AURORA_PORT` - PostgreSQL port (default: 5432)
- `AURORA_DATABASE` - Database name
- `AURORA_USER` - Database username
- `AURORA_PASSWORD` - Database password (use AWS Secrets Manager in production)
- `AURORA_TABLE_NAME` - Table name for IPC sections
- `AURORA_POOL_SIZE` - Connection pool size
- `AURORA_TIMEOUT` - Connection timeout in seconds
- `AURORA_SSL` - Enable SSL (true/false)

### Retry and Resilience

- `MAX_RETRIES` - Maximum retry attempts for AWS service calls (default: 2)
- `RETRY_BASE_DELAY` - Base delay for exponential backoff in seconds (default: 1.0)
- `RETRY_MAX_DELAY` - Maximum delay for exponential backoff in seconds (default: 60.0)
- `CIRCUIT_BREAKER_FAILURE_THRESHOLD` - Failures before circuit opens (default: 5)
- `CIRCUIT_BREAKER_RECOVERY_TIMEOUT` - Seconds before attempting recovery (default: 60)
- `CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS` - Test requests in half-open state (default: 3)

### Monitoring and Observability

- `CLOUDWATCH_NAMESPACE` - CloudWatch metrics namespace (default: AFIRGen/Bedrock)
- `ENABLE_XRAY_TRACING` - Enable AWS X-Ray distributed tracing (true/false)
- `ENABLE_STRUCTURED_LOGGING` - Enable structured JSON logging (true/false)
- `LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Security

- `KMS_KEY_ID` - KMS key ID for S3 encryption (optional, uses AWS managed key if empty)
- `USE_VPC_ENDPOINTS` - Use VPC endpoints for AWS services (true/false)

### Performance

- `MAX_AUDIO_FILE_SIZE_MB` - Maximum audio file size in MB (default: 100)
- `MAX_IMAGE_FILE_SIZE_MB` - Maximum image file size in MB (default: 10)
- `S3_LIFECYCLE_DAYS` - Delete S3 files older than N days (default: 7)
- `IPC_CACHE_SIZE` - Number of IPC queries to cache (default: 100)
- `CACHE_TTL` - Cache time-to-live in seconds (default: 3600)

## Environment-Specific Configuration

### Development

```bash
ENVIRONMENT=development
ENABLE_DEBUG=true
LOG_LEVEL=DEBUG
ENABLE_XRAY_TRACING=false
USE_VPC_ENDPOINTS=false
```

### Staging

```bash
ENVIRONMENT=staging
ENABLE_DEBUG=false
LOG_LEVEL=INFO
ENABLE_XRAY_TRACING=true
USE_VPC_ENDPOINTS=true
```

### Production

```bash
ENVIRONMENT=production
ENABLE_DEBUG=false
LOG_LEVEL=WARNING
ENABLE_XRAY_TRACING=true
USE_VPC_ENDPOINTS=true
ENFORCE_HTTPS=true
USE_AWS_SECRETS=true
```

## Security Best Practices

### 1. Use AWS Secrets Manager in Production

Instead of storing sensitive values in `.env`, use AWS Secrets Manager:

```bash
USE_AWS_SECRETS=true
```

The application will automatically fetch secrets from AWS Secrets Manager with fallback to environment variables.

### 2. Rotate API Keys Regularly

Generate secure API keys:

```bash
# Generate a secure 32-character API key
openssl rand -base64 32
```

### 3. Use IAM Roles

The application uses IAM roles for AWS service authentication. Never hardcode AWS credentials in environment files.

### 4. Enable Encryption

- S3: SSE-KMS encryption (automatic)
- RDS: Encryption at rest (configured in Terraform)
- Aurora: Encryption at rest (configured in Terraform)
- Transit: TLS 1.2+ for all connections

### 5. Use VPC Endpoints

Enable VPC endpoints to keep AWS service traffic within your VPC:

```bash
USE_VPC_ENDPOINTS=true
```

## Validation Script Details

The `validate-env.py` script performs comprehensive validation:

### Checks Performed

1. **Required Variables** - Ensures all required variables are present
2. **Format Validation** - Validates AWS region format, URLs, etc.
3. **Type Validation** - Checks boolean, integer, and choice values
4. **Range Validation** - Verifies integers are within acceptable ranges
5. **Placeholder Detection** - Warns about placeholder values
6. **Security Checks** - Validates API key length and format

### Exit Codes

- `0` - All validations passed
- `1` - Validation failed (errors found)
- `1` - Strict mode with warnings

### Example Output

```
AFIRGen Bedrock Environment Validation
Environment file: .env.bedrock

✓ Loaded 64 environment variables

Validating Bedrock Configuration...
Validating Transcribe Configuration...
Validating Textract Configuration...
Validating Vector Database Configuration...
  Validating OpenSearch Serverless settings...
Validating Retry and Resilience Configuration...
Validating Monitoring Configuration...
Validating Security Configuration...
Validating Performance Configuration...

======================================================================
Validation Summary
======================================================================

✓ Passed: 34
✗ Failed: 0
⚠ Warnings: 0

======================================================================
✓ All validations passed!
```

## Troubleshooting

### Validation Errors

**Error: Missing required variable**
- Ensure the variable is present in your `.env` file
- Check for typos in variable names

**Error: Invalid value for VECTOR_DB_TYPE**
- Must be either `opensearch` or `aurora_pgvector`

**Error: API_KEY contains placeholder value**
- Generate a secure API key and update the value

**Error: OPENSEARCH_ENDPOINT must start with 'https://'**
- Ensure the endpoint URL starts with `https://`

### Warnings

**Warning: OPENSEARCH_ENDPOINT contains placeholder value**
- Update with your actual OpenSearch Serverless collection endpoint

**Warning: AWS_REGION does not match standard format**
- Verify the region code is correct (e.g., `us-east-1`, `eu-west-1`)

**Warning: API_KEY length is below recommended minimum**
- Use at least 32 characters for API keys

## Migration from GGUF

To migrate from GGUF to Bedrock:

1. Keep existing `.env` file as backup
2. Copy `.env.bedrock` to `.env`
3. Update AWS-specific variables
4. Set `ENABLE_BEDROCK=true`
5. Validate configuration
6. Deploy infrastructure (Terraform)
7. Run vector database migration
8. Test endpoints

To rollback:

1. Set `ENABLE_BEDROCK=false`
2. Restart application

## Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Amazon Transcribe Documentation](https://docs.aws.amazon.com/transcribe/)
- [Amazon Textract Documentation](https://docs.aws.amazon.com/textract/)
- [OpenSearch Serverless Documentation](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html)
- [Aurora PostgreSQL with pgvector](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.VectorDB.html)

## Support

For issues or questions:
1. Check validation output for specific errors
2. Review this documentation
3. Check AWS service quotas and limits
4. Verify IAM permissions
5. Review CloudWatch logs for runtime errors
