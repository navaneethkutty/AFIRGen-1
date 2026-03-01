# AFIRGen AWS Bedrock Quick Start Guide

Deploy AFIRGen with Amazon Bedrock in 4 simple commands! 🚀

## What is Bedrock Architecture?

The Bedrock architecture replaces self-hosted GPU models with AWS managed services:
- **No GPU instances** → Use t3.small/medium ($0.02-0.04/hour vs $1.21/hour)
- **No model hosting** → Amazon Bedrock (Claude 3 Sonnet)
- **No maintenance** → AWS manages everything
- **Pay-per-use** → Only pay for what you use

## Prerequisites

1. ✅ AWS Account created
2. ✅ **Amazon Bedrock model access** (see below)
3. A computer with internet connection

### Request Bedrock Model Access (5 minutes)

**IMPORTANT**: Do this first!

1. Log in to [AWS Console](https://console.aws.amazon.com/)
2. Navigate to **Amazon Bedrock** service
3. Click **Model access** in left sidebar
4. Click **Request model access**
5. Select these models:
   - ✅ **Claude 3 Sonnet** (anthropic.claude-3-sonnet-20240229-v1:0)
   - ✅ **Titan Embeddings** (amazon.titan-embed-text-v1)
6. Click **Request model access**
7. Wait for approval (usually instant for Titan, 1-2 hours for Claude)

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
- Region: `us-east-1` (or `ap-south-1` for India)
- Output format: `json`

## Step 3: Deploy Bedrock Infrastructure (20 minutes)

```bash
make deploy-bedrock
```

This automatically:
1. ✅ Creates AWS infrastructure (VPC, EC2, RDS, S3)
2. ✅ Creates vector database (OpenSearch or Aurora pgvector)
3. ✅ Sets up VPC endpoints for Bedrock, Transcribe, Textract
4. ✅ Configures IAM roles with Bedrock permissions
5. ✅ Enables encryption with KMS
6. ✅ Sets up CloudWatch monitoring and X-Ray tracing

**Grab a coffee!** ☕ Infrastructure deployment takes about 20 minutes.

## Step 4: Migrate Data & Deploy App (25 minutes)

```bash
make migrate-data
```

This automatically:
1. ✅ Exports IPC sections from ChromaDB
2. ✅ Generates new embeddings with Titan Embeddings
3. ✅ Migrates to vector database (OpenSearch or Aurora)
4. ✅ Deploys FastAPI backend
5. ✅ Configures environment variables
6. ✅ Starts all services
7. ✅ Verifies deployment

**Total deployment time: ~45 minutes**

## What You Get

After deployment completes, you'll see:

```
==========================================
Bedrock Deployment Complete!
==========================================

Your AFIRGen instance is ready at:
  http://XX.XX.XX.XX:8000

Services:
  ✅ Amazon Bedrock (Claude 3 Sonnet)
  ✅ Amazon Transcribe (10 Indian languages)
  ✅ Amazon Textract (Document OCR)
  ✅ Vector Database (500 IPC sections)
  ✅ CloudWatch Monitoring
  ✅ X-Ray Tracing
```

Access your application:
- **API**: http://XX.XX.XX.XX:8000
- **API Docs**: http://XX.XX.XX.XX:8000/docs
- **Health Check**: http://XX.XX.XX.XX:8000/health

## Cost

**Pay-per-use pricing:**
- Optimized: $100-150/month (Aurora pgvector)
- Full features: $500+/month (OpenSearch Serverless)

**Cost breakdown:**
- EC2 t3.small: ~$15/month
- RDS MySQL: ~$12/month
- Vector DB: $50-350/month (Aurora vs OpenSearch)
- Bedrock: $0.003-0.015 per 1K tokens
- Transcribe: $0.024 per minute
- Textract: $0.0015 per page

See [COST-ESTIMATION.md](COST-ESTIMATION.md) for detailed calculations.

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

# Rollback to GGUF architecture
make rollback-to-gguf

# Destroy everything (cleanup)
make clean
```

## Testing Your Deployment

### Test Audio Transcription (Hindi)

```bash
curl -X POST http://XX.XX.XX.XX:8000/api/v1/fir/generate/audio \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio_file=@sample_audio.mp3" \
  -F "language_code=hi-IN" \
  -F "complainant_name=Test User" \
  -F "complainant_address=Test Address" \
  -F "complainant_phone=1234567890" \
  -F "station_name=Test Station" \
  -F "investigating_officer=Test Officer"
```

### Test Document OCR

```bash
curl -X POST http://XX.XX.XX.XX:8000/api/v1/fir/generate/image \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image_file=@sample_document.jpg" \
  -F "complainant_name=Test User" \
  -F "complainant_address=Test Address" \
  -F "complainant_phone=1234567890" \
  -F "station_name=Test Station" \
  -F "investigating_officer=Test Officer"
```

### Test Text-Based FIR Generation

```bash
curl -X POST http://XX.XX.XX.XX:8000/api/v1/fir/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "complaint_text": "My mobile phone was stolen yesterday at the market.",
    "complainant_name": "Test User",
    "complainant_address": "Test Address",
    "complainant_phone": "1234567890",
    "station_name": "Test Station",
    "investigating_officer": "Test Officer"
  }'
