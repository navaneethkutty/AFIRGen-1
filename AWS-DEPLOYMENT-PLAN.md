# AFIRGen AWS Bedrock Deployment Plan

## Executive Summary

This plan provides step-by-step instructions to deploy AFIRGen on AWS using Amazon Bedrock architecture. The deployment is **95% automated** using Terraform for infrastructure and automated scripts for data migration.

**Estimated Time**: 45-60 minutes for first-time deployment
**Monthly Cost**: Pay-per-use (estimated $50-150/month depending on usage)
**Automation Level**: 95% automated (everything except AWS account setup)

---

## Architecture Overview

### Bedrock Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ AWS Bedrock Architecture                                            │
│                                                                     │
│  Internet                                                           │
│     │                                                               │
│     ▼                                                               │
│  [Elastic IP] ──> [EC2 t3.small/medium - Public Subnet]           │
│                    │                                                │
│                    ├─ FastAPI Backend (Port 8000)                  │
│                    ├─ IPC Cache (In-Memory)                        │
│                    └─ X-Ray Daemon                                 │
│                    │                                                │
│                    ▼                                                │
│              [RDS MySQL - Private Subnet]                          │
│                    FIR Storage (20GB)                              │
│                    │                                                │
│                    ▼                                                │
│              [Vector Database - Private Subnet]                    │
│                    OpenSearch Serverless OR                        │
│                    Aurora PostgreSQL with pgvector                 │
│                                                                     │
│  [AWS Managed Services via VPC Endpoints]                          │
│     ├─ Amazon Bedrock (Claude 3 Sonnet)                           │
│     ├─ Amazon Bedrock (Titan Embeddings)                          │
│     ├─ Amazon Transcribe (10 Indian Languages)                    │
│     ├─ Amazon Textract (Document OCR)                             │
│     └─ Amazon S3 (Temporary File Storage)                         │
│                                                                     │
│  [Observability]                                                   │
│     ├─ CloudWatch (Metrics & Logs)                                │
│     └─ X-Ray (Distributed Tracing)                                │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Differences from GGUF Architecture

| Component | GGUF Architecture | Bedrock Architecture |
|-----------|-------------------|---------------------|
| **Compute** | g5.2xlarge GPU ($1.21/hour) | t3.small/medium ($0.02-0.04/hour) |
| **Transcription** | Self-hosted Whisper | Amazon Transcribe |
| **OCR** | Self-hosted Donut | Amazon Textract |
| **LLM** | Self-hosted GGUF models | Amazon Bedrock (Claude 3 Sonnet) |
| **Embeddings** | Self-hosted model | Amazon Bedrock (Titan Embeddings) |
| **Vector DB** | ChromaDB | OpenSearch Serverless or Aurora pgvector |
| **Cost Model** | Fixed hourly cost | Pay-per-use |
| **Maintenance** | Manual model updates | AWS managed |
| **Scalability** | Limited by instance | Auto-scaling |

---

## Prerequisites

### 1. AWS Account Setup
- [ ] Create AWS account at https://aws.amazon.com/
- [ ] Enable MFA for root account (security best practice)
- [ ] Create IAM user with admin access
- [ ] Save AWS Access Key ID and Secret Access Key
- [ ] **Request Bedrock model access** (see below)

### 2. Request Amazon Bedrock Model Access

**IMPORTANT**: You must request access to Bedrock models before deployment.

1. Log in to AWS Console
2. Navigate to Amazon Bedrock service
3. Go to "Model access" in the left sidebar
4. Request access to:
   - **Claude 3 Sonnet** (anthropic.claude-3-sonnet-20240229-v1:0)
   - **Titan Embeddings** (amazon.titan-embed-text-v1)
5. Wait for approval (usually instant for Titan, may take 1-2 hours for Claude)

### 3. Local Tools Installation

**Option A: Automated (Recommended)**
```bash
make install-tools
```

**Option B: Manual Installation**
```bash
# Terraform (Infrastructure as Code)
# macOS
brew install terraform

# Windows
choco install terraform

# AWS CLI
# macOS
brew install awscli

# Windows
choco install awscli
```

