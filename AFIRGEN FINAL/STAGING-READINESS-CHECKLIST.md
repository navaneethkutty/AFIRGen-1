# AFIRGen Bedrock Migration - Staging Readiness Checklist

## Purpose

This checklist ensures all prerequisites are met before deploying to staging and executing Task 12.1: End-to-End Testing.

## Pre-Deployment Checklist

### AWS Account & Permissions

- [ ] AWS account created and accessible
- [ ] AWS CLI installed (version 2.x)
- [ ] AWS credentials configured (`aws configure`)
- [ ] IAM user/role has AdministratorAccess or equivalent
- [ ] Billing alerts configured
- [ ] Cost budget set for staging environment

### AWS Service Access

- [ ] Amazon Bedrock service enabled in AWS account
- [ ] Bedrock model access requested and approved:
  - [ ] Claude 3 Sonnet (`anthropic.claude-3-sonnet-20240229-v1:0`)
  - [ ] Titan Embeddings (`amazon.titan-embed-text-v1`)
- [ ] Amazon Transcribe access enabled
- [ ] Amazon Textract access enabled
- [ ] Amazon S3 access enabled
- [ ] Amazon RDS access enabled
- [ ] Amazon CloudWatch access enabled
- [ ] AWS X-Ray access enabled

**Note:** Bedrock model access can take 1-2 business days for approval.

### Infrastructure Tools

- [ ] Terraform installed (v1.0+)
- [ ] Python 3.8+ installed
- [ ] pip installed
- [ ] Git installed
- [ ] SSH client available
- [ ] Text editor (VS Code, vim, etc.)

### Network & Security

- [ ] VPC CIDR block planned (e.g., 10.0.0.0/16)
- [ ] Public subnet CIDR planned (e.g., 10.0.1.0/24)
- [ ] Private subnet CIDR planned (e.g., 10.0.2.0/24)
- [ ] SSH key pair created for EC2 access
- [ ] Security group rules planned
- [ ] SSL/TLS certificates available (if using HTTPS)

### Database

- [ ] MySQL RDS instance size selected (e.g., db.t3.micro)
- [ ] Database name decided (e.g., `afirgen_staging`)
- [ ] Master username decided (e.g., `admin`)
- [ ] Strong master password generated
- [ ] Backup retention period decided (e.g., 7 days)

### Vector Database Selection

Choose ONE:

**Option A: OpenSearch Serverless**
- [ ] OpenSearch Serverless collection name decided
- [ ] OCU capacity planned (minimum 2 OCUs)
- [ ] Index name decided (e.g., `ipc_sections`)

**Option B: Aurora PostgreSQL with pgvector**
- [ ] Aurora cluster name decided
- [ ] Instance class selected (e.g., db.t3.medium)
- [ ] ACU capacity planned (minimum 0.5 ACU)
- [ ] pgvector extension installation planned

### Storage

- [ ] S3 bucket name decided (must be globally unique)
  - Example: `afirgen-staging-temp-files-{account-id}`
- [ ] S3 lifecycle policy planned (e.g., delete after 7 days)
- [ ] KMS key for encryption planned (or use AWS managed key)

### Application Configuration

- [ ] Application domain/subdomain decided (e.g., `staging.afirgen.com`)
- [ ] API authentication key generated
- [ ] CORS origins configured
- [ ] Rate limiting values decided
- [ ] Log retention period decided

### Code Readiness

- [ ] All Phase 1-11 tasks marked as completed
- [ ] Code merged to staging branch
- [ ] Unit tests passing (90%+ coverage)
- [ ] Integration tests passing
- [ ] Property-based tests passing
- [ ] Code review completed
- [ ] No known critical bugs

### Test Data Preparation

- [ ] Audio test files prepared (10 languages):
  - [ ] Hindi (hi-IN)
  - [ ] English (en-IN)
  - [ ] Tamil (ta-IN)
  - [ ] Telugu (te-IN)
  - [ ] Bengali (bn-IN)
  - [ ] Marathi (mr-IN)
  - [ ] Gujarati (gu-IN)
  - [ ] Kannada (kn-IN)
  - [ ] Malayalam (ml-IN)
  - [ ] Punjabi (pa-IN)
- [ ] Image test files prepared (JPEG, PNG)
- [ ] Text complaint samples prepared
- [ ] Test user credentials created:
  - [ ] Admin user
  - [ ] Officer user
  - [ ] Viewer user
  - [ ] Clerk user

### Monitoring & Observability

- [ ] CloudWatch log groups planned
- [ ] CloudWatch metrics namespace decided (e.g., `AFIRGen/Bedrock`)
- [ ] X-Ray tracing enabled
- [ ] Alert thresholds defined
- [ ] Notification channels configured (email, Slack, etc.)

