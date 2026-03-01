# Bedrock Configuration Guide

Complete reference for all environment variables and configuration options for AFIRGen Bedrock architecture.

## Table of Contents

- [Overview](#overview)
- [AWS Configuration](#aws-configuration)
- [Bedrock Configuration](#bedrock-configuration)
- [Vector Database Configuration](#vector-database-configuration)
- [Storage Configuration](#storage-configuration)
- [Database Configuration](#database-configuration)
- [Application Configuration](#application-configuration)
- [Retry and Resilience Configuration](#retry-and-resilience-configuration)
- [Caching Configuration](#caching-configuration)
- [Monitoring Configuration](#monitoring-configuration)
- [Security Configuration](#security-configuration)
- [Rate Limiting Configuration](#rate-limiting-configuration)
- [Configuration Validation](#configuration-validation)
- [Environment-Specific Configurations](#environment-specific-configurations)

---

## Overview

The Bedrock architecture uses environment variables for all configuration. This approach:
- ✅ Separates configuration from code
- ✅ Enables easy environment switching (dev/staging/prod)
- ✅ Supports feature flags for gradual rollout
- ✅ Keeps sensitive data out of version control

**Configuration File:** `.env.bedrock`

**Validation:** Run `python scripts/validate-env.py` to verify all required variables are set correctly.

---

## AWS Configuration

### AWS_REGION
**Required:** Yes  
**Default:** None  
**Description:** AWS region where all services are deployed  
**Valid Values:** Any AWS region (e.g., `us-east-1`, `ap-south-1`)  
**Example:** `AWS_REGION=us-east-1`

**Notes:**
- Must match the region where Bedrock models are available
- Claude 3 Sonnet is available in: us-east-1, us-west-2, ap-southeast-1, ap-northeast-1, eu-central-1
- Affects latency and data transfer costs

### AWS_DEFAULT_REGION
**Required:** Yes  
**Default:** None  
**Description:** Default region for AWS SDK (should match AWS_REGION)  
**Example:** `AWS_DEFAULT_REGION=us-east-1`

---

## Bedrock Configuration

### BEDROCK_MODEL_ID
**Required:** Yes  
**Default:** `anthropic.claude-3-sonnet-20240229-v1:0`  
**Description:** Amazon Bedrock model ID for Claude 3 Sonnet  
**Valid Values:**
- `anthropic.claude-3-sonnet-20240229-v1:0` (recommended)
- `anthropic.claude-3-haiku-20240307-v1:0` (faster, cheaper)
- `anthropic.claude-3-opus-20240229-v1:0` (more capable, expensive)

**Example:** `BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0`

**Pricing (per 1K tokens):**
- Sonnet: $0.003 input, $0.015 output
- Haiku: $0.00025 input, $0.00125 output
- Opus: $0.015 input, $0.075 output

### BEDROCK_EMBEDDINGS_MODEL_ID
**Required:** Yes  
**Default:** `amazon.titan-embed-text-v1`  
**Description:** Amazon Bedrock model ID for Titan Embeddings  
**Valid Values:**
- `amazon.titan-embed-text-v1` (1536 dimensions)
- `amazon.titan-embed-text-v2` (1024 dimensions, newer)

**Example:** `BEDROCK_EMBEDDINGS_MODEL_ID=amazon.titan-embed-text-v1`

**Pricing:** $0.0001 per 1K tokens

### ENABLE_BEDROCK
**Required:** Yes  
**Default:** `true`  
**Description:** Feature flag to enable/disable Bedrock architecture  
**Valid Values:** `true`, `false`  
**Example:** `ENABLE_BEDROCK=true`

**Notes:**
- When `false`, system uses GGUF models (requires GPU instance)
- When `true`, system uses Bedrock services
- Can be changed without code deployment for quick rollback

---

## Vector Database Configuration

### VECTOR_DB_TYPE
**Required:** Yes  
**Default:** None  
**Description:** Type of vector database to use  
**Valid Values:** `opensearch`, `aurora_pgvector`  
**Example:** `VECTOR_DB_TYPE=opensearch`

**Comparison:**

| Feature | OpenSearch Serverless | Aurora pgvector |
|---------|----------------------|-----------------|
| **Cost** | ~$350/month (2 OCU) | ~$50/month (Serverless v2) |
| **Performance** | Faster for large datasets | Good for small-medium datasets |
| **Scalability** | Auto-scaling | Manual scaling |
| **Setup** | Simpler | Requires PostgreSQL knowledge |
| **Recommendation** | Production, high-volume | Development, cost-sensitive |

### VECTOR_DB_ENDPOINT
**Required:** Yes  
**Default:** None  
**Description:** Endpoint URL for vector database  
**Example (OpenSearch):** `VECTOR_DB_ENDPOINT=https://abc123.us-east-1.aoss.amazonaws.com`  
**Example (Aurora):** `VECTOR_DB_ENDPOINT=afirgen-vectors.cluster-abc123.us-east-1.rds.amazonaws.com`

### VECTOR_DB_INDEX_NAME
**Required:** No  
**Default:** `ipc_sections`  
**Description:** Index/table name for IPC sections  
**Example:** `VECTOR_DB_INDEX_NAME=ipc_sections`

### OpenSearch-Specific Configuration

#### OPENSEARCH_REGION
**Required:** Yes (if using OpenSearch)  
**Default:** Same as AWS_REGION  
**Description:** AWS region for OpenSearch Serverless  
**Example:** `OPENSEARCH_REGION=us-east-1`

### Aurora pgvector-Specific Configuration

#### PG_HOST
**Required:** Yes (if using Aurora pgvector)  
**Default:** None  
**Description:** Aurora PostgreSQL cluster endpoint  
**Example:** `PG_HOST=afirgen-vectors.cluster-abc123.us-east-1.rds.amazonaws.com`

#### PG_PORT
**Required:** No  
**Default:** `5432`  
**Description:** PostgreSQL port  
**Example:** `PG_PORT=5432`

#### PG_DATABASE
**Required:** Yes (if using Aurora pgvector)  
**Default:** `afirgen_vectors`  
**Description:** Database name  
**Example:** `PG_DATABASE=afirgen_vectors`

#### PG_USER
**Required:** Yes (if using Aurora pgvector)  
**Default:** None  
**Description:** Database username  
**Example:** `PG_USER=admin`

**Security Note:** Use AWS Secrets Manager for production

#### PG_PASSWORD
**Required:** Yes (if using Aurora pgvector)  
**Default:** None  
**Description:** Database password  
**Example:** `PG_PASSWORD=your_secure_password_here`

**Security Note:** Use AWS Secrets Manager for production

---

## Storage Configuration

### S3_BUCKET_NAME
**Required:** Yes  
**Default:** None  
**Description:** S3 bucket name for temporary file storage  
**Example:** `S3_BUCKET_NAME=afirgen-temp-files-us-east-1`

**Notes:**
- Used for audio files (Transcribe input)
- Used for image files (Textract input)
- Files are automatically deleted after processing
- Bucket must have SSE-KMS encryption enabled

### S3_LIFECYCLE_DAYS
**Required:** No  
**Default:** `7`  
**Description:** Days before S3 objects are automatically deleted  
**Example:** `S3_LIFECYCLE_DAYS=7`

---

## Database Configuration

### MYSQL_HOST
**Required:** Yes  
**Default:** None  
**Description:** MySQL RDS endpoint  
**Example:** `MYSQL_HOST=afirgen-db.abc123.us-east-1.rds.amazonaws.com`

### MYSQL_PORT
**Required:** No  
**Default:** `3306`  
**Description:** MySQL port  
**Example:** `MYSQL_PORT=3306`

### MYSQL_USER
**Required:** Yes  
**Default:** None  
**Description:** MySQL username  
**Example:** `MYSQL_USER=admin`

### MYSQL_PASSWORD
**Required:** Yes  
**Default:** None  
**Description:** MySQL password  
**Example:** `MYSQL_PASSWORD=your_secure_password_here`

**Security Note:** Use AWS Secrets Manager for production

### MYSQL_DB
**Required:** Yes  
**Default:** `fir_db`  
**Description:** MySQL database name  
**Example:** `MYSQL_DB=fir_db`

---

## Application Configuration

### PORT
**Required:** No  
**Default:** `8000`  
**Description:** Port for FastAPI application  
**Example:** `PORT=8000`

### FIR_AUTH_KEY
**Required:** Yes  
**Default:** None  
**Description:** Secret key for FIR authentication  
**Example:** `FIR_AUTH_KEY=your_random_32_byte_hex_string`

**Generate:** `openssl rand -hex 32`

### API_KEY
**Required:** Yes  
**Default:** None  
**Description:** API key for external integrations  
**Example:** `API_KEY=your_random_32_byte_hex_string`

**Generate:** `openssl rand -hex 32`

### TRANSCRIBE_LANGUAGES
**Required:** No  
**Default:** `hi-IN,en-IN,ta-IN,te-IN,bn-IN,mr-IN,gu-IN,kn-IN,ml-IN,pa-IN`  
**Description:** Comma-separated list of supported Transcribe language codes  
**Example:** `TRANSCRIBE_LANGUAGES=hi-IN,en-IN,ta-IN`

**Supported Languages:**
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

### ENVIRONMENT
**Required:** No  
**Default:** `production`  
**Description:** Environment name  
**Valid Values:** `development`, `staging`, `production`  
**Example:** `ENVIRONMENT=production`

### ENABLE_DEBUG
**Required:** No  
**Default:** `false`  
**Description:** Enable debug logging  
**Valid Values:** `true`, `false`  
**Example:** `ENABLE_DEBUG=false`

**Warning:** Never enable in production (logs sensitive data)

---

## Retry and Resilience Configuration

### MAX_RETRIES
**Required:** No  
**Default:** `2`  
**Description:** Maximum number of retry attempts for AWS service calls  
**Valid Values:** 0-10  
**Example:** `MAX_RETRIES=2`

**Notes:**
- Applies to: Transcribe, Textract, Bedrock, vector database
- Retries on: throttling errors, 5xx errors, transient network errors
- Does not retry on: 4xx client errors (except 429)

### BASE_DELAY
**Required:** No  
**Default:** `1.0`  
**Description:** Base delay in seconds for exponential backoff  
**Valid Values:** 0.1-10.0  
**Example:** `BASE_DELAY=1.0`

**Formula:** `delay = min(BASE_DELAY * (2 ** attempt) + jitter, MAX_DELAY)`

### MAX_DELAY
**Required:** No  
**Default:** `60.0`  
**Description:** Maximum delay in seconds for exponential backoff  
**Valid Values:** 1.0-300.0  
**Example:** `MAX_DELAY=60.0`

### FAILURE_THRESHOLD
**Required:** No  
**Default:** `5`  
**Description:** Number of consecutive failures before circuit breaker opens  
**Valid Values:** 1-20  
**Example:** `FAILURE_THRESHOLD=5`

### RECOVERY_TIMEOUT
**Required:** No  
**Default:** `60`  
**Description:** Seconds to wait before transitioning from OPEN to HALF_OPEN  
**Valid Values:** 10-600  
**Example:** `RECOVERY_TIMEOUT=60`

### HALF_OPEN_MAX_CALLS
**Required:** No  
**Default:** `3`  
**Description:** Number of test requests allowed in HALF_OPEN state  
**Valid Values:** 1-10  
**Example:** `HALF_OPEN_MAX_CALLS=3`

---

## Caching Configuration

### ENABLE_CACHING
**Required:** No  
**Default:** `true`  
**Description:** Enable in-memory caching for IPC sections  
**Valid Values:** `true`, `false`  
**Example:** `ENABLE_CACHING=true`

**Benefits:**
- Reduces embedding API calls by 30-50%
- Faster response times for frequent queries
- Lower costs

### CACHE_MAX_SIZE
**Required:** No  
**Default:** `100`  
**Description:** Maximum number of cached query results  
**Valid Values:** 10-1000  
**Example:** `CACHE_MAX_SIZE=100`

**Notes:**
- Uses LRU (Least Recently Used) eviction
- Each entry stores query hash → IPC sections mapping
- Memory usage: ~1KB per entry

---

## Monitoring Configuration

### ENABLE_XRAY
**Required:** No  
**Default:** `true`  
**Description:** Enable AWS X-Ray distributed tracing  
**Valid Values:** `true`, `false`  
**Example:** `ENABLE_XRAY=true`

**Benefits:**
- Request flow visualization
- Latency breakdown by service
- Error tracking with stack traces
- Performance bottleneck identification

### CLOUDWATCH_NAMESPACE
**Required:** No  
**Default:** `AFIRGen/Bedrock`  
**Description:** CloudWatch namespace for custom metrics  
**Example:** `CLOUDWATCH_NAMESPACE=AFIRGen/Bedrock`

**Metrics Emitted:**
- Bedrock request count, latency, token usage
- Transcribe request count, latency
- Textract request count, latency
- Vector database operation count, latency
- FIR generation end-to-end latency

---

## Security Configuration

### ENFORCE_HTTPS
**Required:** No  
**Default:** `false`  
**Description:** Enforce HTTPS for all API requests  
**Valid Values:** `true`, `false`  
**Example:** `ENFORCE_HTTPS=false`

**Notes:**
- Set to `true` after SSL certificate setup
- Redirects HTTP to HTTPS
- Required for production

### SESSION_TIMEOUT
**Required:** No  
**Default:** `3600`  
**Description:** Session timeout in seconds  
**Valid Values:** 300-86400  
**Example:** `SESSION_TIMEOUT=3600`

### CORS_ORIGINS
**Required:** No  
**Default:** `*`  
**Description:** Comma-separated list of allowed CORS origins  
**Example:** `CORS_ORIGINS=http://example.com,https://example.com`

**Security Note:** Never use `*` in production

---

## Rate Limiting Configuration

### RATE_LIMIT_REQUESTS
**Required:** No  
**Default:** `100`  
**Description:** Maximum requests per window  
**Valid Values:** 1-10000  
**Example:** `RATE_LIMIT_REQUESTS=100`

### RATE_LIMIT_WINDOW
**Required:** No  
**Default:** `60`  
**Description:** Rate limit window in seconds  
**Valid Values:** 1-3600  
**Example:** `RATE_LIMIT_WINDOW=60`

**Example:** `RATE_LIMIT_REQUESTS=100` and `RATE_LIMIT_WINDOW=60` = 100 requests per minute

---

## Configuration Validation

### Validation Script

Run the validation script to check all configuration:

```bash
python scripts/validate-env.py
```

**Checks:**
- ✅ All required variables present
- ✅ Valid values for enum fields
- ✅ AWS credentials configured
- ✅ Bedrock model access granted
- ✅ Vector database connectivity
- ✅ RDS connectivity
- ✅ S3 bucket accessibility

**Example Output:**
```
✅ All required environment variables present
✅ AWS credentials configured
✅ Bedrock access verified (Claude 3 Sonnet, Titan Embeddings)
✅ Vector database connection successful (opensearch)
✅ RDS connection successful
✅ S3 bucket accessible (afirgen-temp-files-us-east-1)
✅ Configuration valid
```

---

## Environment-Specific Configurations

### Development Environment

```bash
# .env.development
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0  # Cheaper
VECTOR_DB_TYPE=aurora_pgvector  # Cheaper
ENABLE_CACHING=true
ENABLE_DEBUG=true
ENABLE_XRAY=false  # Reduce overhead
MAX_RETRIES=1  # Fail fast
RATE_LIMIT_REQUESTS=10  # Lower limit
```

### Staging Environment

```bash
# .env.staging
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
VECTOR_DB_TYPE=opensearch
ENABLE_CACHING=true
ENABLE_DEBUG=false
ENABLE_XRAY=true
MAX_RETRIES=2
RATE_LIMIT_REQUESTS=100
```

### Production Environment

```bash
# .env.production
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
VECTOR_DB_TYPE=opensearch
ENABLE_CACHING=true
ENABLE_DEBUG=false
ENABLE_XRAY=true
MAX_RETRIES=2
RATE_LIMIT_REQUESTS=1000
ENFORCE_HTTPS=true
CORS_ORIGINS=https://yourdomain.com
```

---

## Complete Example Configuration

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_EMBEDDINGS_MODEL_ID=amazon.titan-embed-text-v1
ENABLE_BEDROCK=true

# Vector Database Configuration
VECTOR_DB_TYPE=opensearch
VECTOR_DB_ENDPOINT=https://abc123.us-east-1.aoss.amazonaws.com
VECTOR_DB_INDEX_NAME=ipc_sections
OPENSEARCH_REGION=us-east-1

# Storage Configuration
S3_BUCKET_NAME=afirgen-temp-files-us-east-1
S3_LIFECYCLE_DAYS=7

# Database Configuration
MYSQL_HOST=afirgen-db.abc123.us-east-1.rds.amazonaws.com
MYSQL_PORT=3306
MYSQL_USER=admin
MYSQL_PASSWORD=your_secure_password_here
MYSQL_DB=fir_db

# Application Configuration
PORT=8000
FIR_AUTH_KEY=your_random_32_byte_hex_string
API_KEY=your_random_32_byte_hex_string
TRANSCRIBE_LANGUAGES=hi-IN,en-IN,ta-IN,te-IN,bn-IN,mr-IN,gu-IN,kn-IN,ml-IN,pa-IN
ENVIRONMENT=production
ENABLE_DEBUG=false

# Retry and Resilience Configuration
MAX_RETRIES=2
BASE_DELAY=1.0
MAX_DELAY=60.0
FAILURE_THRESHOLD=5
RECOVERY_TIMEOUT=60
HALF_OPEN_MAX_CALLS=3

# Caching Configuration
ENABLE_CACHING=true
CACHE_MAX_SIZE=100

# Monitoring Configuration
ENABLE_XRAY=true
CLOUDWATCH_NAMESPACE=AFIRGen/Bedrock

# Security Configuration
ENFORCE_HTTPS=false
SESSION_TIMEOUT=3600
CORS_ORIGINS=*

# Rate Limiting Configuration
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

---

## Security Best Practices

1. **Never commit `.env.bedrock` to version control**
   ```bash
   echo ".env.bedrock" >> .gitignore
   ```

2. **Use AWS Secrets Manager for production**
   ```python
   # Instead of environment variables
   import boto3
   secrets = boto3.client('secretsmanager')
   db_password = secrets.get_secret_value(SecretId='afirgen/db/password')
   ```

3. **Rotate credentials regularly**
   - Database passwords: Every 90 days
   - API keys: Every 180 days
   - AWS access keys: Every 90 days

4. **Use IAM roles instead of access keys**
   - EC2 instances should use IAM instance profiles
   - No need for AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY

5. **Enable encryption at rest**
   - S3: SSE-KMS
   - RDS: Encryption enabled
   - EBS: Encryption enabled

6. **Enable encryption in transit**
   - HTTPS for API
   - TLS for database connections
   - VPC endpoints for AWS services

---

## Troubleshooting Configuration Issues

### "Missing required environment variable"

**Solution:**
```bash
# Check which variables are missing
python scripts/validate-env.py

# Add missing variables to .env.bedrock
nano .env.bedrock
```

### "Invalid VECTOR_DB_TYPE"

**Solution:**
```bash
# Must be exactly "opensearch" or "aurora_pgvector"
VECTOR_DB_TYPE=opensearch  # Not "OpenSearch" or "open_search"
```

### "Bedrock access denied"

**Solution:**
1. Verify model access in AWS Console
2. Check IAM role has bedrock:InvokeModel permission
3. Verify model ID is correct

### "Vector database connection failed"

**Solution:**
1. Check VECTOR_DB_ENDPOINT is correct
2. Verify security group allows EC2 → Vector DB
3. Check VPC endpoint connectivity
4. Verify credentials (for Aurora pgvector)

---

## Related Documentation

- [AWS Deployment Plan](AWS-DEPLOYMENT-PLAN.md)
- [Bedrock Troubleshooting](BEDROCK-TROUBLESHOOTING.md)
- [Cost Estimation](COST-ESTIMATION.md)
- [Migration Guide](MIGRATION-GUIDE.md)

---

## Summary

**Total Configuration Variables:** 40+  
**Required Variables:** 15  
**Optional Variables:** 25+  
**Validation:** Automated via `validate-env.py`

**Key Configuration Decisions:**
1. **Vector Database:** OpenSearch (performance) vs Aurora pgvector (cost)
2. **Bedrock Model:** Sonnet (balanced) vs Haiku (cheap) vs Opus (capable)
3. **Caching:** Enabled (recommended) for cost savings
4. **Monitoring:** X-Ray enabled (recommended) for observability