### 4. Configure AWS CLI

**Option A: Automated (Recommended)**
```bash
make setup-aws
```

**Option B: Manual**
```bash
aws configure
# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: us-east-1 (or ap-south-1 for India)
# - Default output format: json

# Verify configuration
aws sts get-caller-identity

# Verify Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

---

## 🚀 QUICK START (Fully Automated)

If you just want to deploy everything quickly:

```bash
# 1. Install tools and configure AWS
make install-tools
make setup-aws

# 2. Deploy Bedrock infrastructure
make deploy-bedrock

# 3. Migrate data to vector database
make migrate-data
```

That's it! The entire deployment is automated. Skip to the "Verify Deployment" section below.

---

## Phase 1: Infrastructure Provisioning (AUTOMATED)

### Step 1.1: Prepare Terraform Configuration

```bash
# Navigate to terraform directory
cd "AFIRGEN FINAL/terraform/free-tier"

# Create configuration file
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars
nano terraform.tfvars
```

**Required Configuration:**
```hcl
# Project Configuration
project_name = "afirgen"
environment  = "production"
aws_region   = "us-east-1"  # or "ap-south-1" for India

# Instance Configuration
instance_type = "t3.small"  # or "t3.medium" for better performance

# Vector Database Selection
vector_db_type = "opensearch"  # or "aurora_pgvector"

# Bedrock Configuration
bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
embeddings_model_id = "amazon.titan-embed-text-v1"

# Enable Bedrock Architecture
enable_bedrock = true
```

### Step 1.2: Initialize Terraform

```bash
# Initialize Terraform (downloads AWS provider)
terraform init

# Validate configuration
terraform validate

# Expected output: "Success! The configuration is valid."
```

### Step 1.3: Review Infrastructure Plan

```bash
# See what will be created
terraform plan

# Review the output - should show:
# - 1 VPC (10.0.0.0/16)
# - 3 Subnets (1 public, 2 private)
# - 1 Internet Gateway
# - Security Groups (EC2, RDS, Vector DB, VPC Endpoints)
# - 4 S3 Buckets
# - 1 EC2 t3.small/medium instance
# - 1 RDS MySQL instance
# - 1 Vector Database (OpenSearch or Aurora pgvector)
# - 4 VPC Endpoints (Bedrock, Transcribe, Textract, S3)
# - IAM roles and policies with Bedrock permissions
# - KMS key for encryption
# - 1 Elastic IP
```

### Step 1.4: Deploy Infrastructure

**Option A: Automated (Recommended)**
```bash
make deploy-infra
```

**Option B: Manual**
```bash
# Deploy all resources
terraform apply

# Review the plan and type 'yes' to confirm
# Deployment takes 15-20 minutes
```

### Step 1.5: Save Outputs

```bash
# Save all outputs to file
terraform output -json > deployment-outputs.json

# View specific outputs
terraform output ec2_public_ip
terraform output rds_endpoint
terraform output vector_db_endpoint
terraform output s3_bucket_names
```

**What Gets Created Automatically:**
- ✅ VPC with public and private subnets
- ✅ Security groups (EC2, RDS, Vector DB, VPC Endpoints)
- ✅ S3 buckets with SSE-KMS encryption
- ✅ EC2 instance (t3.small/medium) with Docker
- ✅ RDS MySQL database with encryption at rest
- ✅ Vector database (OpenSearch Serverless or Aurora pgvector)
- ✅ VPC endpoints for Bedrock, Transcribe, Textract, S3
- ✅ IAM roles with Bedrock, Transcribe, Textract permissions
- ✅ KMS key with automatic rotation
- ✅ CloudWatch monitoring and X-Ray tracing setup

---

## Phase 2: Application Deployment (SEMI-AUTOMATED)

### Step 2.1: Connect to EC2 Instance

```bash
# Get EC2 public IP
EC2_IP=$(terraform output -raw ec2_public_ip)

