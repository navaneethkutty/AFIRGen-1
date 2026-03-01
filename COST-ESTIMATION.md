# Cost Estimation Guide

Detailed cost breakdown and optimization strategies for AFIRGen Bedrock architecture.

## Executive Summary

**GGUF Architecture Cost:** ~/month (g5.2xlarge GPU instance at .21/hour)

**Bedrock Architecture Cost:**
- **Optimized (Aurora pgvector):** -150/month
- **Full Features (OpenSearch):** -600/month

**Cost Savings:** 80-90% reduction compared to GPU infrastructure

---

## Cost Comparison: GGUF vs Bedrock

| Component | GGUF Architecture | Bedrock Architecture (Optimized) | Bedrock Architecture (Full) |
|-----------|-------------------|----------------------------------|----------------------------|
| **Compute** | g5.2xlarge: /mo | t3.small: /mo | t3.medium: /mo |
| **Database** | RDS db.t3.micro: /mo | RDS db.t3.micro: /mo | RDS db.t3.micro: /mo |
| **Vector DB** | ChromaDB (included) | Aurora pgvector: /mo | OpenSearch: /mo |
| **AI Services** | Self-hosted (included) | Bedrock: -50/mo | Bedrock: -50/mo |
| **Storage** | S3: /mo | S3: /mo | S3: /mo |
| **Data Transfer** | /mo | /mo (VPC endpoints) | /mo (VPC endpoints) |
| **Total** | **~/mo** | **~-132/mo** | **~-452/mo** |
| **Savings** | Baseline | **85-90%** | **50-55%** |

---

## Detailed Cost Breakdown

### 1. Compute Costs

#### EC2 Instance

**GGUF Architecture:**
- Instance: g5.2xlarge (8 vCPUs, 32 GB RAM, 1 NVIDIA A10G GPU)
- Cost: .21/hour  730 hours = **.30/month**

**Bedrock Architecture (Optimized):**
- Instance: t3.small (2 vCPUs, 2 GB RAM)
- Cost: .0208/hour  730 hours = **.18/month**

**Bedrock Architecture (Full):**
- Instance: t3.medium (2 vCPUs, 4 GB RAM)
- Cost: .0416/hour  730 hours = **.37/month**

**Savings:** 95-97% reduction in compute costs

#### Reserved Instances (1-year commitment)

**t3.small Reserved Instance:**
- On-Demand: .18/month
- 1-year RI (No Upfront): .13/month
- **Savings: 40%**

**t3.medium Reserved Instance:**
- On-Demand: .37/month
- 1-year RI (No Upfront): .25/month
- **Savings: 40%**

### 2. Database Costs

#### MySQL RDS

**Configuration:**
- Instance: db.t3.micro (2 vCPUs, 1 GB RAM)
- Storage: 20 GB General Purpose SSD (gp3)
- Backup: 7 days retention

**Cost Breakdown:**
- Instance: .017/hour  730 hours = .41/month
- Storage: 20 GB  .115/GB = .30/month
- Backup: 20 GB  .095/GB = .90/month
- **Total: .61/month**

**Optimization:**
- Use db.t3.micro (sufficient for demo)
- Enable Multi-AZ only for production (+100% cost)
- Use Aurora Serverless v2 for auto-scaling (variable cost)

### 3. Vector Database Costs

#### Option A: OpenSearch Serverless

**Configuration:**
- Minimum: 2 OCU (OpenSearch Compute Units)
- OCU includes: compute, storage, data transfer

**Cost:**
- 2 OCU  .24/OCU-hour  730 hours = **.40/month**

**Pros:**
- Fully managed, no maintenance
- Auto-scaling
- Fast for large datasets

**Cons:**
- Expensive for small workloads
- Minimum 2 OCU required

#### Option B: Aurora PostgreSQL with pgvector (Recommended)

**Configuration:**
- Aurora Serverless v2
- Minimum: 0.5 ACU (Aurora Capacity Units)
- Maximum: 2 ACU
- Storage: 10 GB

**Cost:**
- Compute: 0.5 ACU  .12/ACU-hour  730 hours = .80/month
- Storage: 10 GB  .10/GB = .00/month
- I/O: 1M requests  .20/1M = .20/month
- Backup: 10 GB  .021/GB = .21/month
- **Total: .21/month**

**Pros:**
- Cost-effective for small-medium workloads
- PostgreSQL compatibility
- Auto-scaling

**Cons:**
- Requires PostgreSQL knowledge
- Manual scaling configuration

**Recommendation:** Use Aurora pgvector for cost optimization (saves ~/month)

### 4. AI Service Costs

#### Amazon Bedrock

**Claude 3 Sonnet Pricing:**
- Input tokens: .003 per 1K tokens
- Output tokens: .015 per 1K tokens

**Titan Embeddings Pricing:**
- .0001 per 1K tokens

**Usage Estimation (100 FIRs/month):**

