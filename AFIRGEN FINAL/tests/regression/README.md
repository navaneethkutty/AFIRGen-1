# Regression Tests for Bedrock Migration

This directory contains regression tests for bugs discovered during Task 12.5 (Bug Triage and Fixes). Each test verifies that a specific bug has been fixed and prevents regression in future releases.

## Purpose

Regression tests ensure that:
1. Fixed bugs remain fixed in future releases
2. New code changes don't reintroduce old bugs
3. Critical security and infrastructure issues are continuously validated
4. Production deployments meet all requirements

## Test Coverage

### BUG-0001: S3 SSE-KMS Encryption Not Applied
**File:** `test_s3_encryption.py`  
**Priority:** P0 (Critical)  
**Component:** S3 Storage

**Tests:**
- `test_s3_bucket_exists` - Verify S3 bucket exists
- `test_s3_bucket_encryption_enabled` - Verify encryption is enabled
- `test_s3_bucket_uses_kms_encryption` - Verify KMS encryption (not AES256)
- `test_s3_bucket_has_kms_key` - Verify KMS key is specified
- `test_s3_bucket_encryption_enforced` - Verify encryption is enforced
- `test_s3_upload_with_encryption` - Verify uploads work with encryption

**Why This Matters:**
Without S3 encryption, sensitive audio and image files containing complaint data would be stored unencrypted at rest, creating a critical security vulnerability and compliance violation.

---

### BUG-0002: VPC Endpoints Not Created for AWS Services
**File:** `test_vpc_endpoints.py`  
**Priority:** P1 (High)  
**Component:** VPC Networking

**Tests:**
- `test_vpc_exists` - Verify VPC exists
- `test_vpc_endpoints_exist` - Verify all 3 endpoints exist
- `test_bedrock_runtime_endpoint_exists` - Verify Bedrock endpoint
- `test_transcribe_endpoint_exists` - Verify Transcribe endpoint
- `test_textract_endpoint_exists` - Verify Textract endpoint
- `test_vpc_endpoints_are_available` - Verify endpoints are available
- `test_vpc_endpoints_have_security_groups` - Verify security groups
- `test_vpc_endpoints_in_correct_subnets` - Verify subnet placement
- `test_s3_gateway_endpoint_exists` - Verify S3 endpoint (related)
- `test_vpc_endpoint_dns_enabled` - Verify private DNS enabled

**Why This Matters:**
Without VPC endpoints, AWS service traffic routes through the internet gateway, increasing costs (~$5-10/month), reducing security (traffic leaves VPC), and slightly increasing latency.

---

## Running Tests

### Run All Regression Tests
```bash
cd "AFIRGEN FINAL"
pytest tests/regression/ -v
```

### Run Specific Test File
```bash
pytest tests/regression/test_s3_encryption.py -v
pytest tests/regression/test_vpc_endpoints.py -v
```

### Run Specific Test Function
```bash
pytest tests/regression/test_s3_encryption.py::test_s3_bucket_encryption_enabled -v
pytest tests/regression/test_vpc_endpoints.py::test_vpc_endpoints_exist -v
```

### Run with Coverage
```bash
pytest tests/regression/ --cov=services --cov-report=html
```

### Run with Detailed Output
```bash
pytest tests/regression/ -v --tb=short
```

## Prerequisites

### AWS Credentials
Tests require AWS credentials with permissions to:
- S3: `GetBucketEncryption`, `HeadBucket`, `PutObject`, `HeadObject`, `DeleteObject`
- EC2: `DescribeVpcs`, `DescribeVpcEndpoints`

Configure credentials using one of:
```bash
# Environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1

# AWS CLI profile
aws configure

# IAM role (on EC2 instance)
# No configuration needed
```

### Python Dependencies
```bash
pip install pytest boto3 botocore
```

## Test Configuration

### Infrastructure IDs
Tests use the following infrastructure identifiers:

**S3 Bucket:**
- Name: `afirgen-temp-724554528268`
- Region: `us-east-1`

**VPC:**
- ID: `vpc-0e420c4cc3f10b810`
- Region: `us-east-1`

**VPC Endpoints:**
- Bedrock Runtime: `com.amazonaws.us-east-1.bedrock-runtime`
- Transcribe: `com.amazonaws.us-east-1.transcribe`
- Textract: `com.amazonaws.us-east-1.textract`

### Updating Configuration
If infrastructure IDs change, update the constants at the top of each test file:

```python
# test_s3_encryption.py
S3_BUCKET_NAME = "your-bucket-name"
AWS_REGION = "your-region"

# test_vpc_endpoints.py
VPC_ID = "vpc-xxxxxxxxx"
AWS_REGION = "your-region"
```

## Expected Results

### All Tests Passing
```
tests/regression/test_s3_encryption.py::test_s3_bucket_exists PASSED
tests/regression/test_s3_encryption.py::test_s3_bucket_encryption_enabled PASSED
tests/regression/test_s3_encryption.py::test_s3_bucket_uses_kms_encryption PASSED
tests/regression/test_s3_encryption.py::test_s3_bucket_has_kms_key PASSED
tests/regression/test_s3_encryption.py::test_s3_bucket_encryption_enforced PASSED
tests/regression/test_s3_encryption.py::test_s3_upload_with_encryption PASSED

tests/regression/test_vpc_endpoints.py::test_vpc_exists PASSED
tests/regression/test_vpc_endpoints.py::test_vpc_endpoints_exist PASSED
tests/regression/test_vpc_endpoints.py::test_bedrock_runtime_endpoint_exists PASSED
tests/regression/test_vpc_endpoints.py::test_transcribe_endpoint_exists PASSED
tests/regression/test_vpc_endpoints.py::test_textract_endpoint_exists PASSED
tests/regression/test_vpc_endpoints.py::test_vpc_endpoints_are_available PASSED
tests/regression/test_vpc_endpoints.py::test_vpc_endpoints_have_security_groups PASSED
tests/regression/test_vpc_endpoints.py::test_vpc_endpoints_in_correct_subnets PASSED
tests/regression/test_vpc_endpoints.py::test_s3_gateway_endpoint_exists PASSED
tests/regression/test_vpc_endpoints.py::test_vpc_endpoint_dns_enabled PASSED

======================== 16 passed in 5.23s ========================
```

