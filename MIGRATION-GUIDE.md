# AFIRGen Migration Guide: GGUF to Bedrock Architecture

## Executive Summary

This guide provides a complete roadmap for migrating the AFIRGen (Automated FIR Generation) system from self-hosted GGUF models on GPU instances to AWS managed services using Amazon Bedrock architecture.

**Migration Overview:**
- **From**: g5.2xlarge GPU instance ($1.21/hour = ~$870/month) with self-hosted models
- **To**: t3.small/medium instance ($0.02-0.04/hour = ~$15-30/month) with AWS managed services
- **Cost Savings**: ~85-95% reduction in infrastructure costs
- **Timeline**: 2-3 days for complete migration
- **Downtime**: Zero (feature flag enables instant rollback)

**Key Changes:**
- Audio Transcription: Self-hosted Whisper → Amazon Transcribe
- Document OCR: Self-hosted Donut → Amazon Textract
- LLM Processing: Self-hosted GGUF models → Amazon Bedrock (Claude 3 Sonnet)
- Embeddings: Self-hosted model → Amazon Bedrock (Titan Embeddings)
- Vector Database: ChromaDB → OpenSearch Serverless or Aurora pgvector
- Compute: g5.2xlarge GPU → t3.small/medium CPU

**Migration Benefits:**
- ✅ 85-95% cost reduction
- ✅ Zero model maintenance
- ✅ Auto-scaling capabilities
- ✅ AWS managed service reliability
- ✅ Instant rollback capability
- ✅ Improved observability with CloudWatch and X-Ray

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Migration Checklist](#pre-migration-checklist)
3. [Phase 1: Infrastructure Preparation](#phase-1-infrastructure-preparation)
4. [Phase 2: Data Migration](#phase-2-data-migration)
5. [Phase 3: Application Deployment](#phase-3-application-deployment)
6. [Phase 4: Testing and Validation](#phase-4-testing-and-validation)
7. [Phase 5: Production Cutover](#phase-5-production-cutover)
8. [Rollback Procedures](#rollback-procedures)
9. [Troubleshooting](#troubleshooting)
10. [Post-Migration Tasks](#post-migration-tasks)
11. [Cost Monitoring](#cost-monitoring)

---

## Prerequisites

### 1. AWS Account Requirements

**Required:**
- [ ] AWS account with admin access
- [ ] MFA enabled for root account
- [ ] IAM user with programmatic access
- [ ] AWS CLI configured with credentials
- [ ] **Amazon Bedrock model access granted** (see below)

**Request Bedrock Model Access (CRITICAL):**

You MUST request access to Bedrock models before starting migration:

1. Log in to AWS Console
2. Navigate to **Amazon Bedrock** service
3. Go to **Model access** in left sidebar
4. Click **Request model access**
5. Select these models:
   - ✅ **Claude 3 Sonnet** (anthropic.claude-3-sonnet-20240229-v1:0)
   - ✅ **Titan Embeddings** (amazon.titan-embed-text-v1)
6. Click **Request model access**
7. Wait for approval (usually instant for Titan, 1-2 hours for Claude)

**Verify Access:**
```bash
aws bedrock list-foundation-models --region us-east-1 | grep -E "claude-3-sonnet|titan-embed"
```

### 2. Local Tools Installation


**Required Tools:**
- Terraform >= 1.0
- AWS CLI >= 2.0
- Python >= 3.9
- Git

**Installation:**
```bash
# Automated installation
make install-tools

# Or manual installation
# macOS
brew install terraform awscli python@3.9

# Windows
choco install terraform awscli python

# Linux (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y terraform awscli python3.9
```

### 3. Current System Backup

**CRITICAL: Backup before migration!**

```bash
# 1. Backup ChromaDB data
cd "AFIRGEN FINAL"
python scripts/export_chromadb.py
# Creates: data/ipc_sections_export.json

# 2. Backup MySQL database
mysqldump -h <RDS_ENDPOINT> -u admin -p fir_db > fir_db_backup.sql

# 3. Backup configuration files
cp .env .env.backup
cp -r config config.backup

# 4. Verify backups
ls -lh data/ipc_sections_export.json
ls -lh fir_db_backup.sql
```

### 4. Network and Access Requirements

- [ ] VPN/network access to current infrastructure
- [ ] SSH key for EC2 instances
- [ ] Database credentials for MySQL RDS
- [ ] S3 bucket access
- [ ] Ability to modify security groups

---

## Pre-Migration Checklist


Complete this checklist before starting migration:

### Infrastructure Readiness
- [ ] AWS account created and configured
- [ ] Bedrock model access granted (Claude 3 Sonnet, Titan Embeddings)
- [ ] AWS CLI configured with correct region
- [ ] Terraform installed and initialized
- [ ] Current system backed up (ChromaDB, MySQL, configs)

### Documentation Review
- [ ] Read [AWS-DEPLOYMENT-PLAN.md](AWS-DEPLOYMENT-PLAN.md)
- [ ] Read [BEDROCK-CONFIGURATION.md](BEDROCK-CONFIGURATION.md)
- [ ] Read [BEDROCK-TROUBLESHOOTING.md](BEDROCK-TROUBLESHOOTING.md)
- [ ] Review [FEATURE-FLAG-ROLLBACK.md](AFIRGEN FINAL/docs/FEATURE-FLAG-ROLLBACK.md)

### Team Coordination
- [ ] Migration window scheduled (recommend off-peak hours)
- [ ] Stakeholders notified
- [ ] Rollback plan reviewed with team
- [ ] On-call engineer assigned

### Testing Environment
- [ ] Staging environment available for testing
- [ ] Test data prepared (sample audio, images, text)
- [ ] Test user accounts created

---

## Phase 1: Infrastructure Preparation

**Estimated Time:** 30-45 minutes  
**Downtime:** None (parallel infrastructure)

### Step 1.1: Configure Terraform Variables

```bash
cd "AFIRGEN FINAL/terraform/free-tier"

# Create terraform.tfvars from example
cp terraform.tfvars.example terraform.tfvars

# Edit configuration
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
vector_db_type = "opensearch"  # or "aurora_pgvector" for cost savings

# Bedrock Configuration
bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
embeddings_model_id = "amazon.titan-embed-text-v1"

# Enable Bedrock Architecture
enable_bedrock = true
```

**Vector Database Decision:**

| Option | Cost | Performance | Recommendation |
|--------|------|-------------|----------------|
| OpenSearch Serverless | ~$350/month | Excellent | Production, high-volume |
| Aurora pgvector | ~$50/month | Good | Development, cost-sensitive |


### Step 1.2: Initialize Terraform

```bash
# Initialize Terraform
terraform init

# Validate configuration
terraform validate
# Expected: "Success! The configuration is valid."

# Review planned changes
terraform plan -out=tfplan

# Review output carefully - should show:
# - EC2 instance type change (g5.2xlarge → t3.small/medium)
# - New IAM policies for Bedrock, Transcribe, Textract
# - New VPC endpoints
# - New vector database (OpenSearch or Aurora pgvector)
# - Security group updates
```

### Step 1.3: Deploy New Infrastructure

**Option A: Automated (Recommended)**
```bash
make deploy-bedrock-infra
```

**Option B: Manual**
```bash
# Apply Terraform changes
terraform apply tfplan

# Deployment takes 15-20 minutes
# Monitor progress in AWS Console
```

**What Gets Created:**
- ✅ New EC2 t3.small/medium instance
- ✅ IAM roles with Bedrock, Transcribe, Textract permissions
- ✅ VPC endpoints for AWS services
- ✅ Vector database (OpenSearch Serverless or Aurora pgvector)
- ✅ Security groups with updated rules
- ✅ KMS keys for encryption
- ✅ CloudWatch log groups
- ✅ X-Ray configuration

### Step 1.4: Save Infrastructure Outputs

```bash
# Save all outputs
terraform output -json > deployment-outputs.json

# View key outputs
terraform output ec2_public_ip
terraform output rds_endpoint
terraform output vector_db_endpoint
terraform output s3_bucket_names

# Save to environment variables
export NEW_EC2_IP=$(terraform output -raw ec2_public_ip)
export VECTOR_DB_ENDPOINT=$(terraform output -raw vector_db_endpoint)
export S3_BUCKET=$(terraform output -raw s3_bucket_temp_files)
```

### Step 1.5: Verify Infrastructure

```bash
# Check EC2 instance is running
aws ec2 describe-instances --instance-ids <INSTANCE_ID> --query 'Reservations[0].Instances[0].State.Name'
# Expected: "running"

# Check IAM role permissions
aws iam get-role-policy --role-name afirgen-ec2-role --policy-name BedrockAccess

# Check VPC endpoints
aws ec2 describe-vpc-endpoints --filters "Name=tag:Project,Values=afirgen"

# Check vector database
# For OpenSearch:
aws opensearchserverless list-collections

# For Aurora pgvector:
aws rds describe-db-clusters --db-cluster-identifier afirgen-vectors
```

**Estimated Time for Phase 1:** 30-45 minutes

---

## Phase 2: Data Migration

**Estimated Time:** 20-30 minutes  
**Downtime:** None (read-only operation)


### Step 2.1: Export IPC Sections from ChromaDB

**Option A: Automated (Recommended)**
```bash
make export-chromadb
```

**Option B: Manual**
```bash
# SSH to current GGUF instance
ssh -i your-key.pem ubuntu@<CURRENT_EC2_IP>

# Navigate to application directory
cd /opt/afirgen

# Run export script
python scripts/export_chromadb.py

# Verify export
ls -lh data/ipc_sections_export.json
# Should show file with ~500 IPC sections

# Download to local machine
exit
scp -i your-key.pem ubuntu@<CURRENT_EC2_IP>:/opt/afirgen/data/ipc_sections_export.json ./
```

**Export Format:**
```json
[
  {
    "ipc_section": "IPC 420",
    "description": "Cheating and dishonestly inducing delivery of property",
    "penalty": "Imprisonment up to 7 years and fine",
    "embedding": [0.123, -0.456, ...]  // Optional, will regenerate
  }
]
```

### Step 2.2: Configure Environment Variables

**Option A: Automated (Recommended)**
```bash
make setup-bedrock-env
```

This automatically generates `.env.bedrock` with all required variables.

**Option B: Manual**
```bash
# SSH to new Bedrock instance
ssh -i your-key.pem ubuntu@$NEW_EC2_IP

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
VECTOR_DB_ENDPOINT=<VECTOR_DB_ENDPOINT>
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
S3_BUCKET_NAME=<S3_BUCKET>

# MySQL Database (RDS) - Use existing endpoint
MYSQL_HOST=<RDS_ENDPOINT>
MYSQL_PORT=3306
MYSQL_USER=admin
MYSQL_PASSWORD=<YOUR_PASSWORD>
MYSQL_DB=fir_db

# Application Configuration
PORT=8000
FIR_AUTH_KEY=<GENERATE_SECURE_KEY>
API_KEY=<GENERATE_SECURE_KEY>

# Transcribe Configuration
TRANSCRIBE_LANGUAGES=hi-IN,en-IN,ta-IN,te-IN,bn-IN,mr-IN,gu-IN,kn-IN,ml-IN,pa-IN

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

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

**Generate Secure Keys:**
```bash
# Generate FIR_AUTH_KEY
openssl rand -hex 32

# Generate API_KEY
openssl rand -hex 32
```


### Step 2.3: Validate Environment Configuration

```bash
# SSH to new Bedrock instance
ssh -i your-key.pem ubuntu@$NEW_EC2_IP

# Run validation script
cd /opt/afirgen
python scripts/validate-env.py

# Expected output:
# ✅ All required environment variables present
# ✅ AWS credentials configured
# ✅ Bedrock access verified (Claude 3 Sonnet, Titan Embeddings)
# ✅ Vector database connection successful
# ✅ RDS connection successful
# ✅ S3 bucket accessible
# ✅ Configuration valid
```

**If validation fails:**
- Check AWS credentials: `aws sts get-caller-identity`
- Check Bedrock access: `aws bedrock list-foundation-models --region us-east-1`
- Check security groups allow EC2 → Vector DB, RDS
- Review [BEDROCK-TROUBLESHOOTING.md](BEDROCK-TROUBLESHOOTING.md)

### Step 2.4: Migrate IPC Sections to Vector Database

**Option A: Automated (Recommended)**
```bash
make migrate-vectors
```

**Option B: Manual**
```bash
# SSH to new Bedrock instance
ssh -i your-key.pem ubuntu@$NEW_EC2_IP

# Upload exported data
scp -i your-key.pem ipc_sections_export.json ubuntu@$NEW_EC2_IP:/opt/afirgen/data/

# Run migration script
cd /opt/afirgen
python scripts/migrate_vector_db.py

# Monitor progress
tail -f logs/migration.log
```

**Migration Process:**
1. Reads exported IPC sections from JSON
2. Generates new embeddings using Titan Embeddings (1536 dimensions)
3. Inserts embeddings and metadata into vector database
4. Processes in batches of 25 for optimization
5. Verifies embedding count matches source
6. Performs sample similarity searches

**Expected Output:**
```
Starting vector database migration...
✅ Loaded 500 IPC sections from export
✅ Generated embeddings for 500 sections (batch size: 25)
✅ Inserted 500 vectors into opensearch
✅ Verified: 500 vectors in source, 500 in target
✅ Sample similarity search successful
   Query: "theft of mobile phone"
   Top result: IPC 379 (Theft) - similarity: 0.89
Migration completed in 12.5 minutes
```

### Step 2.5: Verify Data Migration

```bash
# Check vector count
python scripts/verify_migration.py

# Expected output:
# ✅ Vector database contains 500 IPC sections
# ✅ All sections have 1536-dimensional embeddings
# ✅ Sample searches return relevant results

# Test similarity search
python -c "
from services.vector_db.factory import VectorDBFactory
from services.aws.titan_embeddings_client import TitanEmbeddingsClient
import asyncio

async def test():
    embeddings = TitanEmbeddingsClient('us-east-1')
    vector_db = VectorDBFactory.create()
    await vector_db.connect()
    
    query = 'theft of mobile phone'
    embedding = await embeddings.generate_embedding(query)
    results = await vector_db.similarity_search(embedding, top_k=5)
    
    print('Top 5 relevant IPC sections:')
    for r in results:
        print(f'  {r.ipc_section}: {r.description} (similarity: {r.score:.2f})')

asyncio.run(test())
"
```

**Estimated Time for Phase 2:** 20-30 minutes

---

## Phase 3: Application Deployment

**Estimated Time:** 15-20 minutes  
**Downtime:** None (parallel deployment)


### Step 3.1: Deploy Application Code

**Option A: Automated (Recommended)**
```bash
make deploy-bedrock-app
```

**Option B: Manual**
```bash
# SSH to new Bedrock instance
ssh -i your-key.pem ubuntu@$NEW_EC2_IP

# Navigate to application directory
cd /opt/afirgen

# Pull latest code (if using Git)
git pull origin main

# Install dependencies
pip install -r requirements.txt

# Install additional Bedrock dependencies
pip install boto3 botocore opensearch-py asyncpg pgvector

# Verify installation
python -c "import boto3; print('boto3:', boto3.__version__)"
python -c "from opensearchpy import OpenSearch; print('OpenSearch client installed')"
```

### Step 3.2: Start Application Services

**Using systemd (Recommended):**
```bash
# Create systemd service file
sudo nano /etc/systemd/system/afirgen-backend.service
```

**Service Configuration:**
```ini
[Unit]
Description=AFIRGen Backend Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/afirgen
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/opt/afirgen/.env.bedrock
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Start Service:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable afirgen-backend

# Start service
sudo systemctl start afirgen-backend

# Check status
sudo systemctl status afirgen-backend

# View logs
sudo journalctl -u afirgen-backend -f
```

**Manual Start (Alternative):**
```bash
# Start application
cd /opt/afirgen
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 &

# Check process
ps aux | grep uvicorn
```

### Step 3.3: Verify Application Health

```bash
# Check health endpoint
curl http://$NEW_EC2_IP:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "implementation": "bedrock",
#   "enable_bedrock": true,
#   "bedrock": {
#     "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
#     "embeddings_model_id": "amazon.titan-embed-text-v1",
#     "vector_db_type": "opensearch",
#     "services_initialized": true
#   },
#   "transcribe": {"status": "available", "languages": 10},
#   "textract": {"status": "available"},
#   "vector_db": {"status": "connected", "count": 500},
#   "database": "connected"
# }
```

**If health check fails:**
- Check application logs: `sudo journalctl -u afirgen-backend -n 50`
- Check environment variables: `cat /opt/afirgen/.env.bedrock`
- Check AWS service connectivity: `python scripts/validate-env.py`
- Review [BEDROCK-TROUBLESHOOTING.md](BEDROCK-TROUBLESHOOTING.md)

### Step 3.4: Configure X-Ray Daemon

```bash
# Install X-Ray daemon
wget https://s3.us-east-2.amazonaws.com/aws-xray-assets.us-east-2/xray-daemon/aws-xray-daemon-3.x.deb
sudo dpkg -i aws-xray-daemon-3.x.deb

# Start X-Ray daemon
sudo systemctl start xray
sudo systemctl enable xray

# Verify X-Ray is running
sudo systemctl status xray
```

### Step 3.5: Configure CloudWatch Agent (Optional)

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard

# Start agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json
```

**Estimated Time for Phase 3:** 15-20 minutes

---

## Phase 4: Testing and Validation

**Estimated Time:** 30-45 minutes  
**Downtime:** None (testing only)


### Step 4.1: Test Audio Transcription

**Test Hindi Audio:**
```bash
curl -X POST http://$NEW_EC2_IP:8000/api/v1/fir/generate/audio \
  -H "Authorization: Bearer <TOKEN>" \
  -F "audio_file=@test_audio_hindi.mp3" \
  -F "language_code=hi-IN" \
  -F "complainant_name=Test User" \
  -F "complainant_address=Test Address" \
  -F "complainant_phone=1234567890" \
  -F "station_name=Test Station" \
  -F "investigating_officer=Test Officer"

# Expected: FIR generated with Hindi transcript
```

**Test Multiple Languages:**
```bash
# Test all 10 supported languages
for lang in hi-IN en-IN ta-IN te-IN bn-IN mr-IN gu-IN kn-IN ml-IN pa-IN; do
  echo "Testing language: $lang"
  curl -X POST http://$NEW_EC2_IP:8000/api/v1/fir/generate/audio \
    -H "Authorization: Bearer <TOKEN>" \
    -F "audio_file=@test_audio_${lang}.mp3" \
    -F "language_code=$lang" \
    -F "complainant_name=Test User" \
    -F "complainant_address=Test Address" \
    -F "complainant_phone=1234567890" \
    -F "station_name=Test Station" \
    -F "investigating_officer=Test Officer"
done
```

**Verify:**
- ✅ Transcription completes within 3 minutes for 5-minute audio
- ✅ Transcript text is accurate
- ✅ FIR generated with correct IPC sections
- ✅ No errors in logs

### Step 4.2: Test Document OCR

**Test Image Upload:**
```bash
curl -X POST http://$NEW_EC2_IP:8000/api/v1/fir/generate/image \
  -H "Authorization: Bearer <TOKEN>" \
  -F "image_file=@test_document.jpg" \
  -F "complainant_name=Test User" \
  -F "complainant_address=Test Address" \
  -F "complainant_phone=1234567890" \
  -F "station_name=Test Station" \
  -F "investigating_officer=Test Officer"

# Expected: FIR generated with extracted text
```

**Verify:**
- ✅ OCR completes within 30 seconds
- ✅ Extracted text is accurate
- ✅ FIR generated with correct IPC sections
- ✅ No errors in logs

### Step 4.3: Test Text-Based FIR Generation

**Test Simple Complaint:**
```bash
curl -X POST http://$NEW_EC2_IP:8000/api/v1/fir/generate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "complaint_text": "My mobile phone was stolen yesterday at the market. The accused snatched it from my hand and ran away.",
    "complainant_name": "Test User",
    "complainant_address": "123 Test Street, Test City",
    "complainant_phone": "9876543210",
    "station_name": "Test Police Station",
    "investigating_officer": "Inspector Test"
  }'

# Expected: FIR with IPC 379 (Theft) and IPC 356 (Assault)
```

**Test Complex Complaint:**
```bash
curl -X POST http://$NEW_EC2_IP:8000/api/v1/fir/generate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "complaint_text": "I was cheated by a person who promised to deliver goods but took my money and disappeared. He also threatened me when I asked for a refund.",
    "complainant_name": "Test User",
    "complainant_address": "456 Test Avenue, Test City",
    "complainant_phone": "9876543210",
    "station_name": "Test Police Station",
    "investigating_officer": "Inspector Test"
  }'

# Expected: FIR with IPC 420 (Cheating), IPC 406 (Criminal breach of trust), IPC 506 (Criminal intimidation)
```

**Verify:**
- ✅ FIR generation completes within 10 seconds
- ✅ Relevant IPC sections identified correctly
- ✅ Legal narrative is formal and concise (max 3 sentences)
- ✅ All required FIR fields populated
- ✅ No errors in logs

### Step 4.4: Test Vector Search Accuracy

```bash
# Test vector search directly
python -c "
from services.vector_db.factory import VectorDBFactory
from services.aws.titan_embeddings_client import TitanEmbeddingsClient
import asyncio

async def test_searches():
    embeddings = TitanEmbeddingsClient('us-east-1')
    vector_db = VectorDBFactory.create()
    await vector_db.connect()
    
    test_queries = [
        'theft of mobile phone',
        'cheating and fraud',
        'assault and battery',
        'criminal intimidation',
        'murder'
    ]
    
    for query in test_queries:
        print(f'\nQuery: {query}')
        embedding = await embeddings.generate_embedding(query)
        results = await vector_db.similarity_search(embedding, top_k=3)
        
        for i, r in enumerate(results, 1):
            print(f'  {i}. {r.ipc_section}: {r.description} (similarity: {r.score:.2f})')

asyncio.run(test_searches())
"
```

**Verify:**
- ✅ Search returns relevant IPC sections
- ✅ Similarity scores are reasonable (>0.7 for top result)
- ✅ Search completes within 2 seconds
- ✅ No errors in logs


### Step 4.5: Performance Testing

**Test Concurrent Requests:**
```bash
# Install Apache Bench (if not installed)
sudo apt-get install apache2-utils

# Test 10 concurrent requests
ab -n 10 -c 10 -p test_request.json -T application/json \
  -H "Authorization: Bearer <TOKEN>" \
  http://$NEW_EC2_IP:8000/api/v1/fir/generate

# Review results
# - Time per request (mean)
# - Requests per second
# - Failed requests (should be 0)
```

**Verify:**
- ✅ System handles 10 concurrent requests without errors
- ✅ Average latency remains acceptable
- ✅ No timeout errors
- ✅ 99% success rate maintained

### Step 4.6: Integration Test Suite

```bash
# Run integration tests
cd /opt/afirgen
pytest tests/integration/ -v

# Expected tests:
# ✅ test_transcribe_integration.py
# ✅ test_textract_integration.py
# ✅ test_bedrock_integration.py
# ✅ test_vector_db_integration.py
# ✅ test_fir_generation_integration.py
# ✅ test_feature_flag_rollback.py
```

### Step 4.7: Monitoring Verification

**Check CloudWatch Metrics:**
```bash
# View metrics in AWS Console
# CloudWatch → Dashboards → afirgen-bedrock-dashboard

# Or use CLI
aws cloudwatch get-metric-statistics \
  --namespace AFIRGen/Bedrock \
  --metric-name BedrockRequestCount \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

**Check X-Ray Traces:**
```bash
# View traces in AWS Console
# X-Ray → Traces → Filter by: Service name = afirgen-backend

# Verify traces show:
# - Complete request flow
# - Latency breakdown by service
# - No errors
```

**Check Application Logs:**
```bash
# View CloudWatch Logs
aws logs tail /aws/ec2/afirgen-backend --follow

# Or view locally
sudo journalctl -u afirgen-backend -f
```

**Verify:**
- ✅ Metrics being emitted to CloudWatch
- ✅ X-Ray traces being created
- ✅ Logs in structured JSON format
- ✅ No PII in logs
- ✅ Correlation IDs present

**Estimated Time for Phase 4:** 30-45 minutes

---

## Phase 5: Production Cutover

**Estimated Time:** 10-15 minutes  
**Downtime:** <5 minutes (DNS/load balancer update)

### Step 5.1: Final Pre-Cutover Checklist

- [ ] All Phase 4 tests passed successfully
- [ ] Monitoring and alerting configured
- [ ] Rollback procedure reviewed and ready
- [ ] Team on standby for cutover
- [ ] Stakeholders notified of cutover window

### Step 5.2: Update DNS or Load Balancer

**Option A: DNS Update**
```bash
# Update DNS A record to point to new EC2 IP
# Example using Route 53:
aws route53 change-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "afirgen.yourdomain.com",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "'$NEW_EC2_IP'"}]
      }
    }]
  }'

# Wait for DNS propagation (5-10 minutes)
# Check propagation:
dig afirgen.yourdomain.com
```

**Option B: Load Balancer Update**
```bash
# Register new instance with load balancer
aws elbv2 register-targets \
  --target-group-arn <TARGET_GROUP_ARN> \
  --targets Id=<NEW_INSTANCE_ID>

# Wait for health checks to pass
aws elbv2 describe-target-health \
  --target-group-arn <TARGET_GROUP_ARN>

# Deregister old instance
aws elbv2 deregister-targets \
  --target-group-arn <TARGET_GROUP_ARN> \
  --targets Id=<OLD_INSTANCE_ID>
```

### Step 5.3: Monitor Production Traffic

```bash
# Monitor application logs
sudo journalctl -u afirgen-backend -f

# Monitor CloudWatch metrics
watch -n 5 'aws cloudwatch get-metric-statistics \
  --namespace AFIRGen/Bedrock \
  --metric-name FIRGenerationCount \
  --start-time $(date -u -d "5 minutes ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum'

# Monitor error rate
watch -n 5 'aws cloudwatch get-metric-statistics \
  --namespace AFIRGen/Bedrock \
  --metric-name ErrorCount \
  --start-time $(date -u -d "5 minutes ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Sum'
```

### Step 5.4: Verify Production Functionality

```bash
# Test production endpoint
curl https://afirgen.yourdomain.com/health

# Test FIR generation
curl -X POST https://afirgen.yourdomain.com/api/v1/fir/generate \
  -H "Authorization: Bearer <PROD_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "complaint_text": "Production test complaint",
    "complainant_name": "Test User",
    "complainant_address": "Test Address",
    "complainant_phone": "1234567890",
    "station_name": "Test Station",
    "investigating_officer": "Test Officer"
  }'
```

### Step 5.5: Announce Migration Complete

**If all checks pass:**
- ✅ Notify stakeholders migration is complete
- ✅ Update status page
- ✅ Document any issues encountered
- ✅ Schedule post-migration review

**If issues detected:**
- ⚠️ Execute rollback procedure (see below)
- ⚠️ Investigate issues
- ⚠️ Schedule retry

**Estimated Time for Phase 5:** 10-15 minutes

---

## Rollback Procedures


### When to Rollback

Execute rollback if:
- ❌ Critical functionality broken (FIR generation fails)
- ❌ Error rate >5%
- ❌ Latency >2x baseline
- ❌ AWS service unavailable
- ❌ Data integrity issues
- ❌ Security concerns

### Rollback Method 1: Feature Flag (Instant - Recommended)

**Fastest rollback method - uses feature flag to switch back to GGUF:**

```bash
# Option A: Automated
make rollback-to-gguf

# Option B: Manual
ssh -i your-key.pem ubuntu@<CURRENT_EC2_IP>
cd /opt/afirgen

# Update environment variable
sed -i 's/ENABLE_BEDROCK=true/ENABLE_BEDROCK=false/' .env

# Restart application
sudo systemctl restart afirgen-backend

# Verify rollback
curl http://<CURRENT_EC2_IP>:8000/health | jq .implementation
# Expected: "gguf"
```

**Verify GGUF Services:**
```bash
# Check GGUF model servers are running
curl http://localhost:8001/health  # Model server
curl http://localhost:8002/health  # ASR/OCR server

# If not running, start them
sudo systemctl start gguf-model-server
sudo systemctl start gguf-asr-ocr-server
```

**Estimated Time:** 2-3 minutes

### Rollback Method 2: DNS/Load Balancer Revert

**Revert traffic to old GGUF instance:**

```bash
# Option A: DNS Revert
aws route53 change-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "afirgen.yourdomain.com",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "<OLD_EC2_IP>"}]
      }
    }]
  }'

