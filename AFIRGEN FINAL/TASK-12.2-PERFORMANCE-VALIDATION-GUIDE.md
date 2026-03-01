# Task 12.2: Performance Validation - Execution Guide

## Status: READY FOR EXECUTION

The performance validation script has been updated and is ready to run. This guide explains how to execute the validation and interpret results.

## What Was Done

### 1. Updated Performance Validation Script
**File**: `tests/validation/performance_validation.py`

**Changes Made**:
- ✅ Updated API endpoints to match actual AFIRGen implementation (`/process`, `/validate`)
- ✅ Fixed audio transcription test to use correct endpoint and parameters
- ✅ Fixed document OCR test to use correct endpoint
- ✅ Updated legal narrative test to use `/process` with text input
- ✅ Simplified vector search test (tested as part of end-to-end flow)
- ✅ Updated end-to-end FIR test to use multi-step validation workflow
- ✅ Updated concurrent request test to use correct endpoint
- ✅ Added graceful handling for missing test fixtures
- ✅ Added comprehensive documentation

### 2. Created Documentation
**File**: `tests/validation/README.md`

**Contents**:
- Prerequisites and setup instructions
- How to run performance validation
- What gets tested and requirements
- Example output and interpretation
- Troubleshooting guide
- Performance baselines

## How to Execute Performance Validation

### Prerequisites

1. **Start the AFIRGen Application**:
   ```bash
   cd "AFIRGEN FINAL/main backend"
   python agentv5.py
   ```
   
   Wait for the application to start and listen on port 8000.

2. **Verify Application is Running**:
   ```bash
   curl http://localhost:8000/health
   ```
   
   Should return a 200 OK response.

3. **(Optional) Prepare Test Fixtures**:
   - Create `AFIRGEN FINAL/tests/fixtures/` directory
   - Add `test_audio_5min.wav` - a 5-minute audio file
   - Add `test_document.jpg` - a document image
   
   **Note**: Tests will skip audio/image tests if fixtures are missing and focus on text-based testing.

### Running the Validation

#### Option 1: Local Testing
```bash
cd "AFIRGEN FINAL"
python tests/validation/performance_validation.py
```

#### Option 2: Staging Environment
```bash
cd "AFIRGEN FINAL"
python tests/validation/performance_validation.py http://staging-url:8000
```

### Expected Output

The script will test the following and generate a report:

```
============================================================
BEDROCK MIGRATION - PERFORMANCE VALIDATION
============================================================

Testing audio transcription performance...
Testing document OCR performance...
Testing legal narrative generation performance...
Testing vector similarity search performance...
Testing end-to-end FIR generation performance...
Testing 10 concurrent requests...

============================================================
PERFORMANCE VALIDATION REPORT
============================================================
Timestamp: 2024-01-15 14:30:00

Individual Component Tests:
------------------------------------------------------------
✓ PASS | audio_transcription        |   X.XXs /    180s
✓ PASS | document_ocr               |   X.XXs /     30s
✓ PASS | legal_narrative            |   X.XXs /     10s
✓ PASS | vector_search              |   X.XXs /      2s
✓ PASS | end_to_end_fir             |   X.XXs /    300s

Concurrency Test:
------------------------------------------------------------
✓ PASS | Concurrent Requests: 10
       Success Rate: XX.XX% (required: 99.00%)
       Avg Duration: X.XXs
       P95 Duration: X.XXs
       P99 Duration: X.XXs

============================================================
OVERALL RESULT: ✓ PASS or ✗ FAIL
============================================================

Report saved to: performance_validation_report.json
```

## Performance Requirements (from Design Document)

| Requirement | Threshold | Acceptance Criteria |
|-------------|-----------|---------------------|
| Audio Transcription (5 min file) | ≤ 3 minutes (180s) | Completes within threshold |
| Document OCR | ≤ 30 seconds | Completes within threshold |
| Legal Narrative Generation | ≤ 10 seconds | Completes within threshold |
| Vector Similarity Search | ≤ 2 seconds | Completes within threshold |
| End-to-End FIR Generation | ≤ 5 minutes (300s) | Completes within threshold |
| Concurrent Requests | 10 requests | No degradation |
| Success Rate | 99% | Under normal load |

## Validation Checklist

Use this checklist to verify all acceptance criteria:

- [ ] **Audio transcription completes within 3 minutes for 5-minute files**
  - Test: Upload 5-minute audio file via `/process` endpoint
  - Measure: Time from upload to transcription completion
  - Pass: Duration < 180 seconds

- [ ] **Document OCR completes within 30 seconds**
  - Test: Upload document image via `/process` endpoint
  - Measure: Time from upload to text extraction completion
  - Pass: Duration < 30 seconds

- [ ] **Legal narrative generation completes within 10 seconds**
  - Test: Submit text complaint via `/process` endpoint
  - Measure: Time to generate formal narrative
  - Pass: Duration < 10 seconds

