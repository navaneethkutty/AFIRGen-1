# AFIRGen AWS Quick Start Guide

Deploy AFIRGen to AWS in 3 simple commands! 🚀

## Prerequisites

1. ✅ AWS Account created (you have this!)
2. ✅ AWS Builder ID created (you have this!)
3. A computer with internet connection

## Step 1: Install Tools (2 minutes)

```bash
make install-tools
```

This installs:
- Terraform (infrastructure automation)
- AWS CLI (AWS management)

## Step 2: Configure AWS (1 minute)

```bash
make setup-aws
```

Enter your AWS credentials when prompted:
- AWS Access Key ID
- AWS Secret Access Key
- Region: `us-east-1`
- Output format: `json`

## Step 3: Deploy Everything (30-40 minutes)

```bash
make deploy-all
```

This automatically:
1. ✅ Creates AWS infrastructure (VPC, EC2, RDS, S3)
2. ✅ Downloads ML models from HuggingFace (~5GB)
3. ✅ Downloads knowledge base from HuggingFace
4. ✅ Generates secure configuration
5. ✅ Uploads everything to AWS
6. ✅ Starts all services
7. ✅ Verifies deployment

**Grab a coffee!** ☕ The deployment takes about 30-40 minutes.

## What You Get

After deployment completes, you'll see:

```
==========================================
Deployment Complete!
==========================================

Your AFIRGen instance is ready at:
  http://XX.XX.XX.XX
```

Access your application:
- **Frontend**: http://XX.XX.XX.XX
- **API**: http://XX.XX.XX.XX:8000
- **API Docs**: http://XX.XX.XX.XX:8000/docs

## Cost

**$0/month** for 12 months (AWS Free Tier)

After 12 months: ~$30-40/month

## Useful Commands

```bash
# Check deployment status
make status

# View application logs
make logs

# SSH to your server
make ssh

# Restart services
make restart

# Update application (after code changes)
make update

# Destroy everything (cleanup)
make clean
```

## Troubleshooting

### "Command not found: make"

**Windows:**
```bash
choco install make
```

**macOS:**
```bash
brew install make
```

**Linux:**
```bash
sudo apt-get install make  # Ubuntu/Debian
sudo yum install make      # CentOS/RHEL
```

### "Terraform not found"

Run `make install-tools` again.

### "AWS credentials not configured"

Run `make setup-aws` again.

### Deployment failed

Check the error message and try:
```bash
# View detailed logs
cd "AFIRGEN FINAL/terraform/free-tier"
terraform plan

# Or ask for help with the error message
```

## What's Happening Behind the Scenes?

The `make deploy-all` command runs these steps:

1. **deploy-infra**: Creates AWS resources with Terraform
   - VPC with public/private subnets
   - EC2 t2.micro instance (1GB RAM, 1 vCPU)
   - RDS db.t3.micro MySQL database
   - S3 buckets for storage
   - Security groups and networking

2. **download-models**: Downloads from HuggingFace
   - complaint_2summarizing.gguf (~1.5GB)
   - complaint_summarizing_model.gguf (~1.5GB)
   - BNS-RAG-q4k.gguf (~2GB)
   - Whisper ASR model (~75MB)
   - Donut OCR model (~500MB)

3. **download-kb**: Downloads knowledge base
   - BNS definitions, detailed sections, special acts
   - General retrieval databases

4. **setup-env**: Generates configuration
   - Secure random keys
   - Database connection strings
   - CORS settings

5. **upload-models-s3**: Uploads models to S3

6. **deploy-app**: Deploys to EC2
   - Copies application files
   - Starts Docker containers
   - Initializes database

7. **verify**: Tests deployment
   - Health checks
   - Service verification

## Manual Deployment (If You Prefer)

If you want more control, follow the detailed guide:
- [AWS-DEPLOYMENT-PLAN.md](AWS-DEPLOYMENT-PLAN.md)

## Next Steps

1. **Test the application**
   - Generate a test FIR
   - Try speech-to-text
   - Test OCR functionality

2. **Monitor usage**
   - Check AWS CloudWatch dashboard
   - Monitor free tier limits

3. **Customize**
   - Update CORS origins for your domain
   - Configure SSL/HTTPS (optional)
   - Adjust rate limits

## Support

- **Detailed Guide**: [AWS-DEPLOYMENT-PLAN.md](AWS-DEPLOYMENT-PLAN.md)
- **Terraform Docs**: [AFIRGEN FINAL/terraform/free-tier/README.md](AFIRGEN FINAL/terraform/free-tier/README.md)
- **AWS Free Tier**: https://aws.amazon.com/free/

## Summary

Three commands to deploy:
```bash
make install-tools  # 2 minutes
make setup-aws      # 1 minute
make deploy-all     # 30-40 minutes
```

Total time: ~45 minutes (mostly automated)

Cost: $0 for 12 months

Automation: 95% (everything except AWS account setup)

Enjoy your AI-powered FIR generation system! 🎉