# Option B: Load Balancer Revert
aws elbv2 register-targets \
  --target-group-arn <TARGET_GROUP_ARN> \
  --targets Id=<OLD_INSTANCE_ID>

aws elbv2 deregister-targets \
  --target-group-arn <TARGET_GROUP_ARN> \
  --targets Id=<NEW_INSTANCE_ID>
```

**Estimated Time:** 5-10 minutes (DNS propagation)

### Rollback Method 3: Infrastructure Teardown

**Complete rollback - destroy Bedrock infrastructure:**

```bash
# Navigate to terraform directory
cd "AFIRGEN FINAL/terraform/free-tier"

# Destroy Bedrock infrastructure
terraform destroy -target=module.bedrock

# Or destroy everything
terraform destroy

# Type 'yes' to confirm
```

**Warning:** This permanently deletes:
- New EC2 instance
- Vector database (OpenSearch or Aurora pgvector)
- VPC endpoints
- IAM roles

**Estimated Time:** 15-20 minutes

### Post-Rollback Verification

```bash
# Check health endpoint
curl http://<OLD_EC2_IP>:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "implementation": "gguf",
#   "enable_bedrock": false,
#   "gguf": {
#     "model_server": {"status": "healthy"},
#     "asr_ocr_server": {"status": "healthy"},
#     "kb_collections": 3,
#     "kb_cache_size": 100
#   }
# }

