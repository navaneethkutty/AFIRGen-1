# Feature Flag Rollback Mechanism

## Overview

The AFIRGen system supports a feature flag mechanism that allows seamless toggling between two implementations:

1. **Bedrock Mode**: Uses AWS managed services (Transcribe, Textract, Bedrock Claude, Titan Embeddings)
2. **GGUF Mode**: Uses self-hosted models (Whisper, Donut OCR, custom legal models)

This feature flag enables safe rollback to the GGUF implementation if issues occur with Bedrock, without requiring code changes or redeployment.

## Feature Flag Configuration

### Environment Variable

The feature flag is controlled by a single environment variable:

```bash
ENABLE_BEDROCK=true   # Use Bedrock (AWS managed services)
ENABLE_BEDROCK=false  # Use GGUF (self-hosted models)
```

### Configuration Files

#### For Bedrock Mode (.env.bedrock)

```bash
# Feature Flag
ENABLE_BEDROCK=true

# AWS Configuration
AWS_REGION=us-east-1
S3_BUCKET_NAME=afirgen-bedrock-bucket

# Bedrock Models
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_EMBEDDINGS_MODEL_ID=amazon.titan-embed-text-v1

# Vector Database
VECTOR_DB_TYPE=opensearch
OPENSEARCH_ENDPOINT=https://your-opensearch-endpoint.amazonaws.com
OPENSEARCH_INDEX_NAME=ipc_sections

# Monitoring
ENABLE_CLOUDWATCH_METRICS=true
ENABLE_XRAY=true
ENABLE_STRUCTURED_LOGGING=true
```

#### For GGUF Mode (.env.gguf)

```bash
# Feature Flag
ENABLE_BEDROCK=false

# Model Server URLs (GGUF)
MODEL_SERVER_URL=http://localhost:8001
ASR_OCR_SERVER_URL=http://localhost:8002

# Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=fir_db

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_kb
```

## Implementation Details

### Startup Behavior

When the application starts, it:

1. Reads the `ENABLE_BEDROCK` environment variable
2. Logs the active implementation prominently
3. Initializes only the required services:
   - **Bedrock Mode**: Initializes AWS clients, vector database, IPC cache
   - **GGUF Mode**: Initializes model pool, ChromaDB, local services

### Startup Logs

```
============================================================
ACTIVE IMPLEMENTATION: Bedrock (AWS managed services)
Feature Flag ENABLE_BEDROCK: True
============================================================
✅ Model pool initialized
Initializing Bedrock services...
✅ Bedrock services initialized successfully
   - Transcribe client ready (region: us-east-1)
   - Textract client ready (region: us-east-1)
   - Bedrock client ready (model: anthropic.claude-3-sonnet-20240229-v1:0)
   - Titan Embeddings ready (model: amazon.titan-embed-text-v1)
   - Vector DB ready (type: opensearch)
```

Or for GGUF mode:

```
============================================================
ACTIVE IMPLEMENTATION: GGUF (self-hosted models)
Feature Flag ENABLE_BEDROCK: False
============================================================
✅ Model pool initialized
Bedrock services disabled - using GGUF implementation
   - GGUF model servers will be used for all operations
   - Ensure model servers are running and accessible
```

### Request Routing

All FIR generation requests are automatically routed to the appropriate implementation:

```python
async def initial_processing(state: InteractiveFIRState):
    settings = get_settings()
    
    if settings.enable_bedrock:
        # Use Bedrock Transcribe/Textract
        log.info("Using Bedrock implementation")
        # ... Bedrock code ...
    else:
        # Use GGUF Whisper/Donut
        log.info("Using GGUF implementation")
        # ... GGUF code ...
```

### API Contract Consistency

Both implementations maintain **identical API contracts**:

- Same request schemas
- Same response schemas
- Same error formats
- Same HTTP status codes
- Same endpoint paths

This ensures frontend applications work without changes regardless of which implementation is active.

## Health Endpoint

The `/health` endpoint indicates which implementation is currently active:

### Bedrock Mode Response

```json
{
  "status": "healthy",
  "implementation": "bedrock",
  "enable_bedrock": true,
  "bedrock": {
    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
    "embeddings_model_id": "amazon.titan-embed-text-v1",
    "vector_db_type": "opensearch",
    "services_initialized": true
  },
  "database": "connected",
  "session_persistence": "sqlite"
}
```

### GGUF Mode Response

```json
{
  "status": "healthy",
  "implementation": "gguf",
  "enable_bedrock": false,
  "gguf": {
    "model_server": {"status": "healthy"},
    "asr_ocr_server": {"status": "healthy"},
    "kb_collections": 3,
    "kb_cache_size": 100
  },
  "database": "connected",
  "session_persistence": "sqlite"
}
```

## Rollback Procedure

If critical issues occur with Bedrock, follow this procedure to rollback to GGUF:

### Step 1: Update Environment Variable

```bash
# Update .env file or export directly
export ENABLE_BEDROCK=false
```

### Step 2: Restart Application

```bash
# Using systemd
sudo systemctl restart afirgen-backend

# Or manually
pkill -f uvicorn
python -m uvicorn agentv5:app --host 0.0.0.0 --port 8000
```

### Step 3: Verify Health Endpoint

```bash
curl http://localhost:8000/health | jq .

# Expected output:
# {
#   "status": "healthy",
#   "implementation": "gguf",
#   "enable_bedrock": false,
#   ...
# }
```

### Step 4: Verify GGUF Model Servers

Ensure GGUF model servers are running:

```bash
# Check model server
curl http://localhost:8001/health

# Check ASR/OCR server
curl http://localhost:8002/health
```

### Step 5: Test FIR Generation

