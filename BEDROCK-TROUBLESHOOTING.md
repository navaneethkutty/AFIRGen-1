# Bedrock Troubleshooting Guide

Comprehensive troubleshooting guide for AFIRGen Bedrock architecture.

## Quick Diagnostics

### Health Check
\\ash
curl http://<EC2_IP>:8000/health
\
### Validate Configuration
\\ash
python scripts/validate-env.py
\
### Check Logs
\\ash
tail -f /var/log/afirgen/application.log
grep ERROR /var/log/afirgen/application.log | tail -20
\
## Bedrock Issues

### Bedrock Access Denied

**Symptoms:** AccessDeniedException: User is not authorized to perform: bedrock:InvokeModel

**Solutions:**
1. Request model access: AWS Console  Bedrock  Model access  Request access to Claude 3 Sonnet and Titan Embeddings
2. Verify IAM permissions: aws iam get-role-policy --role-name afirgen-ec2-role --policy-name BedrockAccess
3. Check model ID in .env.bedrock matches exactly

### Bedrock Throttling

**Symptoms:** ThrottlingException: Rate exceeded

**Solutions:**
1. Request quota increase: AWS Console  Service Quotas  Bedrock
2. Ensure retry settings configured: MAX_RETRIES=2, BASE_DELAY=1.0, MAX_DELAY=60.0
3. Implement request batching

### Bedrock High Latency

**Symptoms:** Requests taking >10 seconds

**Solutions:**
1. Use region closest to users (us-east-1, us-west-2, ap-southeast-1, eu-central-1)
2. Verify VPC endpoint exists
3. Optimize prompts: reduce length, use lower temperature, consider Claude 3 Haiku

## Transcribe Issues

### Transcribe Job Failed

**Symptoms:** TranscribeJobFailed: Job failed with status FAILED

**Solutions:**
1. Check audio format (supported: WAV, MP3, MPEG)
2. Verify S3 permissions: IAM role must have s3:GetObject on temp bucket
3. Check language code is supported (hi-IN, en-IN, ta-IN, te-IN, bn-IN, mr-IN, gu-IN, kn-IN, ml-IN, pa-IN)

### Transcribe High Costs

**Solutions:**
1. Implement caching (already in TranscribeClient)
2. Optimize audio: ffmpeg -i input.mp3 -ar 16000 -ac 1 output.mp3 (16kHz mono sufficient)

## Textract Issues

### Textract Extraction Failed

**Symptoms:** TextractException: Document analysis failed

**Solutions:**
1. Check image format (supported: JPEG, PNG)
2. Ensure minimum 150 DPI, maximum 10 MB, clear high-contrast images
3. Verify S3 permissions

## Vector Database Issues

### OpenSearch Connection Failed

**Symptoms:** ConnectionError: Unable to connect to OpenSearch

**Solutions:**
1. Check security group allows EC2  OpenSearch on port 443
2. Verify VPC endpoint accessible
3. Check IAM permissions: aoss:APIAccessAll

### Aurora pgvector Connection Failed

**Symptoms:** OperationalError: could not connect to server

**Solutions:**
1. Check security group allows EC2  RDS on port 5432
2. Verify credentials in .env.bedrock
3. Check pgvector extension installed

### Vector Search Returns No Results

**Solutions:**
1. Verify data migration: python scripts/verify_migration.py
2. Check vector count
3. Re-run migration: python scripts/migrate_vector_db.py

## Database Issues

### MySQL Connection Failed

**Symptoms:** OperationalError: (2003, Can't connect to MySQL server)

**Solutions:**
1. Check security group allows EC2  RDS on port 3306
2. Verify credentials in .env.bedrock
3. Check RDS status

## Network Issues

### VPC Endpoint Not Working

**Symptoms:** Slow responses, high data transfer costs, timeouts

**Solutions:**
1. Verify VPC endpoints exist for: bedrock-runtime, transcribe, textract, s3
2. Check route tables have VPC endpoint routes
3. Verify VPC endpoint security group allows inbound from EC2

## Performance Issues

### Slow FIR Generation

**Symptoms:** FIR generation takes >5 minutes

**Solutions:**
1. Check CloudWatch metrics for latency breakdown
2. Enable caching: ENABLE_CACHING=true, CACHE_MAX_SIZE=100
3. Optimize vector search

### High Memory Usage

**Symptoms:** EC2 instance running out of memory

**Solutions:**
1. Upgrade instance type: instance_type = t3.medium in terraform.tfvars
2. Reduce cache size: CACHE_MAX_SIZE=50

## Cost Issues

### Unexpected High Costs

**Solutions:**
1. Check cost breakdown
2. Switch to Aurora pgvector (saves ~/month)
3. Set up cost alerts
4. Enable caching to reduce API calls
5. Optimize Bedrock prompts

## Deployment Issues

### Terraform Apply Failed

**Solutions:**
1. Verify AWS credentials
2. Check Terraform state
3. Check resource limits

### Application Won't Start

**Solutions:**
1. Check logs: sudo journalctl -u afirgen-backend -n 50
2. Check port binding: sudo netstat -tulpn | grep 8000
3. Restart: sudo systemctl restart afirgen-backend

## Monitoring

### CloudWatch Metrics
AWS Console  CloudWatch  Dashboards  afirgen-bedrock-dashboard

### X-Ray Traces
AWS Console  X-Ray  Traces  Filter by: Service name = afirgen-backend

### Application Logs
tail -f /var/log/afirgen/application.log

## Getting Help

1. Check AWS Service Health: https://status.aws.amazon.com/
2. Review Documentation: AWS-DEPLOYMENT-PLAN.md, BEDROCK-CONFIGURATION.md
3. AWS Support: Open support case with error messages, correlation IDs, timestamps

## Summary

**Most Common Issues:**
1. Bedrock access not requested  Request in AWS Console
2. IAM permissions missing  Check IAM policies
3. Security groups misconfigured  Allow EC2  Services
4. High costs  Switch to Aurora pgvector, enable caching
5. Slow performance  Enable caching, optimize prompts

**Quick Fixes:**
- Run python scripts/validate-env.py
- Check /var/log/afirgen/application.log
- Verify security groups
- Enable caching
