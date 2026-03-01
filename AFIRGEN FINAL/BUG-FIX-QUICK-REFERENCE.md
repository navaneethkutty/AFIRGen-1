# Bug Fix Quick Reference Guide

**Quick reference for fixing critical and high-priority bugs discovered in Task 12.5**

---

## Critical Bugs (P0) - FIX IMMEDIATELY

### BUG-0001: S3 SSE-KMS Encryption Not Applied

**Status:** Open  
**Priority:** P0 (Critical)  
**Time to Fix:** 1 hour

#### Quick Fix
```bash
# 1. Navigate to Terraform directory
cd "AFIRGEN FINAL/terraform/free-tier"

# 2. Apply S3 encryption configuration
terraform apply -target=aws_s3_bucket_server_side_encryption_configuration.temp

# 3. Verify encryption is enabled
aws s3api get-bucket-encryption --bucket afirgen-temp-724554528268

# 4. Run regression test
cd ../..
pytest tests/regression/test_s3_encryption.py -v

# 5. Update bug status
python tests/validation/bug_triage.py update --id BUG-0001 --status Fixed --regression-test tests/regression/test_s3_encryption.py
```

#### Expected Output
```json
{
  "ServerSideEncryptionConfiguration": {
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "arn:aws:kms:us-east-1:724554528268:key/..."
      }
    }]
  }
}
```

---

### BUG-0004: Staging Environment Not Deployed

**Status:** Open  
**Priority:** P0 (Critical)  
**Time to Fix:** 2-3 days

#### Quick Fix (Day 1: Prerequisites)
```bash
# 1. Verify AWS access
aws sts get-caller-identity

# 2. Check Bedrock access
aws bedrock list-foundation-models --region us-east-1

# 3. Configure environment
cd "AFIRGEN FINAL"
cp .env.bedrock .env.staging
# Edit .env.staging with your values
python3 scripts/validate-env.py
```

#### Quick Fix (Day 1-2: Deploy Infrastructure)
```bash
# 4. Deploy infrastructure
cd terraform/free-tier
terraform init
terraform plan -out=staging.tfplan
terraform apply staging.tfplan

# Note: Save EC2 IP address from output
```

#### Quick Fix (Day 2: Deploy Application)
```bash
# 5. SSH to EC2 instance
ssh -i your-key.pem ec2-user@{EC2_IP}

# 6. Deploy application
git clone https://github.com/your-org/afirgen.git
cd afirgen/AFIRGEN\ FINAL
pip3 install -r requirements.txt
cp .env.staging .env
uvicorn main\ backend.agentv5:app --host 0.0.0.0 --port 8000
```

#### Quick Fix (Day 3: Validate)
```bash
# 7. Run health checks
python3 scripts/health-check.py --base-url http://{EC2_IP}:8000

# 8. Run E2E tests
export STAGING_BASE_URL=http://{EC2_IP}:8000
export API_KEY={YOUR_API_KEY}
python3 tests/e2e/test_staging_e2e.py

# 9. Update bug status
python tests/validation/bug_triage.py update --id BUG-0004 --status Fixed
```

---

## High Priority Bugs (P1) - FIX BEFORE PRODUCTION

### BUG-0002: VPC Endpoints Not Created

**Status:** Open  
**Priority:** P1 (High)  
**Time to Fix:** 4 hours

#### Quick Fix
```bash
# 1. Navigate to Terraform directory
cd "AFIRGEN FINAL/terraform/free-tier"

# 2. Apply VPC endpoint configurations
terraform apply -target=aws_vpc_endpoint.bedrock_runtime
terraform apply -target=aws_vpc_endpoint.transcribe
terraform apply -target=aws_vpc_endpoint.textract

# 3. Verify endpoints are created
aws ec2 describe-vpc-endpoints --region us-east-1 \
  --filters "Name=vpc-id,Values=vpc-0e420c4cc3f10b810"

# 4. Update application configuration
# Add to .env on EC2 instance
echo "USE_VPC_ENDPOINTS=true" >> .env

# 5. Restart application
sudo systemctl restart afirgen

# 6. Run regression test
cd ../..
pytest tests/regression/test_vpc_endpoints.py -v

# 7. Update bug status
python tests/validation/bug_triage.py update --id BUG-0002 --status Fixed --regression-test tests/regression/test_vpc_endpoints.py
```

#### Expected Output
```
VpcEndpoints:
- VpcEndpointId: vpce-xxxxx
  ServiceName: com.amazonaws.us-east-1.bedrock-runtime
  State: available
- VpcEndpointId: vpce-yyyyy
  ServiceName: com.amazonaws.us-east-1.transcribe
  State: available
- VpcEndpointId: vpce-zzzzz
  ServiceName: com.amazonaws.us-east-1.textract
  State: available
```

---

## Medium Priority Bugs (P2) - DEFERRED TO SPRINT 2

### BUG-0003: SSL Verification Disabled in Test Files

**Status:** Deferred  
**Priority:** P2 (Medium)  
**Time to Fix:** 2 hours

#### Quick Fix (Sprint 2)
```bash
# 1. Add comments to test files
# Edit test_https_tls.py and tests/validation/security_audit.py

# Add this comment before verify=False:
# SSL verification disabled for local testing only
# NEVER disable SSL verification in production code
response = requests.get(url, verify=False)

# 2. Verify production code uses TLS 1.2+
grep -r "verify=False" "AFIRGEN FINAL/services/" "AFIRGEN FINAL/main backend/"
# Should return no results

# 3. Update bug status
python tests/validation/bug_triage.py update --id BUG-0003 --status Fixed
```