### Documentation

- [ ] Deployment guide reviewed (`STAGING-DEPLOYMENT-GUIDE.md`)
- [ ] Troubleshooting guide reviewed (`BEDROCK-TROUBLESHOOTING.md`)
- [ ] API documentation reviewed (`docs/API.md`)
- [ ] Team trained on deployment process

## Deployment Checklist

### Phase 1: Environment Configuration

- [ ] Clone repository to local machine
- [ ] Copy `.env.bedrock` to `.env.staging`
- [ ] Update all environment variables in `.env.staging`:
  - [ ] AWS_REGION
  - [ ] S3_BUCKET_NAME
  - [ ] BEDROCK_MODEL_ID
  - [ ] BEDROCK_EMBEDDINGS_MODEL_ID
  - [ ] VECTOR_DB_TYPE
  - [ ] OPENSEARCH_ENDPOINT (if using OpenSearch)
  - [ ] AURORA_HOST (if using Aurora)
  - [ ] MYSQL_HOST
  - [ ] MYSQL_PASSWORD
  - [ ] API_KEY
- [ ] Validate environment configuration:
  ```bash
  python3 scripts/validate-env.py
  ```

### Phase 2: Infrastructure Deployment

- [ ] Navigate to Terraform directory:
  ```bash
  cd terraform/free-tier
  ```
- [ ] Initialize Terraform:
  ```bash
  terraform init
  ```
- [ ] Create Terraform plan:
  ```bash
  terraform plan -out=staging.tfplan
  ```
- [ ] Review plan output for errors
- [ ] Apply Terraform configuration:
  ```bash
  terraform apply staging.tfplan
  ```
- [ ] Note infrastructure outputs:
  - [ ] EC2 instance public IP
  - [ ] RDS endpoint
  - [ ] S3 bucket name
  - [ ] Vector database endpoint
- [ ] Verify resources in AWS Console

### Phase 3: Vector Database Migration

- [ ] Export IPC sections from ChromaDB (if applicable):
  ```bash
  python3 scripts/export_chromadb.py --output ipc_sections_export.json
  ```
- [ ] Migrate to new vector database:
  ```bash
  python3 scripts/migrate_vector_db.py \
      --input ipc_sections_export.json \
      --regenerate-embeddings
  ```
- [ ] Verify migration success:
  ```bash
  python3 scripts/migrate_vector_db.py --verify
  ```
- [ ] Check vector count matches source

### Phase 4: Application Deployment

- [ ] SSH into EC2 instance:
  ```bash
  ssh -i your-key.pem ec2-user@{EC2_IP}
  ```
- [ ] Install system dependencies:
  ```bash
  sudo yum update -y
  sudo yum install python3 python3-pip git -y
  ```
- [ ] Clone repository:
  ```bash
  git clone https://github.com/your-org/afirgen.git
  cd afirgen/AFIRGEN\ FINAL
  ```
- [ ] Install Python dependencies:
  ```bash
  pip3 install -r requirements.txt
  ```
- [ ] Copy environment file:
  ```bash
  cp .env.staging .env
  ```
- [ ] Start application:
  ```bash
  # Option 1: Direct
  uvicorn main\ backend.agentv5:app --host 0.0.0.0 --port 8000 &
  
  # Option 2: Systemd (recommended)
  sudo systemctl start afirgen
  sudo systemctl enable afirgen
  ```
- [ ] Verify application is running:
  ```bash
  curl http://localhost:8000/health
  ```

### Phase 5: Health Checks

- [ ] Run health check script:
  ```bash
  python3 scripts/health-check.py --base-url http://{EC2_IP}:8000
  ```
- [ ] Verify all checks pass:
  - [ ] Application health endpoint
  - [ ] Bedrock access
  - [ ] S3 bucket access
  - [ ] RDS connectivity
  - [ ] Vector database connectivity
- [ ] Check CloudWatch logs:
  ```bash
  aws logs tail /aws/afirgen/staging --follow
  ```
- [ ] Verify X-Ray traces are being created

### Phase 6: AWS Service Verification

- [ ] Test Bedrock access:
  ```bash
  aws bedrock list-foundation-models --region us-east-1
  ```
- [ ] Test S3 access:
  ```bash
  aws s3 ls s3://{S3_BUCKET_NAME}
  ```
- [ ] Test Transcribe:
  ```bash
  aws transcribe list-transcription-jobs --region us-east-1
  ```
- [ ] Test Textract:
  ```bash
  aws textract list-adapters --region us-east-1
  ```

## E2E Testing Checklist

### Test Preparation

