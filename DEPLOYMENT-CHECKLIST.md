# AFIRGen AWS Deployment Checklist

Use this checklist to track your deployment progress.

## Pre-Deployment

- [ ] AWS account created
- [ ] AWS Builder ID created
- [ ] Computer with internet connection
- [ ] At least 10GB free disk space (for model downloads)

## Step 1: Tool Installation (2 minutes)

```bash
make install-tools
```

- [ ] Terraform installed
- [ ] AWS CLI installed
- [ ] Tools verified with `terraform --version` and `aws --version`

## Step 2: AWS Configuration (1 minute)

```bash
make setup-aws
```

- [ ] AWS Access Key ID entered
- [ ] AWS Secret Access Key entered
- [ ] Region set to `us-east-1`
- [ ] Credentials verified with `aws sts get-caller-identity`

## Step 3: Deployment (30-40 minutes)

```bash
make deploy-all
```

### 3.1 Infrastructure Deployment (10-15 min)
- [ ] Terraform initialized
- [ ] VPC created
- [ ] Subnets created (1 public, 2 private)
- [ ] Security groups created
- [ ] EC2 instance launched
- [ ] RDS database created
- [ ] S3 buckets created
- [ ] Elastic IP assigned

### 3.2 Model Downloads (15-20 min)
- [ ] complaint_2summarizing.gguf downloaded (~1.5GB)
- [ ] complaint_summarizing_model.gguf downloaded (~1.5GB)
- [ ] BNS-RAG-q4k.gguf downloaded (~2GB)
- [ ] Whisper model downloaded (~75MB)
- [ ] Donut OCR model downloaded (~500MB)
- [ ] Models uploaded to S3

### 3.3 Knowledge Base Downloads (2-5 min)
- [ ] BNS_basic_chroma.jsonl downloaded
- [ ] BNS_details_chroma.jsonl downloaded
- [ ] BNS_spacts_chroma.jsonl downloaded
- [ ] BNS_basic.jsonl downloaded
- [ ] BNS_indepth.jsonl downloaded
- [ ] spacts.jsonl downloaded

### 3.4 Configuration (1 min)
- [ ] .env file generated
- [ ] Secure keys created
- [ ] RDS endpoint configured
- [ ] CORS origins set
- [ ] API URLs configured

### 3.5 Application Deployment (5-10 min)
- [ ] Application files copied to EC2
- [ ] Knowledge base files copied to EC2
- [ ] Docker containers started
- [ ] Main backend healthy
- [ ] GGUF model server healthy
- [ ] ASR/OCR server healthy
- [ ] MySQL connected
- [ ] Redis connected
- [ ] Nginx running

### 3.6 Verification (1 min)
- [ ] Health endpoint responds
- [ ] Frontend accessible
- [ ] API documentation accessible
- [ ] All services running

## Post-Deployment

### Access URLs
Record your URLs here:

- Frontend: http://________________
- API: http://________________:8000
- API Docs: http://________________:8000/docs

### Credentials
Save these securely (from .env file):

- MySQL Password: ________________
- API Key: ________________
- Auth Key: ________________

### Testing
- [ ] Open frontend in browser
- [ ] Test FIR generation
- [ ] Test speech-to-text (if available)
- [ ] Test OCR (if available)
- [ ] Check database records at `/view_fir_records`

### Monitoring
- [ ] CloudWatch dashboard accessible
- [ ] Logs visible in CloudWatch
- [ ] Metrics being collected
- [ ] Alarms configured

## Optional Steps

### SSL/HTTPS Setup (if needed)
- [ ] Domain name purchased
- [ ] Domain pointed to Elastic IP
- [ ] Let's Encrypt certificate generated
- [ ] HTTPS enabled
- [ ] HTTP redirects to HTTPS

### Security Hardening
- [ ] AWS Secrets Manager enabled
- [ ] Security groups reviewed
- [ ] IAM roles reviewed
- [ ] CloudTrail enabled
- [ ] MFA enabled on AWS account

### Performance Optimization
- [ ] CloudWatch metrics reviewed
- [ ] Resource limits adjusted
- [ ] Connection pools tuned
- [ ] Cache settings optimized

## Troubleshooting

If something fails, check:

- [ ] Error message in terminal
- [ ] AWS Console for resource status
- [ ] CloudWatch logs
- [ ] EC2 instance logs: `make logs`
- [ ] Terraform state: `make status`

Common issues:
- [ ] AWS credentials expired → Run `make setup-aws` again
- [ ] Insufficient permissions → Check IAM user permissions
- [ ] Resource limits → Check AWS service quotas
- [ ] Network issues → Check security groups
- [ ] Disk space → Check EC2 instance storage

## Cleanup (When Done Testing)

To remove all resources and stop charges:

```bash
make clean
```

- [ ] Confirmed cleanup
- [ ] All resources destroyed
- [ ] S3 buckets emptied
- [ ] No remaining charges

## Cost Monitoring

### Free Tier Limits
- [ ] EC2: 750 hours/month (1 t2.micro 24/7 = 720 hours ✓)
- [ ] RDS: 750 hours/month (1 db.t3.micro 24/7 = 720 hours ✓)
- [ ] EBS: 30 GB (using 50 GB total - may incur small charge)
- [ ] S3: 5 GB (using ~5 GB ✓)
- [ ] Data Transfer: 100 GB/month

### Monthly Cost Check
- [ ] Week 1: Check AWS billing dashboard
- [ ] Week 2: Verify free tier usage
- [ ] Week 3: Review CloudWatch costs
- [ ] Week 4: Check for unexpected charges

## Maintenance Schedule

### Daily (Automated)
- [ ] Database backups
- [ ] Log rotation
- [ ] Health checks

### Weekly (Manual)
- [ ] Review CloudWatch metrics
- [ ] Check disk space
- [ ] Review application logs
- [ ] Test backup restoration

### Monthly (Manual)
- [ ] Update Docker images
- [ ] Review security groups
- [ ] Check AWS free tier usage
- [ ] Update SSL certificates (if using Let's Encrypt)

## Success Criteria

Your deployment is successful when:

- [ ] All services show "healthy" status
- [ ] Frontend loads without errors
- [ ] API responds to requests
- [ ] FIR generation works end-to-end
- [ ] Database stores records
- [ ] Monitoring shows metrics
- [ ] No error logs in CloudWatch
- [ ] Cost is $0 (within free tier)

## Notes

Use this space for your own notes:

```
Date deployed: _______________
EC2 Instance ID: _______________
RDS Endpoint: _______________
Issues encountered: _______________
_______________
_______________
```

---

## Quick Reference

**Deploy**: `make deploy-all`
**Status**: `make status`
**Logs**: `make logs`
**SSH**: `make ssh`
**Restart**: `make restart`
**Update**: `make update`
**Clean**: `make clean`

---

**Deployment Time**: ~45 minutes
**Cost**: $0 for 12 months
**Automation**: 95%

Good luck with your deployment! 🚀
