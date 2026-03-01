# Integration Tests for AWS Services

This directory contains integration tests that call real AWS services to verify end-to-end functionality of the AFIRGen Bedrock migration.

## Prerequisites

### 1. AWS Credentials

Integration tests require valid AWS credentials with permissions for:
- Amazon Transcribe
- Amazon Textract
- Amazon Bedrock (Claude 3 Sonnet and Titan Embeddings)
- Amazon S3
- OpenSearch Serverless OR Aurora PostgreSQL with pgvector

Configure credentials using one of:
- IAM role (recommended for EC2)
- AWS credentials file (`~/.aws/credentials`)
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)

### 2. Environment Variables

Set the following environment variables before running tests:

```bash
# Required
export AWS_REGION=us-east-1
export S3_BUCKET_NAME=your-bucket-name
export VECTOR_DB_TYPE=opensearch  # or aurora_pgvector

# For OpenSearch
export OPENSEARCH_ENDPOINT=https://your-opensearch-endpoint

# For Aurora pgvector
export AURORA_HOST=your-aurora-host
export AURORA_PORT=5432
export AURORA_DATABASE=afirgen
export AURORA_USER=your-user
export AURORA_PASSWORD=your-password

# Optional
export KMS_KEY_ID=your-kms-key-id
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
export BEDROCK_EMBEDDINGS_MODEL_ID=amazon.titan-embed-text-v1
```

### 3. Test Data

Some tests require sample audio and image files. The tests include placeholder data generators, but for comprehensive testing, provide real test files:

- `test_data/sample_audio_hindi.mp3` - Hindi audio complaint
- `test_data/sample_audio_english.mp3` - English audio complaint
- `test_data/sample_document.png` - Document image with text
- `test_data/sample_form.png` - Form image with fields

## Running Tests

### Run All Integration Tests

```bash
pytest tests/integration/ --integration -v
```

### Run Specific Test File

```bash
pytest tests/integration/test_transcribe_integration.py --integration -v
```

### Run Specific Test

```bash
pytest tests/integration/test_bedrock_integration.py::test_generate_formal_narrative --integration -v
```

### Run with Coverage

```bash
pytest tests/integration/ --integration --cov=services --cov-report=html
```

## Test Structure

### test_transcribe_integration.py
Tests Amazon Transcribe audio transcription:
- Hindi and English language transcription
- Automatic language detection
- Invalid format handling
- S3 cleanup verification

### test_textract_integration.py
Tests Amazon Textract document OCR:
- Text extraction from images
- Form field extraction
- Multiple image formats (JPEG, PNG)
- Invalid format handling

### test_bedrock_integration.py
Tests Amazon Bedrock legal text processing:
- Formal narrative generation
- Metadata extraction
- Complete FIR generation with RAG
- Concurrent API calls
- Token usage tracking
- Retry logic on throttling

### test_vector_db_integration.py
Tests Titan Embeddings and Vector Database:
- Embedding generation (single and batch)
- Embedding similarity verification
- Vector database insert and search
- Top-k parameter validation
- Both OpenSearch and Aurora pgvector

### test_fir_generation_integration.py
Tests complete FIR generation workflow:
- FIR generation from text
- FIR generation from audio (with transcription)
- FIR generation from image (with OCR)
- IPC cache effectiveness
- End-to-end performance

## Resource Cleanup

Integration tests automatically clean up resources after execution:
- Temporary S3 files are deleted
- Transcription jobs are removed
- Test vector database entries can be cleaned up

To manually clean up test resources:

```bash
# Delete test S3 objects
aws s3 rm s3://your-bucket/transcribe-temp/ --recursive
aws s3 rm s3://your-bucket/textract-temp/ --recursive

# Delete test vector database entries
# (depends on your vector DB implementation)
```

## Cost Considerations

Integration tests call real AWS services and incur costs:

- **Transcribe**: ~$0.024 per minute of audio
- **Textract**: ~$0.0015 per page
- **Bedrock Claude**: ~$0.003 per 1K input tokens, ~$0.015 per 1K output tokens
- **Bedrock Titan Embeddings**: ~$0.0001 per 1K input tokens
- **OpenSearch Serverless**: ~$0.24 per OCU-hour
- **Aurora Serverless**: ~$0.12 per ACU-hour

Estimated cost per full test run: **$0.50 - $2.00**

To minimize costs:
- Run integration tests only when needed (not on every commit)
- Use small test data files
- Clean up resources promptly
- Consider using AWS Free Tier where available

## Troubleshooting

### Tests Skip with "need --integration option"

Add the `--integration` flag to run integration tests:
```bash
pytest tests/integration/ --integration
```

### "S3_BUCKET_NAME environment variable not set"

Set required environment variables before running tests.

### "OpenSearch endpoint not configured"

If using OpenSearch, set `OPENSEARCH_ENDPOINT`. If using Aurora, set Aurora configuration variables.

### Throttling Errors

If tests fail with throttling errors:
- Reduce concurrent test execution
- Add delays between tests
- Request service quota increases from AWS

### Permission Errors

Ensure IAM role/user has required permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "transcribe:*",
        "textract:*",
        "bedrock:InvokeModel",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "*"
    }
  ]
}
```

## CI/CD Integration

To run integration tests in CI/CD pipelines:

1. Store AWS credentials as secrets
2. Set environment variables in pipeline configuration
3. Run tests in dedicated stage:

```yaml
# Example GitHub Actions
integration-tests:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v2
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    - name: Run integration tests
      run: pytest tests/integration/ --integration -v
      env:
        S3_BUCKET_NAME: ${{ secrets.S3_BUCKET_NAME }}
        VECTOR_DB_TYPE: opensearch
        OPENSEARCH_ENDPOINT: ${{ secrets.OPENSEARCH_ENDPOINT }}
```

## Best Practices

1. **Isolate test data**: Use unique identifiers for test resources
2. **Clean up resources**: Always clean up in `finally` blocks
3. **Use timeouts**: Set reasonable timeouts for long-running operations
4. **Mock when possible**: Use unit tests with mocks for most testing
5. **Run integration tests sparingly**: Reserve for pre-deployment validation
6. **Monitor costs**: Track AWS costs from integration testing
7. **Parallel execution**: Be careful with parallel test execution to avoid rate limits

## Support

For issues or questions about integration tests:
- Check test logs for detailed error messages
- Review AWS CloudWatch logs for service-specific errors
- Verify IAM permissions and service quotas
- Contact the development team