- [ ] **Vector similarity search completes within 2 seconds**
  - Test: Measured as part of end-to-end FIR generation
  - Measure: Internal vector search operation time
  - Pass: Duration < 2 seconds

- [ ] **End-to-end FIR generation completes within 5 minutes**
  - Test: Complete workflow from text input to finalized FIR
  - Measure: Total time including all validation steps
  - Pass: Duration < 300 seconds

- [ ] **System maintains 99% success rate under normal load**
  - Test: Run multiple requests and calculate success rate
  - Measure: (Successful requests / Total requests) * 100
  - Pass: Success rate ≥ 99%

- [ ] **System handles 10 concurrent requests without degradation**
  - Test: Submit 10 simultaneous requests
  - Measure: Success rate and average latency
  - Pass: All requests succeed, latency < 1.5x baseline

- [ ] **Performance metrics logged to CloudWatch**
  - Verify: Check CloudWatch Logs for performance metrics
  - Check: Latency, success rate, token usage metrics present

- [ ] **Performance report generated**
  - Verify: `performance_validation_report.json` file created
  - Check: Contains all test results and metrics

## Interpreting Results

### Success Criteria
- All individual tests show **✓ PASS**
- Concurrent test shows **✓ PASS**
- Overall result shows **✓ PASS**
- Success rate ≥ 99%

### If Tests Fail

#### Audio/Image Tests Skipped
```
⚠ Skipping: Test audio file not found
```
**Action**: This is expected if test fixtures are not available. Text-based tests will still run.

#### Performance Below Threshold
```
✗ FAIL | legal_narrative | 15.23s / 10s
```
**Possible Causes**:
1. AWS service latency (Bedrock API slow)
2. Network connectivity issues
3. Application not optimized
4. Resource constraints (CPU, memory)

**Actions**:
1. Check CloudWatch metrics for AWS service latency
2. Review application logs for errors or retries
3. Verify network connectivity to AWS services
4. Check EC2 instance resources (CPU, memory usage)
5. Review Bedrock API quotas and throttling

#### Low Success Rate
```
Success Rate: 85.00% (required: 99.00%)
```
**Possible Causes**:
1. Application errors or crashes
2. AWS service throttling
3. Database connection issues
4. Timeout errors

**Actions**:
1. Review application error logs
2. Check AWS service quotas and limits
3. Verify database connectivity
4. Increase timeout values if needed

## CloudWatch Metrics to Monitor

During performance validation, monitor these CloudWatch metrics:

1. **Application Metrics**:
   - `AFIRGen/Bedrock/RequestCount`
   - `AFIRGen/Bedrock/RequestLatency`
   - `AFIRGen/Bedrock/ErrorRate`

2. **Bedrock Metrics**:
   - `AWS/Bedrock/InvocationLatency`
   - `AWS/Bedrock/TokenUsage`
   - `AWS/Bedrock/ThrottledRequests`

3. **Transcribe Metrics**:
   - `AWS/Transcribe/TranscriptionJobDuration`
   - `AWS/Transcribe/FailedJobs`

4. **Textract Metrics**:
   - `AWS/Textract/ResponseTime`
   - `AWS/Textract/UserErrorCount`

## Next Steps After Validation

### If All Tests Pass ✓
1. Mark Task 12.2 as complete
2. Save performance report for documentation
3. Proceed to Task 12.3: Cost Validation

### If Tests Fail ✗
1. Investigate failures using troubleshooting guide
2. Fix identified issues
3. Re-run performance validation
4. Document any changes made
5. Update performance baselines if needed

## Files Modified/Created

### Modified
- `AFIRGEN FINAL/tests/validation/performance_validation.py`
  - Updated to use correct API endpoints
  - Added graceful handling for missing fixtures
  - Improved error reporting

### Created
- `AFIRGEN FINAL/tests/validation/README.md`
  - Comprehensive guide for running validations
  - Troubleshooting information
  - Performance baselines

- `AFIRGEN FINAL/TASK-12.2-PERFORMANCE-VALIDATION-GUIDE.md` (this file)
  - Execution guide for Task 12.2
  - Validation checklist
  - Interpretation guide

## Summary

The performance validation infrastructure is now ready. To complete Task 12.2:

1. **Start the application** (if not already running)
2. **Run the validation script**: `python tests/validation/performance_validation.py`
3. **Review the results** against the acceptance criteria
4. **Address any failures** using the troubleshooting guide
5. **Document the results** in the performance report
6. **Mark the task complete** when all criteria are met

The validation script is designed to be flexible:
- Works with or without test fixtures
- Provides detailed error messages
- Generates machine-readable JSON report
- Includes performance baselines for comparison

## Contact/Support

For issues during validation:
1. Check application logs in `AFIRGEN FINAL/main backend/logs/`
2. Review CloudWatch Logs for AWS service errors
3. Consult the troubleshooting section in `tests/validation/README.md`
4. Review the main project documentation
