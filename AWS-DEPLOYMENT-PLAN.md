# AFIRGen AWS Free Tier Deployment Plan

## Executive Summary

This plan provides step-by-step instructions to deploy AFIRGen on AWS within free tier limits. The deployment is **95% automated** using Terraform for infrastructure and automated scripts for model/data downloads from HuggingFace.

**Estimated Time**: 30-45 minutes for first-time deployment
**Monthly Cost**: $0 (within free tier limits for 12 months)
**Automation Level**: 95% automated (everything except AWS account setup)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ AWS Free Tier Architecture                                  │
│                                                             │
│  Internet                                                   │
│     │                                                       │
│     ▼                                                       │
│  [Elastic IP] ──> [EC2 t2.micro - Public Subnet]          │
│                    │                                        │
│                    ├─ Docker: Main Backend (Port 8000)     │
│                    ├─ Docker: GGUF Model Server (8001)     │
│                    ├─ Docker: ASR/OCR Server (8002)        │
│                    ├─ Docker: Frontend (80)                │
│                    ├─ Docker: Nginx (443)                  │
│                    ├─ Docker: Redis                        │
│                    └─ Docker: Celery Worker                │
│                    │                                        │
│                    ▼                                        │
│              [RDS db.t3.micro - Private Subnet]            │
│                    MySQL 8.0 (20GB)                        │
│                                                             │
│  [S3 Buckets]                                              │
│     ├─ afirgen-models (ML models ~5GB)                    │
│     ├─ afirgen-frontend (static files)                    │
│     ├─ afirgen-temp (uploads)                             │
│     └─ afirgen-backups (DB backups)                       │
│                                                             │
│  [CloudWatch] - Monitoring & Logs                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### 1. AWS Account Setup
- [ ] Create AWS account at https://aws.amazon.com/
- [ ] Verify free tier eligibility (12 months for new accounts)
- [ ] Enable MFA for root account (security best practice)
- [ ] Create IAM user with admin access
- [ ] Save AWS Access Key ID and Secret Access Key

### 2. Local Tools Installation

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
# Or download from https://www.terraform.io/downloads

# AWS CLI
# macOS
brew install awscli

# Windows
choco install awscli
# Or download from https://aws.amazon.com/cli/
```

### 3. Configure AWS CLI

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
# - Default region: us-east-1
# - Default output format: json

# Verify configuration
aws sts get-caller-identity
```

---

## 🚀 QUICK START (Fully Automated)

If you just want to deploy everything quickly:

```bash
# 1. Install tools and configure AWS
make install-tools
make setup-aws

# 2. Deploy everything (infrastructure + models + app)
make deploy-all
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

# Edit terraform.tfvars (optional - defaults are optimized)
# You can customize:
# - project_name
# - environment
# - aws_region (keep us-east-1 for free tier)
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
# - 2 Security Groups
# - 4 S3 Buckets
# - 1 EC2 t2.micro instance
# - 1 RDS db.t3.micro instance
# - 1 Elastic IP
# - IAM roles and policies
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
# Deployment takes 10-15 minutes
```

### Step 1.5: Save Outputs

```bash
# Save all outputs to file
terraform output -json > deployment-outputs.json

# View specific outputs
terraform output ec2_public_ip
terraform output rds_endpoint
terraform output s3_bucket_names
```

**What Gets Created Automatically:**
- ✅ VPC with public and private subnets
- ✅ Security groups (EC2, RDS)
- ✅ S3 buckets with lifecycle policies
- ✅ EC2 instance with Docker pre-installed
- ✅ RDS MySQL database
- ✅ CloudWatch monitoring setup
- ✅ IAM roles and policies

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

### Step 2.2: Download ML Models from HuggingFace (AUTOMATED)

**Option A: Automated (Recommended)**
```bash
make download-models
```

This automatically downloads:
- ✅ complaint_2summarizing.gguf (~1.5GB)
- ✅ complaint_summarizing_model.gguf (~1.5GB)
- ✅ BNS-RAG-q4k.gguf (~2GB)
- ✅ Whisper 'tiny' model (~75MB)
- ✅ Donut OCR model (~500MB)

**Option B: Manual**
```bash
cd "AFIRGEN FINAL"
chmod +x scripts/download-models.sh
./scripts/download-models.sh
```

