# AFIRGen Free Tier - Quick Start Guide

Get your AFIRGen VPC networking infrastructure up and running in 5 minutes.

## Prerequisites

- AWS Account (free tier eligible)
- AWS CLI installed and configured
- Terraform >= 1.0 installed

## Quick Deploy

```bash
# 1. Navigate to directory
cd "AFIRGEN FINAL/terraform/free-tier"

# 2. Initialize Terraform
terraform init

# 3. Review what will be created
terraform plan

# 4. Deploy infrastructure
terraform apply -auto-approve

# 5. Verify deployment
terraform output
```

## What Gets Created

✅ **VPC** (10.0.0.0/16)
- DNS hostnames and support enabled
- Free tier compliant

✅ **Public Subnet** (10.0.1.0/24)
- For EC2 instance
- Auto-assign public IP enabled
- Internet access via Internet Gateway

✅ **Private Subnets** (10.0.11.0/24, 10.0.12.0/24)
- For RDS MySQL instance
- No direct internet access
- Two AZs for RDS subnet group requirement

✅ **Internet Gateway**
- Provides internet access for public subnet
- Free tier service

✅ **S3 Gateway VPC Endpoint**
- Free S3 access from all subnets
- No data transfer charges

❌ **NAT Gateway** (NOT created)
- Saves $32/month
- EC2 will be in public subnet instead

## Verify Deployment

### Option 1: Using Terraform

```bash
terraform output
```

### Option 2: Using Validation Script

**Linux/macOS:**
```bash
chmod +x validate-deployment.sh
./validate-deployment.sh
```

**Windows:**
```powershell
.\validate-deployment.ps1
```

### Option 3: AWS Console

1. Go to AWS Console → VPC
2. Find VPC with name "afirgen-free-tier-vpc"
3. Verify:
   - CIDR: 10.0.0.0/16
   - 3 subnets (1 public, 2 private)
   - Internet Gateway attached
   - S3 endpoint exists
   - No NAT Gateway

## Cost Verification

All networking resources are **FREE**:

```bash
# Check costs (may take 24 hours to update)
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics UnblendedCost
```

Expected cost: **$0.00**

## Next Steps

1. **Task 1.2**: Create security groups
2. **Task 1.3**: Create S3 buckets
3. **Task 1.5**: Launch EC2 instance
4. **Task 1.6**: Create RDS instance

## Troubleshooting

### "Error creating VPC"
- Check AWS credentials: `aws sts get-caller-identity`
- Verify region is us-east-1: `aws configure get region`

### "CIDR block conflicts"
- You may have an existing VPC with overlapping CIDR
- Use a different AWS account or delete the conflicting VPC

### "Terraform not found"
- Install Terraform: https://www.terraform.io/downloads

## Cleanup

To remove all resources:

```bash
terraform destroy -auto-approve
```

**Warning**: Only do this if you're sure you want to delete everything!

## Documentation

- Full deployment guide: [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md)
- Architecture details: [README.md](README.md)
- Design document: [../../.kiro/specs/aws-optimization-plan/design.md](../../.kiro/specs/aws-optimization-plan/design.md)

## Support

For issues:
1. Check the [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md) troubleshooting section
2. Review AWS Free Tier limits: https://aws.amazon.com/free/
3. Verify Terraform configuration: `terraform validate`
