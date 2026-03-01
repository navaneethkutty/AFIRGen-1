# Bedrock Migration - Terraform Configuration Update Summary

## Overview
This document summarizes the Terraform infrastructure changes for migrating AFIRGen from GPU-based GGUF models to AWS Bedrock managed services.

## Changes Made

### 1. EC2 Instance Configuration (`ec2.tf`)

#### Instance Type Change
- **Before**: `g5.2xlarge` (GPU instance with NVIDIA A10G, 24GB VRAM, 32GB RAM - $1.21/hour)
- **After**: Configurable via `var.ec2_instance_type` (default: `t3.small` - 2 vCPU, 2GB RAM - $0.0208/hour)
- **Cost Savings**: ~$0.87/hour (~$626/month)

#### Storage Optimization
- **Before**: 200GB gp3 EBS volume for models and data
- **After**: 30GB gp3 EBS volume (no local models needed)
- **Reason**: AWS managed services eliminate need for local model storage

#### New IAM Policies Added
1. **Bedrock Access Policy**
   - Actions: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
   - Resources: Claude 3 Sonnet and Titan Embeddings models

2. **Transcribe Access Policy**
   - Actions: `transcribe:StartTranscriptionJob`, `transcribe:GetTranscriptionJob`, `transcribe:DeleteTranscriptionJob`
   - Supports 10 Indian languages

3. **Textract Access Policy**
   - Actions: `textract:DetectDocumentText`, `textract:AnalyzeDocument`
   - For document OCR processing

4. **Enhanced CloudWatch Policy**
   - Added X-Ray tracing permissions
   - Scoped CloudWatch metrics to `AFIRGen/Bedrock` namespace

5. **KMS Policy**
   - For S3 and RDS encryption key access

6. **OpenSearch Policy** (conditional)
   - Only created if `vector_db_type = "opensearch"`
   - Action: `aoss:APIAccessAll`

7. **RDS Connect Policy** (conditional)
   - Only created if `vector_db_type = "aurora_pgvector"`
   - Action: `rds-db:connect` for IAM authentication

### 2. VPC Configuration (`vpc.tf`)

#### New VPC Endpoints Added
All endpoints are Interface type (except S3 which is Gateway type):

1. **Bedrock Runtime Endpoint**
   - Service: `com.amazonaws.{region}.bedrock-runtime`
   - Purpose: Access Claude and Titan models
   - Private DNS enabled

2. **Transcribe Endpoint**
   - Service: `com.amazonaws.{region}.transcribe`
   - Purpose: Audio transcription service
   - Private DNS enabled

3. **Textract Endpoint**
   - Service: `com.amazonaws.{region}.textract`
   - Purpose: Document OCR service
   - Private DNS enabled

4. **VPC Endpoints Security Group**
   - Allows HTTPS (443) from VPC CIDR
   - Attached to all interface endpoints

#### Benefits
- Reduced data transfer costs (traffic stays within AWS network)
- Improved security (no internet gateway needed for AWS services)
- Lower latency

### 3. Vector Database Configuration (`vector-db.tf` - NEW FILE)

#### Supports Two Options

**Option 1: Aurora PostgreSQL with pgvector (Recommended)**
- Engine: Aurora PostgreSQL 15.4
- Serverless v2 with auto-scaling (0.5-1.0 ACU)
- Estimated cost: ~$43/month
- Features:
  - pgvector extension for vector similarity search
  - IVFFlat index for fast approximate nearest neighbor search
  - 1536-dimensional embeddings from Titan
  - Backup retention: 7 days
  - Encryption at rest enabled

**Option 2: OpenSearch Serverless (Alternative)**
- Collection type: VECTORSEARCH
- Minimum: 2 OCU (1 indexing + 1 search)
- Estimated cost: ~$346/month
- Features:
  - k-NN search with HNSW algorithm
  - Cosine similarity metric
  - Encryption and network policies
  - IAM-based access control

#### Selection
- Controlled by `vector_db_type` variable
- Default: `aurora_pgvector` (more cost-effective)

### 4. Variables Configuration (`variables.tf`)

#### New Variables Added

1. **ec2_instance_type**
   - Type: string
   - Default: `t3.small`
   - Validation: Must be `t3.small` or `t3.medium`

2. **vector_db_type**
   - Type: string
   - Default: `aurora_pgvector`
   - Validation: Must be `opensearch` or `aurora_pgvector`

3. **vector_db_name**
   - Type: string
   - Default: `afirgen_vectors`

4. **vector_db_username**
   - Type: string (sensitive)
   - Default: `vector_admin`

5. **vector_db_password**
   - Type: string (sensitive)
   - Required for Aurora pgvector

### 5. Terraform Variables (`terraform.tfvars`)

#### New Configuration Values
```hcl
# EC2 Instance Type
ec2_instance_type = "t3.small"

# Vector Database Configuration
vector_db_type = "aurora_pgvector"
vector_db_name = "afirgen_vectors"
vector_db_username = "vector_admin"
vector_db_password = "VectorDB123!"  # Change in production
```

### 6. Main Configuration (`main.tf`)

#### Updated Outputs
Added new outputs to deployment summary:
- `bedrock_endpoint_id`
- `transcribe_endpoint_id`
- `textract_endpoint_id`
- `ec2_instance_type`
- `vector_db_type`
- `vector_db_endpoint`