# SSH to instance (use your key pair)
ssh -i your-key.pem ubuntu@$EC2_IP

# Check user data script progress
tail -f /var/log/user-data.log

# Wait for setup to complete (5-10 minutes)
# Look for: "User data script completed successfully"
```

### Step 2.2: Configure Environment Variables (AUTOMATED)

**Option A: Automated (Recommended)**
```bash
make setup-bedrock-env
```

This automatically generates `.env.bedrock` with:
- ✅ AWS region and service endpoints
- ✅ Bedrock model IDs
- ✅ Vector database connection details
- ✅ S3 bucket names
- ✅ RDS connection string
- ✅ Secure random keys
- ✅ Feature flag (ENABLE_BEDROCK=true)

**Option B: Manual**
```bash
# SSH to EC2 instance
ssh -i your-key.pem ubuntu@$EC2_IP

# Navigate to application directory
cd /opt/afirgen

# Create .env.bedrock file
nano .env.bedrock
```

**Required Configuration:**
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_EMBEDDINGS_MODEL_ID=amazon.titan-embed-text-v1
ENABLE_BEDROCK=true

# Vector Database Configuration
VECTOR_DB_TYPE=opensearch  # or aurora_pgvector
VECTOR_DB_ENDPOINT=<VECTOR_DB_ENDPOINT>  # From Terraform output
VECTOR_DB_INDEX_NAME=ipc_sections

# OpenSearch Configuration (if using OpenSearch)
OPENSEARCH_REGION=us-east-1

# Aurora pgvector Configuration (if using Aurora)
PG_HOST=<AURORA_ENDPOINT>
PG_PORT=5432
PG_DATABASE=afirgen_vectors
PG_USER=admin
PG_PASSWORD=<SECURE_PASSWORD>

# S3 Configuration
S3_BUCKET_NAME=<TEMP_BUCKET_NAME>  # From Terraform output

# MySQL Database (RDS)
MYSQL_HOST=<RDS_ENDPOINT>  # From Terraform output
MYSQL_PORT=3306
MYSQL_USER=admin
MYSQL_PASSWORD=<YOUR_SECURE_PASSWORD>
MYSQL_DB=fir_db

# Application Configuration
PORT=8000
FIR_AUTH_KEY=<GENERATE_SECURE_KEY>  # Use: openssl rand -hex 32
API_KEY=<GENERATE_SECURE_KEY>

# Transcribe Configuration
TRANSCRIBE_LANGUAGES=hi-IN,en-IN,ta-IN,te-IN,bn-IN,mr-IN,gu-IN,kn-IN,ml-IN,pa-IN

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Retry Configuration
MAX_RETRIES=2
BASE_DELAY=1.0
MAX_DELAY=60.0

# Circuit Breaker Configuration
FAILURE_THRESHOLD=5
RECOVERY_TIMEOUT=60
HALF_OPEN_MAX_CALLS=3

# Caching Configuration
ENABLE_CACHING=true
CACHE_MAX_SIZE=100

# Monitoring Configuration
ENABLE_XRAY=true
CLOUDWATCH_NAMESPACE=AFIRGen/Bedrock

# Security
ENFORCE_HTTPS=false  # Set to true after SSL setup
SESSION_TIMEOUT=3600

# CORS Configuration
CORS_ORIGINS=http://<EC2_PUBLIC_IP>,https://<EC2_PUBLIC_IP>

# Frontend Configuration
API_BASE_URL=http://<EC2_PUBLIC_IP>:8000
ENVIRONMENT=production
ENABLE_DEBUG=false
```

### Step 2.3: Validate Environment Configuration

```bash
# SSH to EC2 instance
ssh -i your-key.pem ubuntu@$EC2_IP

# Run validation script
cd /opt/afirgen
python scripts/validate-env.py

# Expected output:
# ✅ All required environment variables present
# ✅ AWS credentials configured
# ✅ Bedrock access verified
# ✅ Vector database connection successful
# ✅ RDS connection successful
# ✅ S3 bucket accessible
```