**Per FIR:**
- Legal narrative generation: 500 input + 200 output tokens
- Metadata extraction: 300 input + 100 output tokens
- FIR generation: 1000 input + 800 output tokens
- Embeddings: 100 tokens

**Total per FIR:**
- Input tokens: 1800  .003/1K = .0054
- Output tokens: 1100  .015/1K = .0165
- Embeddings: 100  .0001/1K = .00001
- **Total: .022 per FIR**

**Monthly Cost (100 FIRs):**
- 100 FIRs  .022 = **.20/month**

**Monthly Cost (1000 FIRs):**
- 1000 FIRs  .022 = **.00/month**

**Monthly Cost (5000 FIRs):**
- 5000 FIRs  .022 = **.00/month**

#### Amazon Transcribe

**Pricing:** .024 per minute (first 250K minutes/month)

**Usage Estimation:**
- Average audio length: 5 minutes
- 50 audio FIRs/month

**Monthly Cost:**
- 50 FIRs  5 minutes  .024/min = **.00/month**

**Monthly Cost (500 audio FIRs):**
- 500 FIRs  5 minutes  .024/min = **.00/month**

#### Amazon Textract

**Pricing:** .0015 per page (DetectDocumentText)

**Usage Estimation:**
- Average document: 2 pages
- 50 document FIRs/month

**Monthly Cost:**
- 50 FIRs  2 pages  .0015/page = **.15/month**

**Monthly Cost (500 document FIRs):**
- 500 FIRs  2 pages  .0015/page = **.50/month**

### 5. Storage Costs

#### S3 Storage

**Configuration:**
- Temporary files (audio, images)
- Lifecycle policy: Delete after 7 days
- Average storage: 10 GB

**Cost:**
- Storage: 10 GB  .023/GB = .23/month
- PUT requests: 1000  .005/1K = .005/month
- GET requests: 2000  .0004/1K = .0008/month
- **Total: .24/month**

#### EBS Storage

**Configuration:**
- EC2 root volume: 30 GB gp3
- Application data: 20 GB gp3

**Cost:**
- 50 GB  .08/GB = **.00/month**

### 6. Data Transfer Costs

#### Without VPC Endpoints

**Data Transfer Out:**
- Bedrock: 10 GB/month  .09/GB = .90/month
- Transcribe: 5 GB/month  .09/GB = .45/month
- Textract: 2 GB/month  .09/GB = .18/month
- **Total: .53/month**

#### With VPC Endpoints (Recommended)

**VPC Endpoint Costs:**
- Bedrock endpoint: .01/hour  730 hours = .30/month
- Transcribe endpoint: .01/hour  730 hours = .30/month
- Textract endpoint: .01/hour  730 hours = .30/month
- S3 endpoint: Free (Gateway type)
- **Total: .90/month**

**Data Transfer:** Free (within VPC)

**Net Cost:** .90/month (vs .53/month without endpoints)

**Recommendation:** Use VPC endpoints for high-volume workloads (>100 GB/month data transfer)

### 7. Monitoring Costs

#### CloudWatch

**Free Tier:**
- 10 custom metrics
- 5 GB log ingestion
- 5 GB log storage
- 1M API requests

**Typical Usage:**
- 15 custom metrics: 5  .30/metric = .50/month
- 10 GB log ingestion: 5 GB  .50/GB = .50/month
- 10 GB log storage: 5 GB  .03/GB = .15/month
- **Total: .15/month**

#### X-Ray

**Free Tier:**
- 100K traces/month
- First 1M traces retrieved/scanned

**Typical Usage:**
- 200K traces: 100K  .000005/trace = .50/month
- **Total: .50/month**

---

## Total Monthly Cost Estimates

### Scenario 1: Low Volume (100 FIRs/month)

**Optimized Configuration (Aurora pgvector):**
- EC2 t3.small: .18
- RDS MySQL: .61
- Aurora pgvector: .21
- Bedrock (100 FIRs): .20
- Transcribe (50 audio): .00
- Textract (50 docs): .15
- S3: .24
- EBS: .00
- CloudWatch: .15
- X-Ray: .50
- **Total: .24/month**

**Full Configuration (OpenSearch):**
- EC2 t3.medium: .37
- RDS MySQL: .61
- OpenSearch: .40
- Bedrock (100 FIRs): .20
- Transcribe (50 audio): .00
- Textract (50 docs): .15
- S3: .24
- EBS: .00
- VPC Endpoints: .90
- CloudWatch: .15
- X-Ray: .50
- **Total: .52/month**

### Scenario 2: Medium Volume (1000 FIRs/month)

**Optimized Configuration (Aurora pgvector):**
- EC2 t3.small: .18
- RDS MySQL: .61
- Aurora pgvector: .21
- Bedrock (1000 FIRs): .00
- Transcribe (500 audio): .00
- Textract (500 docs): .50
- S3: .24
- EBS: .00
- CloudWatch: .15
- X-Ray: .50
- **Total: .39/month**