# Test FIR generation
curl -X POST http://<OLD_EC2_IP>:8000/api/v1/fir/generate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "complaint_text": "Rollback test complaint",
    "complainant_name": "Test User",
    "complainant_address": "Test Address",
    "complainant_phone": "1234567890",
    "station_name": "Test Station",
    "investigating_officer": "Test Officer"
  }'

# Verify FIR generated successfully
```

### Rollback Checklist

- [ ] Feature flag set to ENABLE_BEDROCK=false
- [ ] Application restarted
- [ ] GGUF model servers running
- [ ] Health endpoint shows "gguf" implementation
- [ ] Test FIR generation successful
- [ ] DNS/load balancer reverted (if applicable)
- [ ] Stakeholders notified of rollback
- [ ] Incident report created
- [ ] Root cause analysis scheduled

---

## Troubleshooting

### Issue: Bedrock Access Denied

**Symptoms:**
```
AccessDeniedException: User is not authorized to perform: bedrock:InvokeModel
```

**Solutions:**
1. Verify model access granted in AWS Console:
   - Bedrock → Model access → Verify "Access granted" for Claude 3 Sonnet and Titan Embeddings
2. Check IAM role permissions:
   ```bash
   aws iam get-role-policy --role-name afirgen-ec2-role --policy-name BedrockAccess
   ```
3. Verify model ID is correct in .env.bedrock
4. Check region supports Bedrock (us-east-1, us-west-2, ap-southeast-1, eu-central-1)


### Issue: Vector Database Connection Failed

**Symptoms:**
```
ConnectionError: Unable to connect to vector database
```

**Solutions:**

**For OpenSearch:**
1. Check security group allows EC2 → OpenSearch on port 443:
   ```bash
   aws ec2 describe-security-groups --group-ids <OPENSEARCH_SG_ID>
   ```
2. Verify VPC endpoint exists and is available:
   ```bash
   aws ec2 describe-vpc-endpoints --filters "Name=service-name,Values=*opensearch*"
   ```
3. Check IAM permissions for OpenSearch:
   ```bash
   aws iam get-role-policy --role-name afirgen-ec2-role --policy-name OpenSearchAccess
   ```
4. Verify endpoint URL in .env.bedrock is correct

**For Aurora pgvector:**
1. Check security group allows EC2 → RDS on port 5432:
   ```bash
   aws ec2 describe-security-groups --group-ids <RDS_SG_ID>
   ```
2. Verify credentials in .env.bedrock
3. Check pgvector extension installed:
   ```bash
   psql -h <PG_HOST> -U admin -d afirgen_vectors -c "SELECT * FROM pg_extension WHERE extname='vector';"
   ```
4. Check Aurora cluster status:
   ```bash
   aws rds describe-db-clusters --db-cluster-identifier afirgen-vectors
   ```

### Issue: Transcribe Job Failed

**Symptoms:**
```
TranscribeJobFailed: Job failed with status FAILED
```

**Solutions:**
1. Check audio format is supported (WAV, MP3, MPEG):
   ```bash
   file test_audio.mp3
   ```
2. Verify S3 permissions - IAM role must have s3:GetObject:
   ```bash
   aws iam get-role-policy --role-name afirgen-ec2-role --policy-name S3Access
   ```
3. Check language code is supported (hi-IN, en-IN, ta-IN, te-IN, bn-IN, mr-IN, gu-IN, kn-IN, ml-IN, pa-IN)
4. Check audio file size <2GB and duration <4 hours
5. View Transcribe job details:
   ```bash
   aws transcribe get-transcription-job --transcription-job-name <JOB_NAME>
   ```

### Issue: High Costs

**Symptoms:**
- AWS bill higher than expected
- Cost alerts triggered

**Solutions:**
1. Check cost breakdown in AWS Cost Explorer:
   - AWS Console → Cost Management → Cost Explorer
2. Identify expensive services:
   ```bash
   aws ce get-cost-and-usage \
     --time-period Start=2024-01-01,End=2024-01-31 \
     --granularity MONTHLY \
     --metrics BlendedCost \
     --group-by Type=SERVICE
   ```
3. **Switch to Aurora pgvector** (saves ~$300/month):
   ```bash
   # Update terraform.tfvars
   vector_db_type = "aurora_pgvector"
   
   # Apply changes
   terraform apply
   ```
4. **Enable caching** to reduce API calls:
   ```bash
   # In .env.bedrock
   ENABLE_CACHING=true
   CACHE_MAX_SIZE=100
   ```
5. **Optimize Bedrock prompts**:
   - Use shorter system prompts
   - Reduce max_tokens where possible
   - Use lower temperature for deterministic outputs
6. **Set up cost alerts**:
   ```bash
   aws budgets create-budget \
     --account-id <ACCOUNT_ID> \
     --budget file://budget.json \
     --notifications-with-subscribers file://notifications.json
   ```

### Issue: Slow Performance

**Symptoms:**
- FIR generation takes >5 minutes
- High latency on API requests

**Solutions:**
1. Check CloudWatch metrics for bottlenecks:
   - AWS Console → CloudWatch → Metrics → AFIRGen/Bedrock
2. Identify slow component:
   ```bash
   # Check X-Ray traces
   # AWS Console → X-Ray → Traces → Sort by duration
   ```
3. **Enable caching**:
   ```bash
   ENABLE_CACHING=true
   CACHE_MAX_SIZE=100
   ```
4. **Upgrade instance type**:
   ```bash
   # Update terraform.tfvars
   instance_type = "t3.medium"  # or t3.large
   
   # Apply changes
   terraform apply
   ```
5. **Optimize vector search**:
   - Reduce top_k from 5 to 3
   - Use approximate search instead of exact
6. **Check network latency**:
   - Ensure VPC endpoints are used (not public internet)
   - Verify EC2 and services in same region

### Issue: Application Won't Start

**Symptoms:**
```
systemctl status afirgen-backend
● afirgen-backend.service - AFIRGen Backend Service
   Loaded: loaded
   Active: failed