---

## Phase 3: Data Migration (AUTOMATED)

### Step 3.1: Export IPC Sections from ChromaDB

**Option A: Automated (Recommended)**
```bash
make export-chromadb
```

**Option B: Manual**
```bash
# SSH to EC2 instance
ssh -i your-key.pem ubuntu@$EC2_IP

# Run export script
cd /opt/afirgen
python scripts/export_chromadb.py

# Verify export
ls -lh data/ipc_sections_export.json
```

### Step 3.2: Migrate to Vector Database

**Option A: Automated (Recommended)**
```bash
make migrate-vectors
```

This automatically:
- ✅ Reads exported IPC sections
- ✅ Generates new embeddings using Titan Embeddings
- ✅ Inserts into target vector database (OpenSearch or Aurora)
- ✅ Verifies embedding count matches source
- ✅ Performs sample similarity searches

**Option B: Manual**
```bash
# SSH to EC2 instance
ssh -i your-key.pem ubuntu@$EC2_IP

# Run migration script
cd /opt/afirgen
python scripts/migrate_vector_db.py

# Monitor progress
tail -f logs/migration.log

# Verify migration
python scripts/verify_migration.py
```

**Migration Output:**
```
Starting vector database migration...
✅ Loaded 500 IPC sections from export
✅ Generated embeddings for 500 sections (batch size: 25)
✅ Inserted 500 vectors into opensearch
✅ Verified: 500 vectors in source, 500 in target
✅ Sample similarity search successful
Migration completed in 12.5 minutes
```

---

## Phase 4: Application Deployment (AUTOMATED)

### Step 4.1: Deploy Application to EC2

**Option A: Automated (Recommended)**
```bash
make deploy-bedrock-app
```

This automatically:
- ✅ Copies application files to EC2
- ✅ Installs Python dependencies
- ✅ Starts FastAPI backend
- ✅ Configures X-Ray daemon
- ✅ Sets up CloudWatch agent
- ✅ Waits for services to be healthy

**Option B: Manual**
```bash
# SSH to EC2 instance
ssh -i your-key.pem ubuntu@$EC2_IP

# Navigate to application directory
cd /opt/afirgen

# Install dependencies
pip install -r requirements.txt

# Start application
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Or use systemd service
sudo systemctl start afirgen-backend
sudo systemctl enable afirgen-backend
```

### Step 4.2: Verify Deployment

**Option A: Automated (Recommended)**
```bash
make verify-bedrock
```

This automatically:
- ✅ Tests health endpoint
- ✅ Verifies Bedrock connectivity
- ✅ Tests Transcribe service
- ✅ Tests Textract service
- ✅ Tests vector database
- ✅ Displays access URLs

**Option B: Manual**
```bash
# Check health endpoint
curl http://<EC2_PUBLIC_IP>:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "bedrock": {"status": "connected", "model": "claude-3-sonnet"},
#   "transcribe": {"status": "available"},
#   "textract": {"status": "available"},
#   "vector_db": {"status": "connected", "type": "opensearch", "count": 500},
#   "database": "connected"
# }

# Access API documentation
# Open browser: http://<EC2_PUBLIC_IP>:8000/docs
```

---

## Phase 5: Testing (MANUAL)

### Step 5.1: Test Audio Transcription

```bash
# Upload sample audio file
curl -X POST http://<EC2_PUBLIC_IP>:8000/api/v1/fir/generate/audio \
  -H "Authorization: Bearer <TOKEN>" \
  -F "audio_file=@sample_audio.mp3" \
  -F "language_code=hi-IN" \
  -F "complainant_name=Test User" \
  -F "complainant_address=Test Address" \
  -F "complainant_phone=1234567890" \
  -F "station_name=Test Station" \
  -F "investigating_officer=Test Officer"

# Expected: FIR generated with transcript
```

### Step 5.2: Test Document OCR