```bash
# Test with text input
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Test complaint for rollback verification"}'
```

### Step 6: Monitor Logs

```bash
# Check application logs
tail -f logs/main_backend.log | grep "ACTIVE IMPLEMENTATION"

# Should show:
# ACTIVE IMPLEMENTATION: GGUF (self-hosted models)
```

## Rollback Validation Checklist

- [ ] Environment variable `ENABLE_BEDROCK=false` is set
- [ ] Application restarted successfully
- [ ] Health endpoint shows `"implementation": "gguf"`
- [ ] GGUF model servers are healthy
- [ ] Test FIR generation completes successfully
- [ ] Logs show "Using GGUF implementation"
- [ ] No Bedrock-related errors in logs
- [ ] Session management working correctly
- [ ] Database connections stable

## Forward Migration (GGUF to Bedrock)

To migrate back to Bedrock after rollback:

### Step 1: Verify Bedrock Services

```bash
# Test AWS credentials
aws sts get-caller-identity

# Test Bedrock access
aws bedrock list-foundation-models --region us-east-1

# Test Transcribe access
aws transcribe list-transcription-jobs --region us-east-1 --max-results 1

# Test Textract access
aws textract list-adapters --region us-east-1
```

### Step 2: Update Environment Variable

```bash
export ENABLE_BEDROCK=true
```

### Step 3: Restart and Verify

```bash
sudo systemctl restart afirgen-backend
curl http://localhost:8000/health | jq .implementation
# Should show: "bedrock"
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Implementation Status**: Check `/health` endpoint regularly
2. **Request Success Rate**: Monitor FIR generation success rate
3. **Latency**: Compare latency between implementations
4. **Error Rate**: Track errors by implementation type
5. **Cost**: Monitor AWS service costs (Bedrock mode only)

### Recommended Alerts

```yaml
# CloudWatch Alarm for Bedrock failures
- AlarmName: BedrockHighErrorRate
  MetricName: ErrorRate
  Threshold: 5%
  EvaluationPeriods: 2
  Action: Trigger rollback to GGUF

# Health check alert
- AlarmName: HealthCheckFailed
  MetricName: HealthCheckStatus
  Threshold: 0 (unhealthy)
  EvaluationPeriods: 3
  Action: Page on-call engineer
```

## Testing

### Integration Tests

Run integration tests to verify both implementations:

```bash
# Test feature flag mechanism
pytest tests/integration/test_feature_flag_rollback.py -v

# Test Bedrock implementation
ENABLE_BEDROCK=true pytest tests/integration/test_fir_generation_integration.py -v

# Test GGUF implementation
ENABLE_BEDROCK=false pytest tests/integration/ -v
```

### Manual Testing

```bash
# Run demonstration script
python scripts/demo_feature_flag.py
```

## Troubleshooting

### Issue: Application fails to start in Bedrock mode

**Symptoms**: Application exits with error during startup

**Solution**:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify environment variables are set correctly
3. Check vector database connectivity
4. Review startup logs for specific error
5. Rollback to GGUF mode if needed

### Issue: Requests failing after switching modes

**Symptoms**: 500 errors after changing ENABLE_BEDROCK

**Solution**:
1. Ensure application was restarted after changing flag
2. Clear any cached sessions: `rm sessions.db`
3. Verify health endpoint shows correct implementation
4. Check logs for initialization errors

### Issue: Inconsistent behavior between implementations

**Symptoms**: Different responses from same input

**Solution**:
1. Verify API contract consistency tests pass
2. Check prompt templates are equivalent
3. Review model parameters (temperature, max_tokens)
4. Compare logs from both implementations

## Best Practices

1. **Always test rollback procedure** in staging before production
2. **Monitor health endpoint** continuously
3. **Keep GGUF model servers running** even in Bedrock mode (for quick rollback)
4. **Document rollback decisions** in incident reports
5. **Set up automated alerts** for implementation failures
6. **Test both implementations regularly** to ensure rollback readiness
7. **Maintain feature parity** between implementations
8. **Version control environment files** (.env.bedrock, .env.gguf)

## Security Considerations

1. **Credentials**: Ensure AWS credentials are properly secured
2. **Secrets**: Use AWS Secrets Manager or environment variables, never hardcode
3. **Access Control**: Maintain same RBAC in both implementations
4. **Encryption**: Both implementations use encryption at rest and in transit
5. **Audit Logs**: Log all implementation switches for compliance

## Performance Comparison

| Metric | GGUF Mode | Bedrock Mode |
|--------|-----------|--------------|
| Audio Transcription | ~2-3 min | ~1-2 min |
| Document OCR | ~20-30 sec | ~10-20 sec |
| Legal Narrative | ~5-10 sec | ~3-5 sec |
| Vector Search | ~1-2 sec | ~0.5-1 sec |
| End-to-End FIR | ~5-7 min | ~3-5 min |
| Infrastructure Cost | $1.21/hour | Pay-per-use |

## Support

For issues or questions about the feature flag mechanism:

1. Check logs: `logs/main_backend.log`
2. Review health endpoint: `curl http://localhost:8000/health`
3. Run diagnostics: `python scripts/demo_feature_flag.py`
4. Contact DevOps team for infrastructure issues
5. Refer to main documentation: `README.md`

## References

- [Requirements Document](.kiro/specs/bedrock-migration/requirements.md) - Requirement 16
- [Design Document](.kiro/specs/bedrock-migration/design.md) - Property 30
- [Tasks Document](.kiro/specs/bedrock-migration/tasks.md) - Task 10.2
- [Migration Guide](MIGRATION-GUIDE.md)
- [API Documentation](docs/API.md)