```

**Solutions:**
1. Check application logs:
   ```bash
   sudo journalctl -u afirgen-backend -n 50
   ```
2. Check environment variables:
   ```bash
   cat /opt/afirgen/.env.bedrock
   python scripts/validate-env.py
   ```
3. Check port binding:
   ```bash
   sudo netstat -tulpn | grep 8000
   # If port in use, kill process or change port
   ```
4. Check Python dependencies:
   ```bash
   pip list | grep -E "boto3|opensearch|asyncpg"
   ```
5. Test manual start:
   ```bash
   cd /opt/afirgen
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   # Check error output
   ```

### Issue: Data Migration Failed

**Symptoms:**
```
Migration failed: Vector count mismatch
Source: 500, Target: 0
```

**Solutions:**
1. Check vector database connectivity:
   ```bash
   python scripts/verify_migration.py
   ```
2. Check Titan Embeddings access:
   ```bash
   aws bedrock invoke-model \
     --model-id amazon.titan-embed-text-v1 \
     --body '{"inputText":"test"}' \
     --region us-east-1 \
     output.json
   ```
3. Check export file exists:
   ```bash
   ls -lh data/ipc_sections_export.json
   ```
4. Re-run migration with verbose logging:
   ```bash
   python scripts/migrate_vector_db.py --verbose
   ```
5. Check migration logs:
   ```bash
   tail -f logs/migration.log
   ```

For more troubleshooting, see [BEDROCK-TROUBLESHOOTING.md](BEDROCK-TROUBLESHOOTING.md).

---

## Post-Migration Tasks


### Week 1: Immediate Post-Migration

**Day 1-2: Intensive Monitoring**
- [ ] Monitor CloudWatch metrics every hour
- [ ] Review X-Ray traces for errors
- [ ] Check application logs for warnings
- [ ] Monitor AWS costs daily
- [ ] Verify all features working correctly
- [ ] Collect user feedback

**Day 3-7: Stabilization**
- [ ] Review performance metrics
- [ ] Optimize slow queries
- [ ] Tune cache settings
- [ ] Adjust instance size if needed
- [ ] Document any issues encountered
- [ ] Update runbooks

### Week 2-4: Optimization

**Performance Optimization:**
- [ ] Analyze CloudWatch metrics for bottlenecks
- [ ] Review X-Ray traces for optimization opportunities
- [ ] Tune vector database settings
- [ ] Optimize Bedrock prompts
- [ ] Implement additional caching where beneficial
- [ ] Load test with production traffic patterns

**Cost Optimization:**
- [ ] Review AWS Cost Explorer
- [ ] Identify cost optimization opportunities
- [ ] Consider Reserved Instances for EC2/RDS (1-year commitment)
- [ ] Evaluate Aurora pgvector vs OpenSearch costs
- [ ] Set up cost anomaly detection
- [ ] Implement cost allocation tags

**Security Hardening:**
- [ ] Review IAM policies for least privilege
- [ ] Enable AWS GuardDuty
- [ ] Configure AWS WAF (if public-facing)
- [ ] Set up AWS Security Hub
- [ ] Review CloudTrail logs
- [ ] Conduct security audit

### Month 2+: Long-Term Maintenance

**Monthly Tasks:**
- [ ] Review cost reports
- [ ] Update dependencies
- [ ] Review security patches
- [ ] Optimize vector database
- [ ] Review and update documentation
- [ ] Conduct disaster recovery drill

**Quarterly Tasks:**
- [ ] Review architecture for improvements
- [ ] Evaluate new AWS services
- [ ] Conduct performance review
- [ ] Update cost projections
- [ ] Review and update monitoring/alerting
- [ ] Conduct security audit

### Decommission Old GGUF Infrastructure

**After 30 days of stable Bedrock operation:**

1. **Final Backup:**
   ```bash
   # Backup GGUF instance data
   ssh -i your-key.pem ubuntu@<OLD_EC2_IP>
   cd /opt/afirgen
   tar -czf afirgen-gguf-backup-$(date +%Y%m%d).tar.gz .
   
   # Download backup
   scp -i your-key.pem ubuntu@<OLD_EC2_IP>:/opt/afirgen/afirgen-gguf-backup-*.tar.gz ./
   
   # Upload to S3 for long-term storage
   aws s3 cp afirgen-gguf-backup-*.tar.gz s3://afirgen-backups/
   ```

2. **Stop GGUF Instance:**
   ```bash
   # Stop instance (don't terminate yet)
   aws ec2 stop-instances --instance-ids <OLD_INSTANCE_ID>
   ```

3. **Monitor for 7 Days:**
   - Verify no issues with Bedrock system
   - Confirm no need to rollback
   - Get stakeholder approval

4. **Terminate GGUF Instance:**
   ```bash
   # Create final snapshot
   aws ec2 create-image \
     --instance-id <OLD_INSTANCE_ID> \
     --name "afirgen-gguf-final-snapshot-$(date +%Y%m%d)" \
     --description "Final snapshot before termination"
   
   # Terminate instance
   aws ec2 terminate-instances --instance-ids <OLD_INSTANCE_ID>
   ```

5. **Update Documentation:**
   - [ ] Update architecture diagrams
   - [ ] Update deployment documentation
   - [ ] Update runbooks
   - [ ] Archive GGUF-specific documentation

---

## Cost Monitoring

### Set Up Cost Alerts

**Create Monthly Budget:**
```bash
# Create budget.json
cat > budget.json << EOF
{
  "BudgetName": "AFIRGen-Monthly-Budget",
  "BudgetLimit": {
    "Amount": "200",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
EOF

# Create notifications.json
cat > notifications.json << EOF
[
  {
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 80
    },
    "Subscribers": [
      {
        "SubscriptionType": "EMAIL",
        "Address": "your-email@example.com"
      }
    ]
  },
  {
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 100
    },
    "Subscribers": [
      {
        "SubscriptionType": "EMAIL",
        "Address": "your-email@example.com"
      }
    ]
  }
]
EOF

