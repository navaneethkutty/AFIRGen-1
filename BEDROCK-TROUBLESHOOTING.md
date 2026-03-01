# Bedrock Troubleshooting Guide

Comprehensive troubleshooting guide for AFIRGen Bedrock architecture issues.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Bedrock Issues](#bedrock-issues)
- [Transcribe Issues](#transcribe-issues)
- [Textract Issues](#textract-issues)
- [Vector Database Issues](#vector-database-issues)
- [Database Issues](#database-issues)
- [Network and Connectivity Issues](#network-and-connectivity-issues)
- [Performance Issues](#performance-issues)
- [Cost Issues](#cost-issues)
- [Deployment Issues](#deployment-issues)
- [Monitoring and Logging](#monitoring-and-logging)

---

## Quick Diagnostics

### Health Check

```bash
# Check overall system health
curl http://<EC2_IP>:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "bedrock": {"status": "connected", "model": "claude-3-sonnet"},
#   "transcribe": {"status": "available"},
#   "textract": {"status": "available"},
#   "vector_db": {"status": "connected", "type": "opensearch", "count": 500},
#   "database": "connected"
# }
```

### Validate Configuration

```bash
# SSH to EC2 instance
ssh -i your-key.pem ubuntu@<EC2_IP>

# Run validation script
cd /opt/afirgen
python scripts/validate-env.py
```

### Check Application Logs

```bash
# View recent logs
tail -f /var/log/afirgen/application.log

# Search for errors
grep ERROR /var/log/afirgen/application.log | tail -20

# Check specific service logs
grep "bedrock" /var/log/afirgen/application.log | tail -20
```

### Check AWS Service Status

```bash
# Check AWS service health
aws health describe-events --region us-east-1

# Check Bedrock availability
aws bedrock list-foundation-models --region us-east-1
```

---

## Bedrock Issues

### Issue: "Bedrock Access Denied"

**Symptoms:**
- Error: `AccessDeniedException: User is not authorized to perform: bedrock:InvokeModel`
- Health check shows bedrock status as "denied"

**Causes:**
1. Model access not requested in AWS Console
2. IAM role missing bedrock permissions
3. Model ID incorrect or not available in region

**Solutions:**

**Solution 1: Request Model Access**
