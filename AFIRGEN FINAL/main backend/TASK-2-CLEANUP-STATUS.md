# Task 2: Set up minimal project structure and configuration - Status

## Completed Items ✅

### 1. Updated requirements.txt
- ✅ Removed broken dependencies:
  - aws-xray-sdk
  - redis
  - celery
  - prometheus-client
  - structlog
  - psutil
  - All opentelemetry libraries
  - pytest-benchmark
  - locust
  - mysql_connector_repackaged (replaced with mysql-connector-python)
  - python_magic
  - filelock
  - ffmpeg-python

- ✅ Kept only essential dependencies (9 packages):
  - fastapi==0.104.1
  - uvicorn[standard]==0.24.0
  - pydantic==2.5.0
  - boto3==1.29.7
  - mysql-connector-python==8.2.0
  - python-multipart==0.0.6
  - Pillow==10.1.0
  - httpx==0.25.1
  - reportlab==4.0.7

### 2. Created .env.example
- ✅ Created comprehensive .env.example template in `AFIRGEN FINAL/main backend/.env.example`
- ✅ Includes all required AWS configuration variables:
  - AWS_REGION
  - S3_BUCKET_NAME
  - DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
  - API_KEY
- ✅ Includes optional configuration with defaults:
  - BEDROCK_MODEL_ID
  - RATE_LIMIT_PER_MINUTE
  - MAX_FILE_SIZE_MB
  - Timeout configurations
  - Retry configurations
- ✅ Includes helpful notes about IAM roles and security groups

### 3. Created README.md
- ✅ Created comprehensive README.md with:
  - Architecture overview
  - Prerequisites for Windows and Linux
  - Local development setup instructions (Windows)
  - EC2 deployment instructions (Linux)
  - Systemd service configuration
  - AWS IAM role configuration
  - API endpoint documentation
  - Troubleshooting guide
  - Maintenance procedures
  - Security considerations
  - Performance tuning tips

### 4. Verified logs/ directory
- ✅ Confirmed logs/ directory exists for application logs

### 5. Created clean reference implementation
- ✅ Created `agentv5_clean.py` as a reference implementation showing:
  - Single-file architecture
  - Minimal imports (no broken dependencies)
  - AWS Bedrock integration structure
  - Clean configuration management
  - Proper logging setup
  - Rate limiting
  - Security headers
  - Health check endpoint

## Remaining Work for agentv5.py ⚠️

The current `agentv5.py` file still contains code that should be removed according to requirements:

### Code to Remove:

1. **ModelPool class** (lines 774-1090)
   - Contains GGUF model server communication
   - References MODEL_SERVER_URL and ASR_OCR_SERVER_URL
   - Methods: whisper_transcribe(), dots_ocr_sync()

2. **Model server references** throughout the file:
   - MODEL_SERVER_URL environment variable references
   - ASR_OCR_SERVER_URL environment variable references
   - model_server_circuit breaker
   - asr_ocr_circuit breaker

3. **Stub classes** (lines 35-83):
   - CircuitBreaker, RetryPolicy, HealthMonitor, GracefulShutdown, AutoRecovery, DependencyHealthCheck
   - These are stubs for removed reliability module

4. **X-Ray tracing stubs** (lines 146-163):
   - setup_xray, trace_subsegment, add_trace_annotation, add_trace_metadata
   - AsyncXRaySubsegment class
   - get_trace_id function

5. **Imports from infrastructure modules**:
   - The file imports from infrastructure/input_validation, infrastructure/json_logging, infrastructure/cloudwatch_metrics, etc.
   - According to Requirement 11 (Simplified File Structure), the backend should NOT have infrastructure/ directory
   - These should be inlined or removed

### Options for Completing agentv5.py Cleanup:

**Option A: Complete Rewrite (Recommended)**
- Replace current agentv5.py with agentv5_clean.py as a starting point
- Implement full FIR generation workflow using AWS Bedrock
- Follow design document's single-file architecture
- Estimated effort: 4-6 hours

**Option B: Incremental Cleanup**
- Remove ModelPool class and all model server code
- Remove stub classes
- Remove or inline infrastructure module imports
- Update all endpoints to use AWS services instead of model servers
- Estimated effort: 2-3 hours

**Option C: Hybrid Approach**
- Keep current agentv5.py for now (it has working endpoints)
- Use agentv5_clean.py as reference for new AWS Bedrock implementation
- Gradually migrate functionality
- Estimated effort: Ongoing

## Recommendations

1. **For immediate deployment**: Use the updated requirements.txt, .env.example, and README.md. The current agentv5.py will fail to start due to missing dependencies, but the infrastructure is in place.

2. **For production readiness**: Complete Option A (rewrite) to fully align with the design document's AWS Bedrock architecture.

3. **For testing**: Install the new requirements.txt and attempt to start the application to identify remaining import errors.

## Testing the Current Setup

To test what's been completed:

```bash
# 1. Install new dependencies
pip install -r requirements.txt

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env with your values
nano .env

# 4. Try to start the application (will likely fail due to infrastructure imports)
python -m uvicorn agentv5:app --host 0.0.0.0 --port 8000
```

Expected issues:
- Import errors from infrastructure modules
- Missing AWS credentials
- Database connection errors (if RDS not configured)

## Next Steps

1. Decide on cleanup approach (A, B, or C above)
2. Test installation with new requirements.txt
3. Address import errors in agentv5.py
4. Implement AWS Bedrock integration
5. Test end-to-end FIR generation workflow