# Create budget
aws budgets create-budget \
  --account-id <ACCOUNT_ID> \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

### Monitor Daily Costs

**View Cost Breakdown:**
```bash
# Get today's costs by service
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-%d),End=$(date -d tomorrow +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=SERVICE \
  --output table

# Get month-to-date costs
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE \
  --output table
```

### Cost Optimization Checklist

**Monthly Review:**
- [ ] Review AWS Cost Explorer
- [ ] Check for unused resources
- [ ] Verify S3 lifecycle policies working
- [ ] Review Bedrock token usage
- [ ] Check Transcribe usage patterns
- [ ] Review Textract usage
- [ ] Evaluate vector database costs
- [ ] Consider Reserved Instances

**Cost Reduction Strategies:**

1. **Vector Database:**
   - OpenSearch Serverless: ~$350/month
   - Aurora pgvector: ~$50/month
   - **Savings: $300/month**

2. **Reserved Instances (1-year):**
   - EC2 t3.small: ~40% savings
   - RDS db.t3.micro: ~35% savings
   - **Savings: ~$10/month**

3. **Caching:**
   - Enable IPC section caching
   - Reduce embedding API calls by 30-50%
   - **Savings: ~$5-10/month**

4. **Prompt Optimization:**
   - Use shorter system prompts
   - Reduce max_tokens where possible
   - **Savings: ~$5-10/month**

