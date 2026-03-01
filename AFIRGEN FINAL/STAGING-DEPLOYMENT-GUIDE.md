# AFIRGen Bedrock Migration - Staging Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the AFIRGen Bedrock architecture to a staging environment and executing Task 12.1: End-to-End Testing on Staging.

## Prerequisites

Before deploying to staging, ensure the following are completed:

### 1. AWS Account Setup
- [ ] AWS account with appropriate permissions
- [ ] IAM roles configured for Bedrock, Transcribe, Textract, S3
- [ ] AWS CLI installed and configured
- [ ] Terraform installed (v1.0+)

### 2. Infrastructure Requirements
- [ ] VPC with public and private subnets
- [ ] Security groups configured
- [ ] RDS MySQL instance (or access to existing)
- [ ] S3 bucket for temporary files
- [ ] Vector database (OpenSearch Serverless OR Aurora pgvector)

### 3. Service Access
- [ ] Amazon Bedrock access enabled in your AWS account
- [ ] Claude 3 Sonnet model access approved
- [ ] Titan Embeddings model access approved
- [ ] Amazon Transcribe access enabled
- [ ] Amazon Textract access enabled

### 4. Code Readiness
- [ ] All Phase 1-11 tasks completed
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Code reviewed and approved

## Deployment Steps

### Step 1: Configure Environment Variables

1. Copy the Bedrock environment template:
```bash
cd "AFIRGEN FINAL"
cp .env.bedrock .env.staging
```

2. Edit `.env.staging` with your staging-specific values:

```bash
# Critical configurations to update:
AWS_REGION=us-east-1  # Your AWS region
S3_BUCKET_NAME=afirgen-staging-temp-files  # Your S3 bucket
OPENSEARCH_ENDPOINT=https://your-collection-id.us-east-1.aoss.amazonaws.com
MYSQL_HOST=your-staging-rds.us-east-1.rds.amazonaws.com
MYSQL_PASSWORD=your-secure-password
```

3. Validate environment configuration:
```bash
python3 scripts/validate-env.py
```

### Step 2: Deploy Infrastructure with Terraform

1. Navigate to Terraform directory:
```bash
cd terraform/free-tier
```

2. Initialize Terraform:
```bash
terraform init
```

3. Review the deployment plan:
```bash
terraform plan -out=staging.tfplan
```

4. Apply the infrastructure changes:
```bash
terraform apply staging.tfplan
```

5. Note the outputs (EC2 IP, RDS endpoint, etc.):
```bash
terraform output
```

### Step 3: Migrate Vector Database

1. Export IPC sections from ChromaDB (if migrating):
```bash
python3 scripts/export_chromadb.py --output ipc_sections_export.json
```

2. Migrate to new vector database:
```bash
python3 scripts/migrate_vector_db.py \
    --input ipc_sections_export.json \
    --regenerate-embeddings \
    --vector-db-type opensearch  # or aurora_pgvector
```

3. Verify migration:
```bash
python3 scripts/migrate_vector_db.py --verify
```

### Step 4: Deploy Application

1. SSH into EC2 instance:
```bash
ssh -i your-key.pem ec2-user@your-ec2-ip
```

2. Clone repository and install dependencies:
```bash
git clone https://github.com/your-org/afirgen.git
cd afirgen/AFIRGEN\ FINAL
pip3 install -r requirements.txt
```

3. Copy environment file:
```bash
cp .env.staging .env
```

4. Start the application:
```bash
# Using systemd (recommended)
sudo systemctl start afirgen

# Or using Docker
docker-compose -f docker-compose.staging.yml up -d

# Or directly
uvicorn main\ backend.agentv5:app --host 0.0.0.0 --port 8000
```

### Step 5: Verify Deployment

1. Run health checks:
```bash
python3 scripts/health-check.py --base-url http://your-ec2-ip:8000
```

2. Verify AWS service connectivity:
```bash
# Test Bedrock
aws bedrock list-foundation-models --region us-east-1

# Test S3
aws s3 ls s3://afirgen-staging-temp-files

# Test Transcribe
aws transcribe list-transcription-jobs --region us-east-1
```

3. Check application logs:
```bash
# Systemd
sudo journalctl -u afirgen -f

# Docker
docker logs -f afirgen-backend

# Direct
tail -f logs/application.log
```

## Task 12.1: End-to-End Testing

Once staging is deployed, execute the comprehensive E2E test suite.

### Running E2E Tests

1. Set staging environment variables:
```bash
export STAGING_BASE_URL=http://your-ec2-ip:8000
export API_KEY=your-staging-api-key
```

2. Run the E2E test suite:
```bash
cd "AFIRGEN FINAL"
python3 tests/e2e/test_staging_e2e.py
```

### Test Coverage

The E2E test suite validates all acceptance criteria:

#### ✓ Audio Transcription (All 10 Languages)
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

#### ✓ Image OCR
- JPEG format support
- PNG format support
- Text extraction accuracy
- Form data extraction

#### ✓ Text-based FIR Generation
- Complaint text processing
- Legal narrative generation
- Metadata extraction
- IPC section retrieval
- Complete FIR generation

#### ✓ Complete Workflows
- Audio → Transcription → FIR → Storage
- Image → OCR → FIR → Storage

#### ✓ Role-Based Access Control
- Admin: Full CRUD access
- Officer: SELECT, INSERT, UPDATE
- Viewer: SELECT only
- Clerk: INSERT only

#### ✓ Error Handling
- Invalid file format rejection
- Retry logic for transient failures
- Exponential backoff
- Circuit breaker functionality