---

### BUG-0005: Test Fixtures Missing

**Status:** Deferred  
**Priority:** P2 (Medium)  
**Time to Fix:** 1 hour

#### Quick Fix (Sprint 2)
```bash
# 1. Create fixtures directory
mkdir -p "AFIRGEN FINAL/tests/fixtures"

# 2. Add test audio file (5 minutes long)
# Copy or record a 5-minute audio file
cp /path/to/audio.wav "AFIRGEN FINAL/tests/fixtures/test_audio_5min.wav"

# 3. Add test document image
# Copy or scan a document image
cp /path/to/document.jpg "AFIRGEN FINAL/tests/fixtures/test_document.jpg"

# 4. Run performance validation
python tests/validation/performance_validation.py

# 5. Update bug status
python tests/validation/bug_triage.py update --id BUG-0005 --status Fixed
```

---

## Verification Checklist

### After Fixing BUG-0001 (S3 Encryption)
- [ ] Terraform apply successful
- [ ] AWS CLI shows encryption enabled
- [ ] Regression test passes
- [ ] Security audit passes S3 check
- [ ] Bug status updated to Fixed

### After Fixing BUG-0004 (Staging Deployment)
- [ ] Infrastructure deployed successfully
- [ ] Application running on EC2
- [ ] Health checks passing
- [ ] E2E tests passing
- [ ] Performance validation passing
- [ ] Bug status updated to Fixed

### After Fixing BUG-0002 (VPC Endpoints)
- [ ] Terraform apply successful
- [ ] AWS CLI shows 3 endpoints created
- [ ] All endpoints in 'available' state
- [ ] Application using VPC endpoints
- [ ] Regression test passes
- [ ] Bug status updated to Fixed

---

## Common Issues

### Issue: Terraform Apply Fails
**Solution:**
```bash
# Check Terraform state
terraform state list

# Refresh state
terraform refresh

# Try targeted apply
terraform apply -target=<resource_name>
```

### Issue: AWS CLI Returns "Access Denied"
**Solution:**
```bash
# Verify credentials
aws sts get-caller-identity

# Check IAM permissions
aws iam get-role --role-name afirgen-free-tier-ec2-role

# Verify region
export AWS_REGION=us-east-1
```

### Issue: Regression Test Fails
**Solution:**
```bash
# Run with verbose output
pytest tests/regression/test_name.py -v --tb=short

# Check AWS resource exists
aws s3api head-bucket --bucket afirgen-temp-724554528268
aws ec2 describe-vpc-endpoints --vpc-endpoint-ids vpce-xxxxx

# Verify configuration applied
terraform show | grep <resource_name>
```

---

## Bug Status Commands

### View All Bugs
```bash
python tests/validation/bug_triage.py report
```

### Update Bug Status
```bash
# Mark as Fixed
python tests/validation/bug_triage.py update --id BUG-0001 --status Fixed

# Mark as Verified
python tests/validation/bug_triage.py update --id BUG-0001 --status Verified

# Add regression test
python tests/validation/bug_triage.py update --id BUG-0001 --regression-test tests/regression/test_name.py
```

### Add Bug Note
```bash
python tests/validation/bug_triage.py add-note --id BUG-0001 --note "Applied Terraform configuration successfully"
```

---

## Timeline

### Day 1 (Critical Bugs)
- **Hour 1:** Fix BUG-0001 (S3 encryption)
- **Hours 2-8:** Start BUG-0004 (Deploy staging - Day 1)

### Day 2-3 (Critical Bugs)
- **Day 2:** Continue BUG-0004 (Deploy application)
- **Day 3:** Complete BUG-0004 (Validate and test)

### Day 4 (High Priority Bugs)
- **Hours 1-4:** Fix BUG-0002 (VPC endpoints)
- **Hours 5-8:** Verify all fixes

### Day 5 (Validation)
- **Full Day:** Run complete validation suite
- Generate final bug report
- Prepare for Task 12.6 (Production Readiness Review)

---

## Success Criteria

### All Critical Bugs Fixed
- ✅ BUG-0001: S3 encryption enabled
- ✅ BUG-0004: Staging environment deployed

### All High Priority Bugs Fixed
- ✅ BUG-0002: VPC endpoints created

### All Regression Tests Passing
- ✅ test_s3_encryption.py (6 tests)
- ✅ test_vpc_endpoints.py (10 tests)

### All Fixes Verified on Staging
- ✅ Security audit passes
- ✅ Performance validation passes
- ✅ E2E tests pass

---

## Next Steps

After fixing all P0 and P1 bugs:

1. **Generate Final Report**
   ```bash
   python tests/validation/bug_triage.py report
   ```

2. **Run Full Validation Suite**
   ```bash
   python tests/validation/run_all_validations.py
   ```

3. **Proceed to Task 12.6**
   - Production Readiness Review
   - Stakeholder approval
   - Production deployment planning

---

**Last Updated:** 2026-03-01  
**Maintained By:** DevOps Team  
**Related Docs:** TASK-12.5-BUG-TRIAGE-REPORT.md, bugs.json