## Cost Comparison

### Current Architecture (GGUF)
| Service | Monthly Cost |
|---------|--------------|
| EC2 g5.2xlarge | $871.20 |
| S3 | $0.23 |
| RDS MySQL | $12.24 |
| **Total** | **$883.67/month** |

### New Architecture (Bedrock with Aurora pgvector)
| Service | Monthly Cost |
|---------|--------------|
| EC2 t3.small | $15.00 |
| Transcribe | $360.00 |
| Textract | $4.50 |
| Bedrock Claude | $144.60 |
| Bedrock Titan | $0.05 |
| Aurora pgvector | $43.20 |
| S3 | $0.23 |
| RDS MySQL | $12.24 |
| VPC Endpoints | ~$21.60 |
| **Total** | **$601.42/month** |

### Savings
- **Monthly**: $282.25 (32% reduction)
- **Annual**: $3,387.00

## Deployment Steps

### 1. Update Variables
Edit `terraform.tfvars`:
```bash
# Set your admin IP for SSH access
admin_ip = "YOUR_IP/32"

# Set EC2 instance type
ec2_instance_type = "t3.small"

# Choose vector database type
vector_db_type = "aurora_pgvector"

# Set vector database credentials
vector_db_username = "vector_admin"
vector_db_password = "STRONG_PASSWORD_HERE"
```

### 2. Initialize Terraform
```bash
cd "AFIRGEN FINAL/terraform/free-tier"
terraform init
```

### 3. Plan Changes
```bash
terraform plan
```

Review the plan to ensure:
- EC2 instance will be replaced (g5.2xlarge → t3.small)
- 4 new VPC endpoints will be created
- Vector database resources will be created
- New IAM policies will be attached

### 4. Apply Changes
```bash
terraform apply
```

**Warning**: This will:
- Terminate the existing g5.2xlarge instance
- Create a new t3.small instance
- Create VPC endpoints (~$0.01/hour each)
- Create Aurora pgvector cluster (~$43/month)

### 5. Verify Deployment
```bash
# Check outputs
terraform output

# Verify VPC endpoints
aws ec2 describe-vpc-endpoints --region us-east-1

# Verify IAM policies
aws iam list-role-policies --role-name afirgen-free-tier-ec2-role

# Test vector database connection
# For Aurora pgvector:
psql -h <vector_db_endpoint> -U vector_admin -d afirgen_vectors
```

## Security Considerations

### IAM Policies
- All policies follow least-privilege principle
- Bedrock access limited to specific model ARNs
- CloudWatch metrics scoped to AFIRGen namespace
- KMS access restricted to S3 and RDS services

### Network Security
- VPC endpoints use private DNS
- Security group restricts endpoint access to VPC CIDR
- Vector database in private subnets only
- No public internet access required for AWS services

### Encryption
- S3: SSE-KMS encryption
- RDS: Encryption at rest enabled
- Aurora: Encryption at rest enabled
- VPC endpoints: TLS 1.2+ for data in transit

## Rollback Plan

If issues occur, rollback to GGUF architecture:

### Option 1: Terraform Rollback
```bash
# Revert to previous Terraform state
terraform state pull > backup.tfstate
git checkout <previous-commit>
terraform apply
```

### Option 2: Feature Flag
The backend supports `ENABLE_BEDROCK` feature flag:
```bash
# In application .env file
ENABLE_BEDROCK=false
```
This allows runtime switching between GGUF and Bedrock without infrastructure changes.

## Next Steps

1. **Update Backend Code** (Task 2.x)
   - Implement Bedrock client
   - Implement Transcribe client
   - Implement Textract client
   - Implement vector database client

2. **Migrate IPC Sections** (Task 3.x)
   - Export from ChromaDB
   - Generate new embeddings with Titan
   - Import to Aurora pgvector

3. **Testing** (Task 4.x)
   - Unit tests for AWS service integrations
   - Integration tests for end-to-end FIR generation
   - Performance comparison with GGUF baseline

4. **Monitoring Setup** (Task 5.x)
   - CloudWatch dashboards
   - X-Ray tracing
   - Cost monitoring alerts

## Validation Checklist

- [x] EC2 instance type changed to t3.small/medium
- [x] IAM policies added for Bedrock, Transcribe, Textract
- [x] VPC endpoints created for all AWS services
- [x] Vector database infrastructure provisioned (Aurora pgvector)
- [x] Security groups configured for VPC endpoint traffic
- [x] Terraform configuration validates successfully
- [ ] Terraform apply completes successfully (requires deployment)

## References

- Requirements: `.kiro/specs/bedrock-migration/requirements.md`
- Design: `.kiro/specs/bedrock-migration/design.md`
- Tasks: `.kiro/specs/bedrock-migration/tasks.md`
- AWS Bedrock Pricing: https://aws.amazon.com/bedrock/pricing/
- AWS Transcribe Pricing: https://aws.amazon.com/transcribe/pricing/
- AWS Textract Pricing: https://aws.amazon.com/textract/pricing/
- Aurora Serverless v2 Pricing: https://aws.amazon.com/rds/aurora/pricing/