```bash
# Upload sample image file
curl -X POST http://<EC2_PUBLIC_IP>:8000/api/v1/fir/generate/image \
  -H "Authorization: Bearer <TOKEN>" \
  -F "image_file=@sample_document.jpg" \
  -F "complainant_name=Test User" \
  -F "complainant_address=Test Address" \
  -F "complainant_phone=1234567890" \
  -F "station_name=Test Station" \
  -F "investigating_officer=Test Officer"

# Expected: FIR generated with extracted text
```

### Step 5.3: Test Text-Based FIR Generation

```bash
# Generate FIR from text
curl -X POST http://<EC2_PUBLIC_IP>:8000/api/v1/fir/generate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "complaint_text": "My mobile phone was stolen yesterday at the market.",
    "complainant_name": "Test User",
    "complainant_address": "Test Address",
    "complainant_phone": "1234567890",
    "station_name": "Test Station",
    "investigating_officer": "Test Officer"
  }'

# Expected: FIR generated with relevant IPC sections
```

---

## Phase 6: Monitoring & Observability (AUTOMATED)

### CloudWatch Monitoring (Already Configured)

**Automatic Monitoring:**
- ✅ EC2 CPU, memory, disk metrics
- ✅ RDS database metrics
- ✅ Bedrock request count, latency, token usage
- ✅ Transcribe request count, latency
- ✅ Textract request count, latency
- ✅ Vector database operation metrics
- ✅ Application logs
- ✅ Error tracking

**View Metrics:**
```bash
# AWS Console → CloudWatch → Dashboards
# Look for: afirgen-bedrock-dashboard

# Or use CLI
aws cloudwatch get-metric-statistics \
  --namespace AFIRGen/Bedrock \
  --metric-name BedrockRequestCount \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

### X-Ray Distributed Tracing

**View Traces:**
```bash
# AWS Console → X-Ray → Traces
# Filter by: Service name = afirgen-backend

# View service map
# AWS Console → X-Ray → Service map
```

**Trace Details Include:**
- Request flow through all AWS services
- Latency breakdown by service
- Error details with stack traces
- Correlation IDs for debugging

---

## Cost Breakdown (Pay-Per-Use)

### Monthly Cost Estimation (Moderate Usage)

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| EC2 t3.small | 730 hours | $0.0208/hour | $15.18 |
| RDS db.t3.micro | 730 hours | $0.017/hour | $12.41 |
| EBS Storage | 50 GB | $0.10/GB | $5.00 |
| OpenSearch Serverless | 2 OCU | $0.24/OCU-hour | $350.40 |
| Bedrock Claude 3 Sonnet | 1M input tokens | $0.003/1K | $3.00 |
| Bedrock Claude 3 Sonnet | 500K output tokens | $0.015/1K | $7.50 |
| Bedrock Titan Embeddings | 1M tokens | $0.0001/1K | $0.10 |
| Transcribe | 100 hours | $0.024/min | $144.00 |
| Textract | 1000 pages | $0.0015/page | $1.50 |
| S3 Storage | 10 GB | $0.023/GB | $0.23 |
| Data Transfer | 50 GB out | $0.09/GB | $4.50 |
| CloudWatch | Standard | Included | $0.00 |
| **Total** | | | **~$543.82/month** |

### Cost Optimization Options

1. **Use Aurora pgvector instead of OpenSearch** (~$350/month savings)
   - Aurora Serverless v2: ~$50/month
   - Total with Aurora: ~$193/month

2. **Reduce Transcribe usage**
   - Cache transcripts
   - Use shorter audio clips
   - Batch processing

3. **Optimize Bedrock usage**
   - Cache frequent queries
   - Use shorter prompts
   - Implement request batching

4. **Use Reserved Instances** (1-year commitment)
   - EC2 savings: ~40%
   - RDS savings: ~35%

**Recommended Configuration for Cost Optimization:**
- Vector DB: Aurora pgvector
- EC2: t3.small with 1-year RI
- RDS: db.t3.micro with 1-year RI
- **Estimated cost: $100-150/month**

See [COST-ESTIMATION.md](COST-ESTIMATION.md) for detailed cost breakdowns, optimization strategies, and monthly estimates for different usage scenarios.

---

## Rollback to GGUF Architecture

If you need to revert to the GGUF architecture:

```bash
# Option A: Automated
make rollback-to-gguf