```

## Monitoring Your Deployment

### CloudWatch Metrics

```bash
# View in AWS Console
# CloudWatch → Dashboards → afirgen-bedrock-dashboard

# Metrics available:
# - Bedrock request count, latency, token usage
# - Transcribe request count, latency
# - Textract request count, latency
# - Vector database operations
# - Application errors
```

### X-Ray Traces

```bash
# View in AWS Console
# X-Ray → Traces

# See detailed request flow:
# - API → Bedrock → Vector DB → RDS
# - Latency breakdown by service
# - Error details with stack traces
```

### Cost Tracking

```bash
# View in AWS Console
# Cost Explorer → Cost & Usage

# Set up budget alerts:
# AWS Budgets → Create budget
# Set monthly limit (e.g., $200)
# Get email alerts at 80%, 100%
```

## Troubleshooting

### "Bedrock Access Denied"

**Solution:**
1. Go to AWS Console → Bedrock → Model access
2. Verify Claude 3 Sonnet and Titan Embeddings are "Access granted"
3. If not, request access and wait for approval

### "Vector Database Connection Failed"

**Solution:**
```bash
# Check security group
aws ec2 describe-security-groups --group-ids <VECTOR_DB_SG_ID>

# Verify VPC endpoint
aws ec2 describe-vpc-endpoints

# Check environment variables
ssh -i your-key.pem ubuntu@<EC2_IP>
cat /opt/afirgen/.env.bedrock | grep VECTOR_DB
```

### "High Costs"

**Solution:**
1. Switch to Aurora pgvector (saves ~$300/month)
2. Enable caching for frequent queries
3. Batch Transcribe requests
4. Use shorter prompts for Bedrock
5. Set up AWS Budgets for alerts

See [BEDROCK-TROUBLESHOOTING.md](BEDROCK-TROUBLESHOOTING.md) for more solutions.

## Cost Optimization Tips

### 1. Use Aurora pgvector Instead of OpenSearch

```bash
# Edit terraform.tfvars
vector_db_type = "aurora_pgvector"  # Instead of "opensearch"

# Redeploy
terraform apply
```

**Savings: ~$300/month**

### 2. Enable Caching

```bash
# In .env.bedrock
ENABLE_CACHING=true
CACHE_MAX_SIZE=100
```

**Savings: Reduces Bedrock API calls by 30-50%**

### 3. Use Reserved Instances (1-year commitment)

```bash
# AWS Console → EC2 → Reserved Instances
# Purchase 1-year RI for t3.small

# Savings: ~40% on EC2 costs
```

### 4. Optimize Bedrock Prompts

- Use shorter system prompts
- Cache frequent queries
- Batch similar requests
- Use lower temperature for deterministic outputs

**Savings: 20-30% on Bedrock costs**

## Rollback to GGUF Architecture

If you need to revert to GPU-based GGUF models:

```bash
# Automated rollback
make rollback-to-gguf

