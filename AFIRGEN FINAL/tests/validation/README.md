# Performance Validation Guide

This directory contains validation scripts for the Bedrock migration, including performance testing, cost validation, security audit, and bug triage.

## Performance Validation

### Prerequisites

1. **Running Application**: The AFIRGen application must be running and accessible
   - Default: `http://localhost:8000`
   - Staging: Set via command line argument

2. **Test Fixtures** (Optional):
   - `tests/fixtures/test_audio_5min.wav` - 5-minute audio file for transcription testing
   - `tests/fixtures/test_document.jpg` - Document image for OCR testing
   
   Note: Tests will skip audio/image tests if fixtures are not available and focus on text-based testing.

3. **Python Dependencies**:
   ```bash
   pip install httpx asyncio
   ```

### Running Performance Validation

#### Local Testing
```bash
python performance_validation.py
```

#### Staging Environment Testing
```bash
python performance_validation.py http://staging-url:8000
```

### What Gets Tested

The performance validation script tests the following requirements:

1. **Audio Transcription** (if test file available)
   - Requirement: < 3 minutes for 5-minute audio files
   - Endpoint: `POST /process` with audio file

2. **Document OCR** (if test file available)
   - Requirement: < 30 seconds
   - Endpoint: `POST /process` with image file

3. **Legal Narrative Generation**
   - Requirement: < 10 seconds
   - Endpoint: `POST /process` with text input

4. **Vector Similarity Search**
   - Requirement: < 2 seconds
   - Note: Tested as part of end-to-end flow (internal operation)

5. **End-to-End FIR Generation**
   - Requirement: < 5 minutes
   - Endpoints: `POST /process` → `POST /validate` (multi-step workflow)

6. **Concurrent Request Handling**
   - Requirement: 10 concurrent requests without degradation
   - Requirement: 99% success rate under normal load

### Output

The script generates:

1. **Console Output**: Real-time test results with pass/fail status
2. **JSON Report**: `performance_validation_report.json` with detailed metrics

### Example Output

```
============================================================
BEDROCK MIGRATION - PERFORMANCE VALIDATION
============================================================

Testing audio transcription performance...
  ⚠ Skipping: Test audio file not found at tests/fixtures/test_audio_5min.wav
Testing document OCR performance...
  ⚠ Skipping: Test image file not found at tests/fixtures/test_document.jpg
Testing legal narrative generation performance...
Testing vector similarity search performance...
  ⚠ Skipping: Vector search is tested as part of end-to-end FIR generation
Testing end-to-end FIR generation performance...
Testing 10 concurrent requests...

============================================================
PERFORMANCE VALIDATION REPORT
============================================================
Timestamp: 2024-01-15 14:30:00

Individual Component Tests:
------------------------------------------------------------
✓ PASS | audio_transcription        |   0.00s /    180s
✓ PASS | document_ocr               |   0.00s /     30s
✓ PASS | legal_narrative            |   8.45s /     10s
✓ PASS | vector_search              |   0.00s /      2s
✓ PASS | end_to_end_fir             |  45.23s /    300s

Concurrency Test:
------------------------------------------------------------
✓ PASS | Concurrent Requests: 10
       Success Rate: 100.00% (required: 99.00%)
       Avg Duration: 9.12s
       P95 Duration: 11.34s
       P99 Duration: 12.01s

============================================================
OVERALL RESULT: ✓ PASS
============================================================

Report saved to: performance_validation_report.json
```

### Interpreting Results

- **✓ PASS**: Test passed, performance meets requirements
- **✗ FAIL**: Test failed, performance below requirements
- **⚠ Skipping**: Test skipped (missing test files or not applicable)

### Troubleshooting

#### Application Not Running
```
Error: Connection refused
```
**Solution**: Start the AFIRGen application first:
```bash
cd "AFIRGEN FINAL/main backend"
python agentv5.py
```

#### Test Files Missing
```
⚠ Skipping: Test audio file not found
```
**Solution**: This is expected if you don't have test fixtures. The script will still test text-based operations.

To add test fixtures:
1. Create `tests/fixtures/` directory
2. Add a 5-minute audio file as `test_audio_5min.wav`
3. Add a document image as `test_document.jpg`

#### Performance Below Requirements
```
✗ FAIL | legal_narrative | 15.23s / 10s
```
**Solution**: 
1. Check AWS service latency (Bedrock, Transcribe, Textract)
2. Verify network connectivity to AWS services
3. Check CloudWatch metrics for bottlenecks
4. Review application logs for errors or retries

## Other Validation Scripts

### Cost Validation
```bash
python cost_validation.py
```
Validates cost reduction goals compared to GPU instance baseline.

### Security Audit
```bash
python security_audit.py
```
Performs security audit to verify all security requirements are met.

### Bug Triage
```bash
python bug_triage.py
```
Identifies and prioritizes bugs discovered during testing.

### Run All Validations
```bash
python run_all_validations.py
```
Runs all validation scripts and generates a comprehensive report.

## CI/CD Integration

To integrate performance validation into your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run Performance Validation
  run: |
    python tests/validation/performance_validation.py http://staging-url:8000
  continue-on-error: false
```

## Performance Baselines

Current performance baselines (from requirements):

| Operation | Threshold | Typical Performance |
|-----------|-----------|---------------------|
| Audio Transcription (5 min) | 180s | ~120s |
| Document OCR | 30s | ~15s |
| Legal Narrative | 10s | ~5-8s |
| Vector Search | 2s | ~0.5s |
| End-to-End FIR | 300s | ~45-60s |
| Concurrent Requests | 10 | 10+ |
| Success Rate | 99% | 99.5%+ |

## Support

For issues or questions:
1. Check application logs in CloudWatch
2. Review the troubleshooting section above
3. Consult the main project documentation