5. **S3 Lifecycle:**
   - Auto-delete temp files after 7 days
   - **Savings: ~$1-2/month**

**Target Monthly Cost (Optimized):**
- EC2 t3.small: $15
- RDS db.t3.micro: $12
- Aurora pgvector: $50
- Bedrock (moderate usage): $10-20
- Transcribe (moderate usage): $20-30
- Textract (moderate usage): $5-10
- S3, CloudWatch, X-Ray: $5-10
- **Total: $117-147/month**

**vs GGUF Architecture:**
- g5.2xlarge: $870/month
- **Savings: $723-753/month (85-87%)**

---

## Migration Timeline Summary


| Phase | Duration | Downtime | Key Activities |
|-------|----------|----------|----------------|
| **Prerequisites** | 1-2 hours | None | Request Bedrock access, install tools, backup data |
| **Phase 1: Infrastructure** | 30-45 min | None | Deploy Terraform, create new infrastructure |
| **Phase 2: Data Migration** | 20-30 min | None | Export ChromaDB, migrate to vector DB |
| **Phase 3: Application** | 15-20 min | None | Deploy code, start services |
| **Phase 4: Testing** | 30-45 min | None | Test all functionality, verify performance |
| **Phase 5: Cutover** | 10-15 min | <5 min | Update DNS/LB, monitor traffic |
| **Total** | **2-3 hours** | **<5 min** | Complete migration |