# This sets ENABLE_BEDROCK=false and restarts with GGUF models
```

See [FEATURE-FLAG-ROLLBACK.md](AFIRGEN FINAL/docs/FEATURE-FLAG-ROLLBACK.md) for details.

## What's Happening Behind the Scenes?

### `make deploy-bedrock` runs:

1. **Terraform Apply**: Creates AWS infrastructure
   - VPC with public/private subnets
   - EC2 t3.small/medium instance
   - RDS MySQL database
   - Vector database (OpenSearch or Aurora pgvector)
   - VPC endpoints (Bedrock, Transcribe, Textract, S3)
   - IAM roles with Bedrock permissions
   - KMS encryption keys
   - CloudWatch monitoring
   - X-Ray tracing

2. **Environment Setup**: Generates configuration
   - AWS region and endpoints
   - Bedrock model IDs
   - Vector database connection
   - Secure random keys
   - Feature flags

### `make migrate-data` runs:

1. **Export ChromaDB**: Exports IPC sections
2. **Generate Embeddings**: Uses Titan Embeddings
3. **Import to Vector DB**: Inserts into OpenSearch/Aurora
4. **Verify Migration**: Checks counts and similarity
5. **Deploy Application**: Starts FastAPI backend
6. **Health Checks**: Verifies all services

## Manual Deployment (If You Prefer)

If you want more control, follow the detailed guide:
- [AWS-DEPLOYMENT-PLAN.md](AWS-DEPLOYMENT-PLAN.md)

## Configuration Files

### Bedrock Configuration

See [BEDROCK-CONFIGURATION.md](BEDROCK-CONFIGURATION.md) for:
- All environment variables
- Vector database options
- Retry and circuit breaker settings
- Caching configuration
- Monitoring setup

### Migration Guide

See [MIGRATION-GUIDE.md](MIGRATION-GUIDE.md) for:
- Step-by-step migration from GGUF
- Data migration procedures
- Rollback procedures
- Testing checklist

## Next Steps

1. **Test the application**
   - Generate test FIRs
   - Try all 10 Indian languages
   - Test OCR functionality
   - Verify vector search

2. **Monitor costs**
   - Set up AWS Budgets
   - Review daily costs
   - Optimize as needed

3. **Configure domain (optional)**
   - Point domain to Elastic IP
   - Set up SSL with Let's Encrypt
   - Update CORS origins

4. **Optimize performance**
   - Review CloudWatch metrics
   - Adjust instance sizes
   - Tune vector database
   - Enable caching

## Support & Resources

**Documentation:**
- [Deployment Plan](AWS-DEPLOYMENT-PLAN.md)
- [Configuration Guide](BEDROCK-CONFIGURATION.md)
- [Troubleshooting Guide](BEDROCK-TROUBLESHOOTING.md)
- [Cost Estimation](COST-ESTIMATION.md)
- [Migration Guide](MIGRATION-GUIDE.md)
- [API Documentation](AFIRGEN FINAL/docs/API.md)

**AWS Resources:**
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [Amazon Transcribe](https://aws.amazon.com/transcribe/)
- [Amazon Textract](https://aws.amazon.com/textract/)
- [OpenSearch Serverless](https://aws.amazon.com/opensearch-service/features/serverless/)

## Summary

Four commands to deploy:
```bash
make install-tools      # 2 minutes
make setup-aws          # 1 minute
make deploy-bedrock     # 20 minutes
make migrate-data       # 25 minutes
```

**Total time:** ~45 minutes (mostly automated)

**Cost:** $100-150/month (optimized) or $500+/month (full features)

**Automation:** 95% (everything except AWS account setup and Bedrock access request)

**Key Benefits:**
- ✅ No GPU infrastructure ($1.21/hour → $0.02/hour)
- ✅ Pay only for what you use
- ✅ AWS managed services (no maintenance)
- ✅ Auto-scaling capabilities
- ✅ Easy rollback to GGUF if needed

Enjoy your AI-powered FIR generation system with Amazon Bedrock! 🎉
