# AFIRGen Free Tier Infrastructure

This Terraform configuration deploys the AFIRGen system using only AWS Free Tier services to achieve zero-cost deployment during the 12-month free tier period.

## Architecture Overview

### Network Architecture (Task 1.1)

**VPC Configuration:**
- VPC CIDR: `10.0.0.0/16`
- Region: `us-east-1`
- DNS hostnames and DNS support enabled

**Subnets:**
- **Public Subnet**: `10.0.1.0/24` in `us-east-1a`
  - For EC2 instance running all application services
  - Internet access via Internet Gateway
  - Auto-assign public IP enabled
  
- **Private Subnet 1**: `10.0.11.0/24` in `us-east-1a`
  - For RDS MySQL instance
  - No direct internet access
  
- **Private Subnet 2**: `10.0.12.0/24` in `us-east-1b`
  - Required for RDS subnet group (multi-AZ requirement)
  - No direct internet access

**Networking Components:**
- **Internet Gateway**: Provides internet access for public subnet
- **S3 Gateway VPC Endpoint**: Free S3 access from all subnets (no data transfer charges)
- **NO NAT Gateway**: Cost optimization - saves $32/month

**Route Tables:**
- **Public Route Table**: Routes 0.0.0.0/0 to Internet Gateway
- **Private Route Table**: No internet route (RDS doesn't need internet access)

### Cost Optimization Strategy

This configuration implements several cost-saving measures:

1. **No NAT Gateway**: EC2 instance is in public subnet with Elastic IP instead of private subnet with NAT Gateway
2. **S3 Gateway Endpoint**: Free S3 access without data transfer charges
3. **Single AZ for EC2**: Only one EC2 instance in one AZ (free tier: 750 hours/month)
4. **Minimal Subnets**: Only the subnets required for functionality

### Requirements Satisfied

- **Requirement 13.1**: EC2 instance in public subnet with Elastic IP
- **Requirement 13.3**: S3 Gateway VPC Endpoint for free S3 access from private subnets

## Prerequisites

1. AWS Account (free tier eligible)
2. Terraform >= 1.0
3. AWS CLI configured with credentials

## Deployment

### Step 1: Initialize Terraform

```bash
cd "AFIRGEN FINAL/terraform/free-tier"
terraform init
```

### Step 2: Review the Plan

```bash
terraform plan
```

Expected resources to be created:
- 1 VPC
- 1 Internet Gateway
- 3 Subnets (1 public, 2 private)
- 2 Route Tables
- 3 Route Table Associations
- 1 S3 Gateway VPC Endpoint

### Step 3: Apply the Configuration

```bash
terraform apply
```

Review the changes and type `yes` to confirm.

### Step 4: Verify Deployment

```bash
# Get VPC ID
terraform output vpc_id

# Get subnet IDs
terraform output public_subnet_id
terraform output private_subnet_ids

# Get S3 endpoint ID
terraform output s3_endpoint_id
```

## Outputs

After deployment, Terraform will output:

- `vpc_id`: VPC identifier
- `vpc_cidr`: VPC CIDR block (10.0.0.0/16)
- `public_subnet_id`: Public subnet for EC2
- `public_subnet_cidr`: Public subnet CIDR (10.0.1.0/24)
- `private_subnet_ids`: Private subnets for RDS
- `private_subnet_cidrs`: Private subnet CIDRs
- `internet_gateway_id`: Internet Gateway identifier
- `s3_endpoint_id`: S3 Gateway VPC Endpoint identifier

## Network Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ VPC: 10.0.0.0/16                                            │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Public Subnet: 10.0.1.0/24 (us-east-1a)           │    │
│  │                                                    │    │
│  │  ┌──────────────────────────────────────┐        │    │
│  │  │ EC2 t2.micro                         │        │    │
│  │  │ - Main Backend                       │        │    │
│  │  │ - GGUF Server                        │        │    │
│  │  │ - ASR/OCR Server                     │        │    │
│  │  │ - Nginx                              │        │    │
│  │  └──────────────────────────────────────┘        │    │
│  │                    │                              │    │
│  └────────────────────┼──────────────────────────────┘    │
│                       │                                    │
│                       │ Internet Gateway                   │
│                       ▼                                    │
│                   Internet                                 │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Private Subnet 1: 10.0.11.0/24 (us-east-1a)       │    │
│  │                                                    │    │
│  │  ┌──────────────────────────────────────┐        │    │
│  │  │ RDS db.t3.micro MySQL                │        │    │
│  │  │ - 20GB storage                       │        │    │
│  │  │ - No public access                   │        │    │
│  │  └──────────────────────────────────────┘        │    │
│  │                                                    │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Private Subnet 2: 10.0.12.0/24 (us-east-1b)       │    │
│  │ (Required for RDS subnet group)                   │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  S3 Gateway VPC Endpoint (Free)                            │
│  └─> Provides free S3 access from all subnets              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Security Considerations

1. **Public Subnet**: EC2 instance is in public subnet with security groups controlling access
2. **Private Subnets**: RDS is isolated in private subnets with no internet access
3. **Security Groups**: Will be configured in subsequent tasks to restrict access
4. **S3 Endpoint**: Gateway endpoint doesn't expose services to internet

## Next Steps

After VPC networking is set up, the following tasks will be completed:

1. **Task 1.2**: Create security groups for EC2 and RDS
2. **Task 1.3**: Create S3 buckets with lifecycle policies
3. **Task 1.5**: Launch EC2 t2.micro instance
4. **Task 1.6**: Create RDS db.t3.micro MySQL instance

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will delete all networking infrastructure. Ensure no other resources depend on this VPC before destroying.

## Free Tier Compliance

This configuration uses only free tier services:

- ✅ VPC: Free
- ✅ Subnets: Free
- ✅ Internet Gateway: Free
- ✅ Route Tables: Free
- ✅ S3 Gateway VPC Endpoint: Free
- ✅ No NAT Gateway: Avoided ($32/month cost)

**Total Monthly Cost**: $0.00

## Troubleshooting

### Issue: Terraform fails to create VPC

**Solution**: Ensure AWS credentials are configured correctly:
```bash
aws configure
aws sts get-caller-identity
```

### Issue: S3 endpoint creation fails

**Solution**: Verify the region is us-east-1 and the service name is correct:
```bash
aws ec2 describe-vpc-endpoint-services --region us-east-1 | grep s3
```

### Issue: Subnet CIDR conflicts

**Solution**: This configuration uses fixed CIDRs per the design document. If you have existing VPCs with overlapping CIDRs, you'll need to use a different AWS account or region.

## References

- Design Document: `.kiro/specs/aws-optimization-plan/design.md`
- Requirements: `.kiro/specs/aws-optimization-plan/requirements.md`
- Tasks: `.kiro/specs/aws-optimization-plan/tasks.md`
- AWS Free Tier: https://aws.amazon.com/free/