**Full Configuration (OpenSearch):**
- EC2 t3.medium: .37
- RDS MySQL: .61
- OpenSearch: .40
- Bedrock (1000 FIRs): .00
- Transcribe (500 audio): .00
- Textract (500 docs): .50
- S3: .24
- EBS: .00
- VPC Endpoints: .90
- CloudWatch: .15
- X-Ray: .50
- **Total: .67/month**

### Scenario 3: High Volume (5000 FIRs/month)

**Optimized Configuration (Aurora pgvector):**
- EC2 t3.medium: .37
- RDS MySQL: .61
- Aurora pgvector (scaled): .00
- Bedrock (5000 FIRs): .00
- Transcribe (2500 audio): .00
- Textract (2500 docs): .50
- S3: .00
- EBS: .00
- VPC Endpoints: .90
- CloudWatch: .00
- X-Ray: .00
- **Total: .38/month**

**Full Configuration (OpenSearch):**
- EC2 t3.medium: .37
- RDS MySQL: .61
- OpenSearch (4 OCU): .80
- Bedrock (5000 FIRs): .00
- Transcribe (2500 audio): .00
- Textract (2500 docs): .50
- S3: .00
- EBS: .00
- VPC Endpoints: .90
- CloudWatch: .00
- X-Ray: .00
- **Total: .18/month**

---

## Cost Optimization Strategies

### 1. Use Aurora pgvector Instead of OpenSearch

**Savings:** ~/month (low volume) to ~/month (high volume)

**Implementation:**
`ash
# In terraform.tfvars
vector_db_type = aurora_pgvector

# Apply changes
terraform apply
`

### 2. Enable Caching

**Savings:** 30-50% reduction in Bedrock API calls

**Implementation:**
`ash
# In .env.bedrock
ENABLE_CACHING=true
CACHE_MAX_SIZE=100
`

**Impact:**
- 1000 FIRs/month: Save -11/month
- 5000 FIRs/month: Save -55/month

### 3. Use Reserved Instances

**Savings:** 40% on EC2 and RDS costs

**Implementation:**
- AWS Console  EC2  Reserved Instances
- Purchase 1-year No Upfront RI

**Impact:**
- EC2 t3.small: Save /month
- EC2 t3.medium: Save /month
- RDS db.t3.micro: Save /month

### 4. Optimize Bedrock Prompts

**Strategies:**
- Use shorter system prompts
- Reduce max_tokens where possible
- Use lower temperature for deterministic outputs
- Consider Claude 3 Haiku for simple tasks (5x cheaper)

**Savings:** 20-30% on Bedrock costs

### 5. Batch Transcribe Requests

**Strategy:**
- Process multiple audio files in batch
- Use asynchronous processing
- Cache transcripts

**Savings:** Reduce processing time, no direct cost savings

### 6. Optimize S3 Lifecycle

**Strategy:**
- Delete temporary files after 1 day (instead of 7)
- Use S3 Intelligent-Tiering for backups

**Savings:** Minimal (~.10/month)

### 7. Use Spot Instances (Development Only)

**Savings:** 70-90% on EC2 costs

**Warning:** Not recommended for production (can be terminated)

---

## Cost Monitoring

### Set Up AWS Budgets

`ash
# Create monthly budget alert
aws budgets create-budget   --account-id <ACCOUNT_ID>   --budget file://budget.json

# budget.json:
{
  BudgetName: AFIRGen-Monthly,
  BudgetLimit: {Amount: 200, Unit: USD},
  TimeUnit: MONTHLY,
  BudgetType: COST
}
`

### CloudWatch Cost Metrics

**Custom Metrics:**
- Bedrock token usage
- Transcribe minutes
- Textract pages
- Vector database operations

**Dashboards:**
- AWS Console  CloudWatch  Dashboards  afirgen-cost-dashboard

### Cost Explorer

**View Cost Breakdown:**
- AWS Console  Cost Explorer
- Group by: Service
- Filter by: Tag (Project=AFIRGen)

---

## Summary

**Recommended Configuration for Cost Optimization:**
- **Compute:** EC2 t3.small with 1-year RI
- **Vector DB:** Aurora pgvector
- **Caching:** Enabled
- **VPC Endpoints:** Only for high volume (>100 GB/month)

**Expected Monthly Cost:**
- **Low Volume (100 FIRs):** -95
- **Medium Volume (1000 FIRs):** -170
- **High Volume (5000 FIRs):** -600

**Cost Savings vs GGUF:**
- **Low Volume:** 90% savings
- **Medium Volume:** 85% savings
- **High Volume:** 35-50% savings

**Break-Even Point:**
- Bedrock becomes more expensive than GGUF at ~10,000 FIRs/month
- For very high volumes, consider hybrid approach or self-hosted models