**Recommended Schedule:**
- **Day 1 (Morning):** Prerequisites, Phase 1-3
- **Day 1 (Afternoon):** Phase 4 (Testing)
- **Day 2 (Off-peak):** Phase 5 (Cutover)
- **Day 2-7:** Intensive monitoring
- **Week 2-4:** Optimization
- **Month 2:** Decommission GGUF

---

## Success Criteria

### Technical Success Criteria

- ✅ All FIR generation workflows functional (text, audio, image)
- ✅ All 10 Indian languages supported for transcription
- ✅ Vector search returns relevant IPC sections
- ✅ Performance meets requirements:
  - Audio transcription: <3 minutes for 5-minute files
  - Document OCR: <30 seconds
  - Legal narrative: <10 seconds
  - Vector search: <2 seconds
  - End-to-end FIR: <5 minutes
- ✅ 99% success rate maintained
- ✅ System handles 10 concurrent requests
- ✅ Monitoring and alerting operational
- ✅ Rollback capability verified

### Business Success Criteria

- ✅ Cost reduction achieved (85-95%)
- ✅ Zero data loss
- ✅ Minimal downtime (<5 minutes)
- ✅ User satisfaction maintained
- ✅ All security requirements met
- ✅ Documentation complete

### Operational Success Criteria