#### ✓ Concurrent Request Handling
- 10 simultaneous requests
- No performance degradation
- Consistent response times

### Manual Testing Checklist

In addition to automated tests, perform these manual validations:

#### Audio Transcription
- [ ] Upload 5-minute Hindi audio file
- [ ] Verify transcription completes within 3 minutes
- [ ] Check transcription accuracy
- [ ] Verify temporary file cleanup in S3

#### Image OCR
- [ ] Upload scanned document (JPEG)
- [ ] Verify OCR completes within 30 seconds
- [ ] Check text extraction accuracy
- [ ] Verify temporary file cleanup in S3

#### FIR Generation
- [ ] Submit text complaint in Hindi
- [ ] Verify legal narrative generation (max 3 sentences)
- [ ] Check metadata extraction (date, location, parties)
- [ ] Verify IPC sections are relevant
- [ ] Confirm FIR stored in MySQL
- [ ] Check end-to-end time < 5 minutes

#### Security
- [ ] Verify S3 uploads use SSE-KMS encryption
- [ ] Check TLS 1.2+ for all connections
- [ ] Confirm no PII in CloudWatch logs
- [ ] Verify IAM role-based authentication
- [ ] Test RBAC enforcement

#### Monitoring
- [ ] Check CloudWatch metrics are being emitted
- [ ] Verify X-Ray traces are created
- [ ] Review structured JSON logs
- [ ] Confirm correlation IDs in logs

## Test Data Preparation

### Audio Files
Prepare test audio files for each language:
```
test_audio_hi-IN.wav  # Hindi
test_audio_en-IN.wav  # English
test_audio_ta-IN.wav  # Tamil
test_audio_te-IN.wav  # Telugu
test_audio_bn-IN.wav  # Bengali
test_audio_mr-IN.wav  # Marathi
test_audio_gu-IN.wav  # Gujarati
test_audio_kn-IN.wav  # Kannada
test_audio_ml-IN.wav  # Malayalam
test_audio_pa-IN.wav  # Punjabi
```

### Image Files
Prepare test document images:
```
test_document_1.jpg  # Scanned complaint
test_document_2.png  # Handwritten complaint
test_document_3.jpg  # Form with structured data
```

### Test Complaints
Prepare sample complaint texts in multiple languages:
```
test_complaint_hindi.txt
test_complaint_english.txt
test_complaint_tamil.txt
```

## Troubleshooting

### Common Issues

#### 1. Bedrock Access Denied
**Error:** `AccessDeniedException: User is not authorized to perform: bedrock:InvokeModel`

**Solution:**
- Verify IAM role has Bedrock permissions
- Check model access is approved in AWS console
- Ensure correct model ARN in IAM policy

#### 2. Transcribe Job Fails
**Error:** `TranscribeError: Job failed with status FAILED`

**Solution:**
- Check audio file format (WAV, MP3, MPEG)
- Verify S3 bucket permissions
- Check language code is supported
- Review Transcribe service limits

#### 3. Vector Database Connection Failed
**Error:** `ConnectionError: Unable to connect to OpenSearch`

**Solution:**
- Verify OpenSearch endpoint URL
- Check security group allows traffic
- Confirm IAM role has OpenSearch permissions
- Test network connectivity from EC2

#### 4. High Latency
**Issue:** FIR generation takes > 5 minutes

**Solution:**
- Check CloudWatch metrics for bottlenecks
- Review X-Ray traces for slow operations
- Verify concurrent request limits
- Check vector database performance

## Success Criteria

Task 12.1 is considered complete when:

- [ ] Staging environment successfully deployed
- [ ] All automated E2E tests pass (100% success rate)
- [ ] All manual test checklist items verified
- [ ] Audio transcription works for all 10 languages
- [ ] Image OCR extracts text accurately
- [ ] Text-based FIR generation completes successfully
- [ ] Complete workflows (audio → FIR, image → FIR) work end-to-end
- [ ] RBAC enforced for all user roles
- [ ] Error handling and retry logic validated
- [ ] 10 concurrent requests handled without degradation
- [ ] No critical bugs identified
- [ ] Performance meets requirements:
  - Audio transcription: < 3 minutes for 5-minute files
  - Image OCR: < 30 seconds
  - Legal narrative: < 10 seconds
  - Vector search: < 2 seconds
  - End-to-end FIR: < 5 minutes
- [ ] CloudWatch metrics being emitted
- [ ] X-Ray traces being created
- [ ] Structured logs being generated

## Next Steps

After Task 12.1 completion:

1. **Task 12.2:** Performance Validation
   - Measure and validate latency metrics
   - Compare against baseline requirements

2. **Task 12.3:** Cost Validation
   - Track AWS service costs
   - Compare against GPU instance costs

3. **Task 12.4:** Security Audit
   - Verify encryption at rest and in transit
   - Audit IAM policies
   - Check for security vulnerabilities

4. **Task 12.5:** Bug Triage and Fixes
   - Document all bugs found during E2E testing
   - Prioritize and fix critical/high-priority bugs

5. **Task 12.6:** Production Readiness Review
   - Final review before production deployment

## Support

For issues or questions:
- Review BEDROCK-TROUBLESHOOTING.md
- Check CloudWatch logs
- Review X-Ray traces
- Contact DevOps team

## Rollback Plan

If critical issues are found:

1. Set feature flag:
```bash
export ENABLE_BEDROCK=false
```

2. Run rollback script:
```bash
./scripts/rollback-to-gguf.sh
```

3. Verify GGUF implementation is working:
```bash
python3 scripts/health-check.py
```
