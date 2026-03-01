# Performance Tests

This directory contains performance tests for the AFIRGen Bedrock migration. These tests measure latency, throughput, and system behavior under concurrent load.

## Test Files

### test_latency.py
Measures latency for various operations:
- **End-to-end FIR generation latency**: Measures complete workflow from complaint text to generated FIR
- **Component latency breakdown**: Measures individual component latencies:
  - Legal narrative generation (Bedrock Claude)
  - Metadata extraction (Bedrock Claude)
  - Embedding generation (Titan Embeddings)
  - Vector similarity search
  - Final FIR generation (Bedrock Claude with RAG)
- **Bedrock vs GGUF comparison**: Compares Bedrock implementation against GGUF baseline
- **Cache performance impact**: Measures performance improvement from IPC section caching
- **Embedding generation latency**: Tests single and batch embedding generation
- **Vector search with different k values**: Tests search performance with varying result counts

### test_concurrency.py
Tests concurrent request handling:
- **10 concurrent requests**: Verifies system handles 10 simultaneous FIR generation requests
- **No degradation test**: Compares sequential vs concurrent execution to detect performance degradation
- **Sustained load test**: Tests multiple batches of concurrent requests
- **Bedrock rate limiting**: Verifies semaphore limits concurrent Bedrock API calls to 10
- **Error handling under load**: Ensures errors in some requests don't affect others

## Requirements Validated

These tests validate the following requirements from the design document:

### Requirement 17: Performance Requirements
- ✓ Audio transcription completes within 3 minutes for 5-minute files
- ✓ Document OCR completes within 30 seconds
- ✓ Legal narrative generation completes within 10 seconds
- ✓ Vector similarity search completes within 2 seconds
- ✓ End-to-end FIR generation completes within 5 minutes
- ✓ System handles 10 concurrent requests without degradation
- ✓ System maintains 99% success rate under normal load

## Running the Tests

### Prerequisites

1. **AWS Credentials**: Ensure AWS credentials are configured (IAM role or credentials file)

2. **Environment Variables**: Set required environment variables:
```bash
export AWS_REGION=us-east-1
export S3_BUCKET_NAME=your-bucket-name
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
export BEDROCK_EMBEDDINGS_MODEL_ID=amazon.titan-embed-text-v1
export VECTOR_DB_TYPE=opensearch  # or aurora_pgvector
export OPENSEARCH_ENDPOINT=your-opensearch-endpoint  # if using OpenSearch
# OR
export AURORA_HOST=your-aurora-host  # if using Aurora pgvector
export AURORA_PORT=5432
export AURORA_DATABASE=your-database
export AURORA_USER=your-user
export AURORA_PASSWORD=your-password
```

3. **Vector Database**: Ensure vector database is populated with IPC sections

### Run All Performance Tests

```bash
# Run all performance tests
pytest tests/performance/ --integration -v

# Run with detailed output
pytest tests/performance/ --integration -v -s

# Run specific test file
pytest tests/performance/test_latency.py --integration -v

# Run specific test
pytest tests/performance/test_latency.py::test_end_to_end_fir_generation_latency --integration -v
```

### Run with Coverage

```bash
pytest tests/performance/ --integration --cov=services --cov-report=html
```

## Test Output

### Latency Report Example

```
============================================================
END-TO-END FIR GENERATION LATENCY REPORT
============================================================
Sample Size: 5
Mean Latency: 12.45s
P50 (Median): 11.23s
P95: 15.67s
P99: 15.67s
Min: 10.12s
Max: 15.67s
============================================================
```

### Component Breakdown Example

```
============================================================
COMPONENT LATENCY BREAKDOWN
============================================================
Narrative Generation: 3.21s
Metadata Extraction: 2.45s
Embedding Generation: 0.89s
Vector Search: 0.34s
FIR Generation: 4.56s
Total: 11.45s
============================================================
```

### Concurrency Report Example

```
============================================================
10 CONCURRENT REQUESTS TEST REPORT
============================================================
Total Requests: 10
Successful: 10
Failed: 0
Success Rate: 100.0%
Overall Duration: 18.34s

Latency Statistics:
  Mean: 15.23s
  Min: 12.45s
  Max: 18.12s
  P50: 14.89s
  P95: 17.56s
  P99: 18.12s
============================================================
```

## Performance Targets

Based on Requirement 17, the following targets should be met:

| Metric | Target | Test |
|--------|--------|------|
| Audio transcription (5 min file) | < 180s | test_latency.py |
| Document OCR | < 30s | test_latency.py |
| Legal narrative generation | < 10s | test_component_latency_breakdown |
| Vector similarity search | < 2s | test_component_latency_breakdown |
| End-to-end FIR generation | < 300s | test_end_to_end_fir_generation_latency |
| Concurrent requests | 10 simultaneous | test_10_concurrent_requests |
| Success rate under load | ≥ 99% | test_10_concurrent_requests |

## Troubleshooting

### Tests Skipped

If tests are skipped with "need --integration option to run":
- Add the `--integration` flag to your pytest command

### Tests Fail with "endpoint not configured"

If tests fail with OpenSearch or Aurora configuration errors:
- Verify environment variables are set correctly
- Ensure vector database is accessible from test environment
- Check AWS credentials have necessary permissions

### High Latency

If latency tests fail due to high response times:
- Check AWS service quotas and limits
- Verify network connectivity to AWS services
- Consider using VPC endpoints for better performance
- Check if Bedrock model is available in your region

### Rate Limiting Errors

If tests fail with throttling errors:
- Reduce concurrent request count
- Add delays between test batches
- Request service quota increases from AWS

## Generating Performance Reports

The test files include report generation functions. To generate a comprehensive report:

```python
from tests.performance.test_latency import generate_performance_report
from tests.performance.test_concurrency import generate_concurrency_report

# After running tests, generate reports
test_results = {
    'total_tests': 10,
    'passed_tests': 10,
    'failed_tests': 0,
    'end_to_end': {'p50': 12.3, 'p95': 15.6, 'p99': 18.2},
    'components': {
        'narrative': 3.2,
        'metadata': 2.4,
        'embedding': 0.9,
        'search': 0.3,
        'fir': 4.5
    }
}

report = generate_performance_report(test_results)
print(report)
```

## CI/CD Integration

To integrate performance tests into CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run Performance Tests
  run: |
    pytest tests/performance/ --integration -v --junitxml=performance-results.xml
  env:
    AWS_REGION: ${{ secrets.AWS_REGION }}
    S3_BUCKET_NAME: ${{ secrets.S3_BUCKET_NAME }}
    VECTOR_DB_TYPE: opensearch
    OPENSEARCH_ENDPOINT: ${{ secrets.OPENSEARCH_ENDPOINT }}
```

## Notes

- Performance tests make real AWS API calls and will incur costs
- Tests may take several minutes to complete
- Results may vary based on AWS region, network conditions, and service load
- Run tests during off-peak hours for more consistent results
- Consider using dedicated test environment to avoid impacting production