- [ ] Set environment variables:
  ```bash
  export STAGING_BASE_URL=http://{EC2_IP}:8000
  export API_KEY={YOUR_API_KEY}
  ```
- [ ] Upload test data to staging:
  - [ ] Audio files to test directory
  - [ ] Image files to test directory
  - [ ] Text complaint samples
- [ ] Verify test user accounts exist in database

### Automated Tests

- [ ] Run E2E test suite:
  ```bash
  python3 tests/e2e/test_staging_e2e.py
  ```
- [ ] Review test results
- [ ] Document any failures
- [ ] Capture screenshots of failures

### Manual Tests

- [ ] Test audio transcription (each language):
  - [ ] Hindi
  - [ ] English
  - [ ] Tamil
  - [ ] Telugu
  - [ ] Bengali
  - [ ] Marathi
  - [ ] Gujarati
  - [ ] Kannada
  - [ ] Malayalam
  - [ ] Punjabi
- [ ] Test image OCR:
  - [ ] JPEG format
  - [ ] PNG format
  - [ ] Handwritten text
  - [ ] Printed text
- [ ] Test text-based FIR generation
- [ ] Test complete workflows:
  - [ ] Audio → Transcription → FIR → Storage
  - [ ] Image → OCR → FIR → Storage
- [ ] Test RBAC:
  - [ ] Admin access
  - [ ] Officer access
  - [ ] Viewer access
  - [ ] Clerk access
- [ ] Test error handling:
  - [ ] Invalid file format
  - [ ] Oversized file
  - [ ] Network timeout
  - [ ] Service unavailable
- [ ] Test concurrent requests (10 simultaneous)

### Performance Validation

- [ ] Measure audio transcription time (< 3 min for 5-min file)
- [ ] Measure image OCR time (< 30 seconds)
- [ ] Measure legal narrative generation (< 10 seconds)
- [ ] Measure vector search time (< 2 seconds)
- [ ] Measure end-to-end FIR generation (< 5 minutes)
- [ ] Verify 99% success rate under load

### Monitoring Validation

- [ ] Verify CloudWatch metrics:
  - [ ] Transcribe request count
  - [ ] Textract request count
  - [ ] Bedrock request count
  - [ ] Vector database operations
  - [ ] API latency
- [ ] Verify X-Ray traces:
  - [ ] Trace created for each request
  - [ ] Subsegments for each AWS service
  - [ ] Correlation IDs present
- [ ] Verify structured logs:
  - [ ] JSON format
  - [ ] No PII in logs
  - [ ] Correlation IDs present

## Post-Testing Checklist

### Bug Documentation

- [ ] Document all bugs found
- [ ] Prioritize bugs (P0, P1, P2, P3)
- [ ] Create bug tickets
- [ ] Assign bugs to developers

### Reporting

- [ ] Generate test report
- [ ] Document test coverage
- [ ] Capture performance metrics
- [ ] Document cost estimates
- [ ] Create summary presentation

### Cleanup (Optional)

- [ ] Stop EC2 instance (if not needed)
- [ ] Delete temporary S3 files
- [ ] Snapshot RDS database
- [ ] Document staging state

## Success Criteria

Task 12.1 is complete when:

- [ ] All checklist items above are completed
- [ ] Staging environment is fully deployed
- [ ] All automated E2E tests pass (100%)
- [ ] All manual tests pass
- [ ] No critical (P0) bugs identified
- [ ] Performance requirements met
- [ ] Monitoring and logging verified
- [ ] Test report generated
- [ ] Team sign-off obtained

## Rollback Plan

If critical issues are found:

- [ ] Set feature flag: `ENABLE_BEDROCK=false`
- [ ] Run rollback script: `./scripts/rollback-to-gguf.sh`
- [ ] Verify GGUF implementation works
- [ ] Document rollback reason
- [ ] Plan remediation

## Estimated Time

| Phase | Duration |
|-------|----------|
| Pre-deployment preparation | 2-4 hours |
| Infrastructure deployment | 2-4 hours |
| Vector database migration | 1-2 hours |
| Application deployment | 1 hour |
| Health checks | 30 minutes |
| Automated E2E tests | 1-2 hours |
| Manual testing | 3-4 hours |
| Bug documentation | 1-2 hours |
| Reporting | 1-2 hours |
| **Total** | **12-21 hours** |

**Recommended:** Allocate 2-3 full days for complete staging deployment and testing.

## Notes

- Keep AWS Console open to monitor resource creation
- Document any deviations from the plan
- Take screenshots of successful deployments
- Save all error messages for troubleshooting
- Communicate progress to team regularly

---

**Last Updated:** 2024  
**Version:** 1.0