# Option B: Manual
ssh -i your-key.pem ubuntu@$EC2_IP
cd /opt/afirgen
./scripts/rollback-to-gguf.sh
```

This sets `ENABLE_BEDROCK=false` and restarts with GGUF models.

See [FEATURE-FLAG-ROLLBACK.md](AFIRGEN FINAL/docs/FEATURE-FLAG-ROLLBACK.md) for details.

---

## Troubleshooting

See [BEDROCK-TROUBLESHOOTING.md](BEDROCK-TROUBLESHOOTING.md) for comprehensive troubleshooting guide.

### Quick Fixes

**Issue: Bedrock Access Denied**
```bash
# Verify model access in AWS Console
# Bedrock → Model access → Request access to Claude 3 Sonnet

# Check IAM permissions
aws iam get-role-policy --role-name afirgen-ec2-role --policy-name BedrockAccess
```

**Issue: Vector Database Connection Failed**
```bash
# Check security group allows EC2 to Vector DB
# Check VPC endpoint connectivity
# Verify credentials in .env.bedrock
```

**Issue: High Costs**
```bash
# Check CloudWatch metrics for usage
# Review cost optimization options above
# Consider switching to Aurora pgvector
```

---

## Maintenance Tasks

### Daily (Automated)
- ✅ Database backups to S3
- ✅ Log rotation
- ✅ Health checks
- ✅ Cost tracking

### Weekly (Manual)
- [ ] Review CloudWatch metrics
- [ ] Check Bedrock token usage
- [ ] Review cost reports
- [ ] Check vector database performance

### Monthly (Manual)
- [ ] Update application dependencies
- [ ] Review security groups
- [ ] Optimize costs
- [ ] Review X-Ray traces for bottlenecks

---

## Cleanup / Teardown

### To Remove Everything:

```bash
# Navigate to terraform directory
cd "AFIRGEN FINAL/terraform/free-tier"

# Destroy all resources
terraform destroy

# Type 'yes' to confirm
```

**Warning:** This will permanently delete all resources and data.

---

## Next Steps After Deployment

1. **Configure Domain (Optional)**
   - Point domain to Elastic IP
   - Set up SSL with Let's Encrypt
   - Update CORS origins

2. **Set Up Cost Alerts**
   - Configure AWS Budgets
   - Set spending alerts
   - Monitor daily costs

3. **Optimize Performance**
   - Review CloudWatch metrics
   - Adjust instance sizes
   - Tune vector database

4. **Security Hardening**
   - Enable AWS Secrets Manager
   - Configure WAF
   - Regular security audits

---

## Support & Resources

**Documentation:**
- [Bedrock Configuration Guide](BEDROCK-CONFIGURATION.md)
- [Bedrock Troubleshooting Guide](BEDROCK-TROUBLESHOOTING.md)
- [Cost Estimation Guide](COST-ESTIMATION.md)
- [Migration Guide](MIGRATION-GUIDE.md)
- [API Documentation](AFIRGEN FINAL/docs/API.md)

**AWS Resources:**
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Amazon Transcribe Documentation](https://docs.aws.amazon.com/transcribe/)
- [Amazon Textract Documentation](https://docs.aws.amazon.com/textract/)
- [OpenSearch Serverless Documentation](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html)

---

## Summary

**Deployment Time:** 45-60 minutes
**Automation Level:** 95%
**Monthly Cost:** $100-150 (optimized) to $500+ (full features)
**Scalability:** Auto-scaling with AWS managed services
**Maintenance:** Minimal (AWS managed)

**Key Benefits:**
- ✅ No GPU infrastructure management
- ✅ Pay only for what you use
- ✅ Auto-scaling capabilities
- ✅ AWS managed service reliability
- ✅ Easy rollback to GGUF if needed