### Test Failures
If tests fail, they provide detailed error messages with remediation steps:

**Example: S3 Encryption Not Enabled**
```
FAILED tests/regression/test_s3_encryption.py::test_s3_bucket_encryption_enabled
S3 bucket afirgen-temp-724554528268 does not have encryption enabled.
This is a CRITICAL security issue (BUG-0001).
Apply Terraform configuration:
terraform apply -target=aws_s3_bucket_server_side_encryption_configuration.temp
```

**Example: VPC Endpoints Missing**
```
FAILED tests/regression/test_vpc_endpoints.py::test_vpc_endpoints_exist
Missing VPC endpoints for services: com.amazonaws.us-east-1.bedrock-runtime, 
com.amazonaws.us-east-1.transcribe, com.amazonaws.us-east-1.textract.
This is a HIGH priority issue (BUG-0002).
Apply Terraform configuration:
terraform apply -target=aws_vpc_endpoint.bedrock_runtime 
-target=aws_vpc_endpoint.transcribe -target=aws_vpc_endpoint.textract
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Regression Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  regression-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install pytest boto3 botocore
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Run regression tests
      run: |
        cd "AFIRGEN FINAL"
        pytest tests/regression/ -v --tb=short
```

### Jenkins Example
```groovy
pipeline {
    agent any
    
    stages {
        stage('Regression Tests') {
            steps {
                sh '''
                    cd "AFIRGEN FINAL"
                    pip install pytest boto3 botocore
                    pytest tests/regression/ -v --tb=short
                '''
            }
        }
    }
    
    post {
        always {
            junit 'tests/regression/results.xml'
        }
    }
}
```

## Troubleshooting

### Test Fails: "Access Denied"
**Problem:** AWS credentials don't have required permissions

**Solution:**
1. Verify AWS credentials are configured
2. Check IAM permissions include S3 and EC2 read access
3. Verify IAM role is attached to EC2 instance (if running on EC2)

### Test Fails: "Bucket Not Found"
**Problem:** S3 bucket doesn't exist or name is incorrect

**Solution:**
1. Verify bucket name in test configuration
2. Check bucket exists: `aws s3 ls s3://afirgen-temp-724554528268`
3. Update `S3_BUCKET_NAME` constant if bucket name changed

### Test Fails: "VPC Not Found"
**Problem:** VPC doesn't exist or ID is incorrect

**Solution:**
1. Verify VPC ID in test configuration
2. Check VPC exists: `aws ec2 describe-vpcs --vpc-ids vpc-0e420c4cc3f10b810`
3. Update `VPC_ID` constant if VPC ID changed

### Test Fails: "Encryption Not Enabled"
**Problem:** S3 encryption configuration not applied

**Solution:**
1. Apply Terraform configuration:
   ```bash
   cd "AFIRGEN FINAL/terraform/free-tier"
   terraform apply -target=aws_s3_bucket_server_side_encryption_configuration.temp
   ```
2. Verify encryption: `aws s3api get-bucket-encryption --bucket afirgen-temp-724554528268`
3. Re-run test

### Test Fails: "VPC Endpoints Missing"
**Problem:** VPC endpoints not created

**Solution:**
1. Apply Terraform configuration:
   ```bash
   cd "AFIRGEN FINAL/terraform/free-tier"
   terraform apply -target=aws_vpc_endpoint.bedrock_runtime
   terraform apply -target=aws_vpc_endpoint.transcribe
   terraform apply -target=aws_vpc_endpoint.textract
   ```
2. Verify endpoints: `aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=vpc-0e420c4cc3f10b810"`
3. Re-run test

## Maintenance

### Adding New Regression Tests
When a new bug is fixed:

1. Create test file: `test_<component>_<issue>.py`
2. Add test functions with descriptive names
3. Include bug ID and priority in docstrings
4. Add remediation steps in failure messages
5. Update this README with test details

### Test Naming Convention
- File: `test_<component>_<issue>.py`
- Function: `test_<what_is_being_tested>`
- Example: `test_s3_bucket_encryption_enabled`

### Documentation Requirements
Each test must include:
- Bug ID and priority in docstring
- Description of what is being tested
- Why the test matters (impact)
- Remediation steps in failure messages

## Related Documentation

- **Bug Triage Report:** `TASK-12.5-BUG-TRIAGE-REPORT.md`
- **Bug Database:** `bugs.json`
- **Security Audit:** `SECURITY-AUDIT-REPORT.md`
- **Deployment Guide:** `STAGING-DEPLOYMENT-GUIDE.md`

## Support

For questions or issues with regression tests:
1. Check this README for troubleshooting steps
2. Review bug triage report for context
3. Check AWS CloudWatch logs for infrastructure issues
4. Contact DevOps team for infrastructure access

---

**Last Updated:** 2026-03-01  
**Maintained By:** QA Team  
**Test Coverage:** 2 bugs, 16 test functions
