# Pre-Deployment Checklist - AFIRGen Production

**Date:** March 2, 2026  
**Deployment Target:** Production  
**Estimated Time:** 2.5 hours

---

## ✅ Pre-Deployment Verification

### 1. System Requirements

- [ ] AWS CLI installed and configured
- [ ] Terraform installed (v1.0+)
- [ ] Python 3.8+ installed
- [ ] SSH key configured for EC2 access
- [ ] Git repository up to date

**Verify:**
```bash
aws --version
terraform --version
python3 --version
ssh -V
```

### 2. AWS Credentials

- [ ] AWS credentials configured (`~/.aws/credentials`)
- [ ] Correct AWS account verified
- [ ] IAM permissions verified (Admin or equivalent)
- [ ] AWS region set to us-east-1

**Verify:**
```bash
aws sts get-caller-identity
aws configure get region
```

### 3. Environment Configuration

- [ ] `.env.bedrock` file exists
- [ ] All required environment variables set
- [ ] Database credentials configured
- [ ] API keys configured
- [ ] Bedrock model access verified

**Verify:**
```bash
cd "AFIRGEN FINAL"
test -f .env.bedrock && echo "✅ .env.bedrock exists" || echo "❌ Missing"
```

### 4. Terraform Configuration

- [ ] `terraform.tfvars` configured
- [ ] AWS account ID set
- [ ] Region set correctly
- [ ] Instance types verified
- [ ] No syntax errors

**Verify:**
```bash
cd "AFIRGEN FINAL/terraform/free-tier"
terraform init
terraform validate
```

### 5. Code Quality

- [ ] All 9 bugs fixed
- [ ] All tests passing
- [ ] No syntax errors
- [ ] Security vulnerabilities resolved
- [ ] Code review findings addressed

**Verify:**
```bash
cd "AFIRGEN FINAL"
python tests/api/test_endpoints_minimal.py
```

### 6. Dependencies

- [ ] `requirements.txt` up to date
- [ ] All Python packages available
- [ ] No conflicting versions
- [ ] Test dependencies documented

**Verify:**
```bash
cd "AFIRGEN FINAL"
pip install --dry-run -r requirements.txt
```

### 7. Database

- [ ] Migration scripts ready
- [ ] Backup strategy defined
- [ ] Connection strings configured
- [ ] Vector database migration plan ready

### 8. Monitoring

- [ ] CloudWatch alarms configured (9 total)
- [ ] SNS topic created
- [ ] Email notifications configured
- [ ] Dashboard JSON ready
- [ ] Log retention set (7 days)

### 9. Security

- [ ] S3 encryption enabled (SSE-KMS)
- [ ] VPC endpoints configured
- [ ] Security groups reviewed
- [ ] IAM roles configured
- [ ] API authentication enabled
- [ ] Rate limiting configured

### 10. Rollback Plan

- [ ] Rollback script tested
- [ ] GGUF fallback available
- [ ] Feature flag configured
- [ ] Backup of current state
- [ ] Rollback time < 5 minutes verified

---

## 🚀 Deployment Readiness Score

**Current Status:** ___/10 sections complete

**Minimum Required:** 10/10 for production deployment

---

## 📋 Pre-Deployment Commands

### Quick Verification Script

Run this to verify all prerequisites:

```bash
cd "AFIRGEN FINAL"

echo "=== Pre-Deployment Verification ==="
echo ""

# 1. Check AWS
echo "1. AWS Credentials:"
aws sts get-caller-identity && echo "✅ AWS OK" || echo "❌ AWS FAIL"
echo ""

# 2. Check Terraform
echo "2. Terraform:"
terraform --version && echo "✅ Terraform OK" || echo "❌ Terraform FAIL"
echo ""

# 3. Check Python
echo "3. Python:"
python3 --version && echo "✅ Python OK" || echo "❌ Python FAIL"
echo ""

# 4. Check Environment
echo "4. Environment File:"
test -f .env.bedrock && echo "✅ .env.bedrock exists" || echo "❌ Missing"
echo ""

# 5. Check Terraform Config
echo "5. Terraform Configuration:"
cd terraform/free-tier
terraform init > /dev/null 2>&1
terraform validate && echo "✅ Terraform config valid" || echo "❌ Terraform config invalid"
cd ../..
echo ""

# 6. Check Tests
echo "6. Minimal Tests:"
python tests/api/test_endpoints_minimal.py && echo "✅ Tests pass" || echo "❌ Tests fail"
echo ""

# 7. Check Scripts
echo "7. Deployment Script:"
test -x scripts/deploy-production-optimized.sh && echo "✅ Script executable" || echo "❌ Script not executable"
echo ""

echo "=== Verification Complete ==="
```

---

## ⚠️ Important Notes

### Before Starting Deployment

1. **Backup Current State**
   - Export current database
   - Save current configuration
   - Document current infrastructure

2. **Notify Stakeholders**
   - Inform team of deployment window
   - Set up on-call rotation
   - Prepare communication channels

3. **Schedule Deployment**
   - Choose low-traffic window
   - Allow 2.5 hours for deployment
   - Have rollback plan ready

4. **Monitor Resources**
   - Watch AWS costs during deployment
   - Monitor CloudWatch metrics
   - Check error logs

### During Deployment

1. **Do Not Interrupt**
   - Let script complete fully
   - Monitor progress in log file
   - Keep terminal session active

2. **Watch for Errors**
   - Check each phase completion
   - Verify health checks pass
   - Monitor CloudWatch alarms

3. **Be Ready to Rollback**
   - Have rollback script ready
   - Monitor application health
   - Check error rates

### After Deployment

1. **Verify Everything**
   - Test all endpoints
   - Check monitoring dashboards
   - Verify cost tracking
   - Test end-to-end FIR generation

2. **Monitor Closely**
   - Watch for 24 hours
   - Check error rates
   - Monitor performance
   - Review cost reports

3. **Document Issues**
   - Log any problems
   - Track resolution time
   - Update runbooks

---

## 🔧 Troubleshooting

### Common Issues

**Issue: AWS credentials not found**
```bash
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1)
```

**Issue: Terraform not initialized**
```bash
cd "AFIRGEN FINAL/terraform/free-tier"
terraform init
```

**Issue: .env.bedrock missing**
```bash
cp .env.example .env.bedrock
# Edit .env.bedrock with your configuration
```

**Issue: Tests failing**
```bash
cd "AFIRGEN FINAL"
python tests/api/test_endpoints_minimal.py
# Review output and fix issues
```

---

## 📞 Emergency Contacts

**DevOps Team:** devops@afirgen.com  
**Security Team:** security@afirgen.com  
**On-Call:** oncall@afirgen.com

---

## ✅ Final Checklist

Before running deployment script:

- [ ] All pre-deployment checks passed
- [ ] Stakeholders notified
- [ ] Backup completed
- [ ] Rollback plan ready
- [ ] Monitoring configured
- [ ] On-call team ready
- [ ] Deployment window scheduled
- [ ] Terminal session stable
- [ ] Log file location noted
- [ ] Emergency contacts available

**Deployment Command:**
```bash
cd "AFIRGEN FINAL/scripts"
./deploy-production-optimized.sh
```

**Estimated Duration:** 2.5 hours

**Rollback Command (if needed):**
```bash
cd "AFIRGEN FINAL/scripts"
./rollback-to-gguf.sh
```

**Rollback Time:** < 5 minutes

---

**Checklist Completed By:** _________________  
**Date:** _________________  
**Time:** _________________

**Approved By:** _________________  
**Date:** _________________

---

**Status:** Ready for deployment when all items checked ✅
