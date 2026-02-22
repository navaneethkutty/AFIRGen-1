# AFIRGen Free Tier Deployment Guide

This guide walks you through deploying the AFIRGen VPC networking infrastructure on AWS Free Tier.

## Prerequisites

### 1. AWS Account Setup

1. Create an AWS account at https://aws.amazon.com/
2. Ensure your account is eligible for the AWS Free Tier (new accounts get 12 months)
3. Note your AWS Account ID

### 2. Install Required Tools

**Terraform:**
```bash
# macOS
brew install terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Windows
# Download from https://www.terraform.io/downloads
# Add to PATH
```

**AWS CLI:**
```bash
# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Windows
# Download from https://aws.amazon.com/cli/
```

### 3. Configure AWS Credentials

```bash
aws configure
```

Enter:
- AWS Access Key ID
- AWS Secret Access Key
- Default region: `us-east-1`
- Default output format: `json`

Verify configuration:
```bash
aws sts get-caller-identity
```

## Deployment Steps

### Step 1: Navigate to Terraform Directory

```bash
cd "AFIRGEN FINAL/terraform/free-tier"
```

### Step 2: Create Configuration File

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` if needed (default values are optimized for free tier).

### Step 3: Initialize Terraform

```bash
terraform init
```

This will:
- Download the AWS provider plugin
- Initialize the backend
- Prepare the working directory

Expected output:
```
Terraform has been successfully initialized!
```

### Step 4: Validate Configuration

```bash
terraform validate
```

Expected output:
```
Success! The configuration is valid.
```

### Step 5: Review the Plan

```bash
terraform plan
```

Review the resources that will be created:
- 1 VPC (10.0.0.0/16)
- 1 Internet Gateway
- 3 Subnets (1 public, 2 private)
- 2 Route Tables
- 3 Route Table Associations
- 1 S3 Gateway VPC Endpoint

**Verify:**
- All resources are in `us-east-1`
- No NAT Gateway is being created
- S3 Gateway Endpoint is included

### Step 6: Apply the Configuration

```bash
terraform apply
```

Review the plan and type `yes` to confirm.

Deployment takes approximately 2-3 minutes.

### Step 7: Verify Deployment

```bash
# Get all outputs
terraform output

# Get specific outputs
terraform output vpc_id
terraform output public_subnet_id
terraform output private_subnet_ids
terraform output s3_endpoint_id
```

### Step 8: Verify in AWS Console

1. Go to AWS Console → VPC
2. Verify VPC exists with CIDR 10.0.0.0/16
3. Check Subnets:
   - Public: 10.0.1.0/24 in us-east-1a
   - Private 1: 10.0.11.0/24 in us-east-1a
   - Private 2: 10.0.12.0/24 in us-east-1b
4. Check Internet Gateway is attached
5. Check Route Tables:
   - Public RT has route to IGW
   - Private RT has no internet route
6. Check VPC Endpoints:
   - S3 Gateway endpoint exists

## Post-Deployment

### Save Terraform State

The `terraform.tfstate` file contains the current state of your infrastructure. **Keep it safe!**

Options:
1. **Local (default)**: Keep in local directory (not recommended for production)
2. **S3 Backend**: Store in S3 bucket (recommended)

To use S3 backend, uncomment the backend configuration in `main.tf` and run:
```bash
terraform init -migrate-state
```

### Export Configuration

Save the outputs for use in subsequent tasks:

```bash
terraform output -json > outputs.json
```

### Next Steps

With VPC networking complete, proceed to:
1. **Task 1.2**: Create security groups
2. **Task 1.3**: Create S3 buckets
3. **Task 1.5**: Launch EC2 instance
4. **Task 1.6**: Create RDS instance

## Verification Checklist

- [ ] VPC created with CIDR 10.0.0.0/16
- [ ] Public subnet created (10.0.1.0/24) in us-east-1a
- [ ] Private subnet 1 created (10.0.11.0/24) in us-east-1a
- [ ] Private subnet 2 created (10.0.12.0/24) in us-east-1b
- [ ] Internet Gateway attached to VPC
- [ ] Public route table routes to Internet Gateway
- [ ] Private route table has no internet route
- [ ] S3 Gateway VPC Endpoint created
- [ ] No NAT Gateway created (cost optimization)
- [ ] All resources tagged appropriately

## Cost Verification

Verify zero cost for networking:

```bash
# Check AWS Cost Explorer (may take 24 hours to update)
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=SERVICE
```

Expected cost for VPC networking: **$0.00**

## Troubleshooting

### Issue: "Error creating VPC"

**Cause**: Insufficient permissions or region issue

**Solution**:
1. Verify AWS credentials: `aws sts get-caller-identity`
2. Check IAM permissions include VPC creation
3. Verify region is us-east-1

### Issue: "CIDR block conflicts"

**Cause**: Existing VPC with overlapping CIDR

**Solution**:
1. List existing VPCs: `aws ec2 describe-vpcs`
2. Delete conflicting VPC or use different AWS account
3. Do not modify CIDR blocks (required for free tier architecture)

### Issue: "S3 endpoint creation failed"

**Cause**: Service name incorrect or region mismatch

**Solution**:
1. Verify region: `aws configure get region`
2. List available endpoints: `aws ec2 describe-vpc-endpoint-services --region us-east-1`
3. Ensure service name is `com.amazonaws.us-east-1.s3`

### Issue: "Terraform state locked"

**Cause**: Previous operation didn't complete

**Solution**:
```bash
# Force unlock (use with caution)
terraform force-unlock <LOCK_ID>
```

## Cleanup

To destroy all networking resources:

```bash
terraform destroy
```

**Warning**: This will delete:
- VPC
- All subnets
- Internet Gateway
- Route tables
- S3 VPC Endpoint

Ensure no other resources (EC2, RDS) are using this VPC before destroying.

## Security Best Practices

1. **Never commit terraform.tfvars**: Contains sensitive configuration
2. **Protect state files**: Contains resource IDs and configuration
3. **Use IAM roles**: Avoid hardcoding credentials
4. **Enable CloudTrail**: Audit all API calls
5. **Review security groups**: Will be configured in Task 1.2

## Support

For issues or questions:
1. Check the README.md in this directory
2. Review the design document: `.kiro/specs/aws-optimization-plan/design.md`
3. Check AWS Free Tier documentation: https://aws.amazon.com/free/

## References

- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS VPC Documentation](https://docs.aws.amazon.com/vpc/)
- [AWS Free Tier](https://aws.amazon.com/free/)
- [AFIRGen Design Document](../../.kiro/specs/aws-optimization-plan/design.md)