- ✅ Team trained on new architecture
- ✅ Runbooks updated
- ✅ Monitoring dashboards configured
- ✅ Cost tracking enabled
- ✅ Backup and recovery tested
- ✅ Incident response plan updated

---

## Key Contacts and Resources

### Documentation

- [AWS Deployment Plan](AWS-DEPLOYMENT-PLAN.md)
- [Quick Start Guide](QUICK-START-AWS.md)
- [Bedrock Configuration](BEDROCK-CONFIGURATION.md)
- [Troubleshooting Guide](BEDROCK-TROUBLESHOOTING.md)
- [Feature Flag Rollback](AFIRGEN FINAL/docs/FEATURE-FLAG-ROLLBACK.md)
- [API Documentation](AFIRGEN FINAL/docs/API.md)

### AWS Resources

- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Amazon Transcribe Documentation](https://docs.aws.amazon.com/transcribe/)
- [Amazon Textract Documentation](https://docs.aws.amazon.com/textract/)
- [OpenSearch Serverless Documentation](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html)
- [Aurora PostgreSQL Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/)

### Support Channels

- **AWS Support:** Open support case in AWS Console
- **AWS Service Health:** https://status.aws.amazon.com/
- **Internal Team:** [Your team contact info]
- **On-Call Engineer:** [On-call rotation]

---

## Appendix A: Quick Reference Commands

### Health Checks
```bash
# Application health
curl http://$EC2_IP:8000/health

# AWS service connectivity
python scripts/validate-env.py

# Vector database
python scripts/verify_migration.py
```

### Monitoring
```bash
# Application logs
sudo journalctl -u afirgen-backend -f

# CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AFIRGen/Bedrock \
  --metric-name FIRGenerationCount \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# X-Ray traces
# AWS Console → X-Ray → Traces
```

### Rollback
```bash
# Feature flag rollback (instant)
make rollback-to-gguf

# Or manual
ssh -i your-key.pem ubuntu@$EC2_IP
sed -i 's/ENABLE_BEDROCK=true/ENABLE_BEDROCK=false/' .env
sudo systemctl restart afirgen-backend
```

### Cost Monitoring
```bash
# Daily costs
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-%d),End=$(date -d tomorrow +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

---

## Appendix B: Troubleshooting Decision Tree

```
Issue: FIR Generation Failed
│
├─ Check health endpoint
│  ├─ Unhealthy → Check application logs
│  │  ├─ AWS service error → Check IAM permissions, service quotas
│  │  ├─ Database error → Check RDS/vector DB connectivity
│  │  └─ Application error → Check environment variables, dependencies
│  │
│  └─ Healthy → Check specific component
│     ├─ Transcribe failed → Check audio format, S3 permissions, language code
│     ├─ Textract failed → Check image format, S3 permissions
│     ├─ Bedrock failed → Check model access, IAM permissions, rate limits
│     └─ Vector search failed → Check vector DB connectivity, data migration
│
└─ If critical → Execute rollback procedure
```

---

## Appendix C: Migration Checklist

**Print this checklist and check off items as you complete them:**

### Pre-Migration
- [ ] AWS account configured
- [ ] Bedrock model access granted
- [ ] Tools installed (Terraform, AWS CLI)
- [ ] Current system backed up
- [ ] Documentation reviewed
- [ ] Team briefed
- [ ] Migration window scheduled

### Phase 1: Infrastructure
- [ ] Terraform variables configured
- [ ] Terraform initialized and validated
- [ ] Infrastructure deployed
- [ ] Outputs saved
- [ ] Infrastructure verified

### Phase 2: Data Migration
- [ ] ChromaDB exported
- [ ] Environment variables configured
- [ ] Configuration validated
- [ ] IPC sections migrated
- [ ] Migration verified

### Phase 3: Application
- [ ] Application code deployed
- [ ] Services started
- [ ] Health check passed
- [ ] X-Ray daemon configured
- [ ] CloudWatch agent configured

### Phase 4: Testing
- [ ] Audio transcription tested (all languages)
- [ ] Document OCR tested
- [ ] Text FIR generation tested
- [ ] Vector search tested
- [ ] Performance tested
- [ ] Integration tests passed
- [ ] Monitoring verified

### Phase 5: Cutover
- [ ] Pre-cutover checklist complete
- [ ] DNS/load balancer updated
- [ ] Production traffic monitored
- [ ] Production functionality verified
- [ ] Stakeholders notified

### Post-Migration
- [ ] Week 1 monitoring complete
- [ ] Performance optimized
- [ ] Costs optimized
- [ ] Security hardened
- [ ] Documentation updated
- [ ] GGUF infrastructure decommissioned (after 30 days)

---

## Conclusion

This migration guide provides a comprehensive roadmap for transitioning from GGUF to Bedrock architecture. The migration is designed to be:

- **Low-risk:** Feature flag enables instant rollback
- **Fast:** Complete migration in 2-3 hours
- **Cost-effective:** 85-95% cost reduction
- **Zero-downtime:** <5 minutes of downtime during cutover

**Key Success Factors:**
1. Request Bedrock model access BEFORE starting
2. Backup all data before migration
3. Test thoroughly in Phase 4
4. Monitor intensively after cutover
5. Keep rollback procedure ready

**Remember:** The feature flag (`ENABLE_BEDROCK`) allows instant rollback if any issues occur. Don't hesitate to rollback if critical functionality is impacted.

For questions or issues during migration, refer to:
- [BEDROCK-TROUBLESHOOTING.md](BEDROCK-TROUBLESHOOTING.md)
- [AWS Support](https://console.aws.amazon.com/support/)
- Your internal team contacts

**Good luck with your migration!** 🚀