All models are downloaded from HuggingFace user: [navaneeth005](https://huggingface.co/navaneeth005)

### Step 2.3: Configure Environment Variables (MANUAL)

```bash
# SSH to EC2 instance
ssh -i your-key.pem ubuntu@$EC2_IP

# Navigate to application directory
cd /opt/afirgen

# Create .env file from example
cp .env.example .env

# Edit .env file
nano .env
```

**Required Configuration:**
```bash
# MySQL Database (RDS endpoint from Terraform output)
MYSQL_HOST=<RDS_ENDPOINT>  # Get from: terraform output rds_endpoint
MYSQL_PORT=3306
MYSQL_USER=admin
MYSQL_PASSWORD=<YOUR_SECURE_PASSWORD>  # Set during Terraform apply
MYSQL_DB=fir_db

# Application Configuration
PORT=8000
FIR_AUTH_KEY=<GENERATE_SECURE_KEY>  # Use: openssl rand -hex 32
API_KEY=<GENERATE_SECURE_KEY>  # Use: openssl rand -hex 32

# Model Server Configuration
MODEL_SERVER_PORT=8001
ASR_OCR_PORT=8002

# CORS Configuration (use your domain or EC2 IP)
CORS_ORIGINS=http://<EC2_PUBLIC_IP>,https://<EC2_PUBLIC_IP>

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Security
ENFORCE_HTTPS=false  # Set to true after SSL setup
SESSION_TIMEOUT=3600

# Frontend Configuration
API_BASE_URL=http://<EC2_PUBLIC_IP>:8000
ENVIRONMENT=production
ENABLE_DEBUG=false

# AWS Configuration
AWS_REGION=us-east-1
USE_AWS_SECRETS=false  # Can enable later for better security
```

### Step 2.4: Download Models from S3 to EC2

```bash
# SSH to EC2 instance
ssh -i your-key.pem ubuntu@$EC2_IP

# Get models bucket name
MODELS_BUCKET=$(aws s3 ls | grep afirgen-models | awk '{print $3}')

# Download models to EC2
cd /opt/afirgen
aws s3 sync s3://$MODELS_BUCKET/ ./models/

# Verify models downloaded
ls -lh models/
```

### Step 2.5: Download Knowledge Base Files (AUTOMATED)

**Option A: Automated (Recommended)**
```bash
make download-kb
```

This automatically downloads from HuggingFace:
- ✅ BNS_basic_chroma.jsonl (BNS definitions)
- ✅ BNS_details_chroma.jsonl (BNS detailed sections)
- ✅ BNS_spacts_chroma.jsonl (Special acts)
- ✅ BNS_basic.jsonl (General retrieval)
- ✅ BNS_indepth.jsonl (Detailed retrieval)
- ✅ spacts.jsonl (Special acts retrieval)

**Option B: Manual**
```bash
cd "AFIRGEN FINAL"
chmod +x scripts/download-knowledge-base.sh
./scripts/download-knowledge-base.sh
```

All datasets are downloaded from HuggingFace user: [navaneeth005](https://huggingface.co/navaneeth005)

### Step 2.6: Deploy Application to EC2 (AUTOMATED)

**Option A: Automated (Recommended)**
```bash
make deploy-app
```

This automatically:
- ✅ Copies application files to EC2
- ✅ Copies knowledge base files to EC2
- ✅ Starts all Docker services
- ✅ Waits for services to be healthy

**Option B: Manual**
```bash
# SSH to EC2 instance
ssh -i your-key.pem ubuntu@$EC2_IP

# Navigate to application directory
cd /opt/afirgen

# Start all services with Docker Compose
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 2.7: Verify Deployment (AUTOMATED)

**Option A: Automated (Recommended)**
```bash
make verify
```

This automatically:
- ✅ Tests health endpoint
- ✅ Displays access URLs
- ✅ Verifies all services are running

**Option B: Manual**
```bash
# Check health endpoint
curl http://<EC2_PUBLIC_IP>:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "model_server": {"status": "healthy"},
#   "asr_ocr_server": {"status": "healthy"},
#   "database": "connected",
#   "kb_collections": 3
# }

# Access frontend
# Open browser: http://<EC2_PUBLIC_IP>

# Check API documentation
# Open browser: http://<EC2_PUBLIC_IP>:8000/docs
```

---

## Phase 3: Database Setup (AUTOMATED)

The database is automatically initialized by the application on first start. No manual steps required!

**What Happens Automatically:**
- ✅ Database connection established to RDS
- ✅ `fir_records` table created
- ✅ Connection pooling configured
- ✅ Character encoding set (utf8mb4)

**Verify Database:**
```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@$EC2_IP

# Check database connection
docker exec -it <backend-container-id> python -c "
from infrastructure.database import get_db_connection
conn = get_db_connection()
print('Database connected successfully!')
conn.close()
"
```

---

## Phase 4: SSL/HTTPS Setup (OPTIONAL - MANUAL)

### Option A: Self-Signed Certificate (Development)

```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@$EC2_IP

cd /opt/afirgen
./scripts/generate-certs.sh
# Select option 1 for self-signed certificate

# Update .env
nano .env
# Set: ENFORCE_HTTPS=true

# Restart services
docker-compose restart
```

### Option B: Let's Encrypt (Production - Requires Domain)

**Prerequisites:**
- Domain name pointed to EC2 Elastic IP
- Port 80 and 443 open in security group

```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@$EC2_IP

cd /opt/afirgen
./scripts/generate-certs.sh
# Select option 2 for Let's Encrypt
# Enter your domain name and email

# Update .env
nano .env
# Set: ENFORCE_HTTPS=true
# Set: DOMAIN_NAME=yourdomain.com

# Restart services
docker-compose restart
```

---

## Phase 5: Monitoring & Maintenance (AUTOMATED)

### CloudWatch Monitoring (Already Configured)

**Automatic Monitoring:**
- ✅ EC2 CPU, memory, disk metrics
- ✅ RDS database metrics
- ✅ Application logs
- ✅ Error tracking
- ✅ Performance metrics

**View Metrics:**
```bash
# AWS Console → CloudWatch → Dashboards
# Look for: afirgen-free-tier-dashboard
```

### Automated Backups (Already Configured)

**Database Backups:**
- ✅ Daily automated backups to S3
- ✅ 7-day retention policy
- ✅ Runs via cron job on EC2

**Verify Backups:**
```bash
# Check backup bucket
BACKUP_BUCKET=$(terraform output -raw s3_backups_bucket)
aws s3 ls s3://$BACKUP_BUCKET/

# View backup logs on EC2
ssh -i your-key.pem ubuntu@$EC2_IP
cat /var/log/backup.log
```

---

## Cost Breakdown (Free Tier)

| Service | Free Tier Limit | Usage | Cost |
|---------|----------------|-------|------|
| EC2 t2.micro | 750 hours/month | 1 instance 24/7 | $0 |
| RDS db.t3.micro | 750 hours/month | 1 instance 24/7 | $0 |
| EBS Storage | 30 GB | 30 GB (EC2) + 20 GB (RDS) | $0 |
| S3 Storage | 5 GB | ~5 GB (models) | $0 |
| S3 Requests | 20,000 GET, 2,000 PUT | Normal usage | $0 |
| Data Transfer | 100 GB/month out | Typical usage | $0 |
| CloudWatch | 10 metrics, 5 GB logs | Standard monitoring | $0 |
| **Total** | | | **$0/month** |

**After Free Tier (12 months):**
- Estimated cost: $30-40/month
- Can optimize further or migrate to cheaper alternatives

---

## Automation Summary

### What's Automated ✅

1. **Infrastructure Provisioning** (Terraform)
   - VPC, subnets, security groups
   - EC2 instance with Docker
   - RDS database
   - S3 buckets
   - IAM roles and policies
   - CloudWatch monitoring

2. **EC2 Setup** (User Data Script)
   - Docker and Docker Compose installation
   - CloudWatch agent setup
   - Directory structure creation
   - Cron jobs for backups
   - Monitoring scripts

3. **Application Initialization**
   - Database table creation
   - Connection pooling
   - Health checks
   - Auto-restart on failure

4. **Monitoring & Backups**
   - CloudWatch metrics collection
   - Daily database backups
   - Log aggregation
   - Alert notifications

### What's Manual 🔧

1. **Initial Setup**
   - AWS account creation
   - Tool installation (Terraform, AWS CLI)
   - AWS credentials configuration
   - SSH key pair creation

2. **Model Deployment**
   - Uploading ML models to S3 (large files)
   - Downloading models to EC2
   - Model file verification

3. **Configuration**
   - Environment variables (.env file)
   - Security keys generation
   - Domain name setup (if using HTTPS)
   - CORS origins configuration

4. **Knowledge Base**
   - Uploading RAG database files
   - Uploading general retrieval files

5. **SSL/HTTPS** (Optional)
   - Certificate generation
   - Domain DNS configuration

---

## Troubleshooting Guide

### Issue: Terraform Apply Fails

**Solution:**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify region
aws configure get region

# Check for resource limits
aws service-quotas list-service-quotas --service-code ec2

# Retry with verbose logging
terraform apply -auto-approve TF_LOG=DEBUG
```

### Issue: EC2 Instance Not Accessible

**Solution:**
```bash
# Check instance status
aws ec2 describe-instances --instance-ids <INSTANCE_ID>

# Verify security group allows SSH (port 22)
aws ec2 describe-security-groups --group-ids <SG_ID>

# Check SSH key permissions
chmod 400 your-key.pem

# Try connecting with verbose output
ssh -v -i your-key.pem ubuntu@<EC2_IP>
```

### Issue: Docker Services Won't Start

**Solution:**
```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@$EC2_IP

# Check Docker status
sudo systemctl status docker

# Check disk space
df -h

# Check memory
free -h

# View service logs
docker-compose logs <service-name>

# Restart services
docker-compose restart
```

### Issue: Database Connection Failed

**Solution:**
```bash
# Verify RDS endpoint
terraform output rds_endpoint

# Check security group allows EC2 to RDS (port 3306)
aws ec2 describe-security-groups --group-ids <RDS_SG_ID>

# Test connection from EC2
ssh -i your-key.pem ubuntu@$EC2_IP
mysql -h <RDS_ENDPOINT> -u admin -p

# Check RDS status
aws rds describe-db-instances --db-instance-identifier <DB_ID>
```

### Issue: Models Not Loading

**Solution:**
```bash
# Check model files exist
ssh -i your-key.pem ubuntu@$EC2_IP
ls -lh /opt/afirgen/models/

# Check model server logs
docker-compose logs gguf_model_server
docker-compose logs asr_ocr_model_server

# Verify model file permissions
chmod -R 755 /opt/afirgen/models/

# Check available disk space
df -h /opt/afirgen/models/
```

---

## Maintenance Tasks

### Daily (Automated)
- ✅ Database backups to S3
- ✅ Log rotation
- ✅ Health checks

### Weekly (Manual)
- [ ] Review CloudWatch metrics
- [ ] Check disk space usage
- [ ] Review application logs
- [ ] Test backup restoration

### Monthly (Manual)
- [ ] Update Docker images
- [ ] Review security groups
- [ ] Check AWS free tier usage
- [ ] Update SSL certificates (if using Let's Encrypt)

---

## Cleanup / Teardown

### To Remove Everything:

```bash
# Navigate to terraform directory
cd "AFIRGEN FINAL/terraform/free-tier"

# Destroy all resources
terraform destroy

# Type 'yes' to confirm

# Verify all resources deleted
aws ec2 describe-instances --filters "Name=tag:Project,Values=afirgen"
aws rds describe-db-instances
aws s3 ls | grep afirgen
```

**Warning:** This will permanently delete:
- All EC2 instances and data
- RDS database and all FIR records
- S3 buckets and all files
- All networking infrastructure

---

## Next Steps After Deployment

1. **Test the Application**
   - Generate a test FIR
   - Verify speech-to-text works
   - Test OCR functionality
   - Check database records

2. **Configure Domain (Optional)**
   - Point domain to Elastic IP
   - Set up SSL with Let's Encrypt
   - Update CORS origins

3. **Set Up Monitoring Alerts**
   - Configure CloudWatch alarms
   - Set up email notifications
   - Monitor free tier usage

4. **Optimize Performance**
   - Review CloudWatch metrics
   - Adjust resource limits
   - Optimize model loading

5. **Security Hardening**
   - Enable AWS Secrets Manager
   - Set up VPN for SSH access
   - Configure WAF (if needed)
   - Regular security audits

---

## Support & Resources

**Documentation:**
- [Terraform Free Tier README](AFIRGEN FINAL/terraform/free-tier/README.md)
- [Deployment Guide](AFIRGEN FINAL/terraform/free-tier/DEPLOYMENT-GUIDE.md)
- [Setup Guide](AFIRGEN FINAL/SETUP.md)
- [Security Documentation](AFIRGEN FINAL/SECURITY.md)

**AWS Resources:**
- [AWS Free Tier](https://aws.amazon.com/free/)
- [EC2 Documentation](https://docs.aws.amazon.com/ec2/)
- [RDS Documentation](https://docs.aws.amazon.com/rds/)
- [S3 Documentation](https://docs.aws.amazon.com/s3/)

**Terraform:**
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Documentation](https://www.terraform.io/docs)

---

## Summary

**Automation Level:**
- 70% automated (infrastructure, setup, monitoring)
- 30% manual (models, configuration, knowledge base)

**Time Investment:**
- First deployment: 2-3 hours
- Subsequent deployments: 30-45 minutes

**Cost:**
- Free for 12 months (within free tier)
- ~$30-40/month after free tier expires

**Recommended Approach:**
1. Use Terraform for infrastructure (fully automated)
2. Use user data script for EC2 setup (automated)
3. Manually upload models and configure environment
4. Let application handle database initialization
5. Set up monitoring and backups (automated)

This gives you the best balance of automation and control!
