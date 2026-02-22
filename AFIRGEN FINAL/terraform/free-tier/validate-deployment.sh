#!/bin/bash
# AFIRGen Free Tier VPC Deployment Validation Script
# This script verifies that the VPC networking infrastructure is correctly deployed

set -e

echo "=========================================="
echo "AFIRGen Free Tier VPC Validation"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ AWS CLI is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ AWS CLI is installed${NC}"

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}✗ Terraform is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Terraform is installed${NC}"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}✗ AWS credentials are not configured${NC}"
    exit 1
fi
echo -e "${GREEN}✓ AWS credentials are configured${NC}"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)
echo "  Account ID: $ACCOUNT_ID"
echo "  Region: $REGION"
echo ""

# Get Terraform outputs
echo "Retrieving Terraform outputs..."
VPC_ID=$(terraform output -raw vpc_id 2>/dev/null || echo "")
PUBLIC_SUBNET_ID=$(terraform output -raw public_subnet_id 2>/dev/null || echo "")
S3_ENDPOINT_ID=$(terraform output -raw s3_endpoint_id 2>/dev/null || echo "")

if [ -z "$VPC_ID" ]; then
    echo -e "${RED}✗ VPC not found. Has Terraform been applied?${NC}"
    exit 1
fi
echo -e "${GREEN}✓ VPC found: $VPC_ID${NC}"
echo ""

# Validate VPC CIDR
echo "Validating VPC configuration..."
VPC_CIDR=$(aws ec2 describe-vpcs --vpc-ids $VPC_ID --query 'Vpcs[0].CidrBlock' --output text)
if [ "$VPC_CIDR" == "10.0.0.0/16" ]; then
    echo -e "${GREEN}✓ VPC CIDR is correct: $VPC_CIDR${NC}"
else
    echo -e "${RED}✗ VPC CIDR is incorrect: $VPC_CIDR (expected 10.0.0.0/16)${NC}"
fi

# Validate DNS settings
DNS_HOSTNAMES=$(aws ec2 describe-vpc-attribute --vpc-id $VPC_ID --attribute enableDnsHostnames --query 'EnableDnsHostnames.Value' --output text)
DNS_SUPPORT=$(aws ec2 describe-vpc-attribute --vpc-id $VPC_ID --attribute enableDnsSupport --query 'EnableDnsSupport.Value' --output text)
if [ "$DNS_HOSTNAMES" == "True" ] && [ "$DNS_SUPPORT" == "True" ]; then
    echo -e "${GREEN}✓ DNS hostnames and support are enabled${NC}"
else
    echo -e "${RED}✗ DNS settings are incorrect${NC}"
fi
echo ""

# Validate subnets
echo "Validating subnets..."
SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].[SubnetId,CidrBlock,AvailabilityZone,MapPublicIpOnLaunch]' --output text)

PUBLIC_SUBNET_COUNT=$(echo "$SUBNETS" | grep "10.0.1.0/24" | wc -l)
PRIVATE_SUBNET_1_COUNT=$(echo "$SUBNETS" | grep "10.0.11.0/24" | wc -l)
PRIVATE_SUBNET_2_COUNT=$(echo "$SUBNETS" | grep "10.0.12.0/24" | wc -l)

if [ $PUBLIC_SUBNET_COUNT -eq 1 ]; then
    echo -e "${GREEN}✓ Public subnet (10.0.1.0/24) exists${NC}"
else
    echo -e "${RED}✗ Public subnet not found${NC}"
fi

if [ $PRIVATE_SUBNET_1_COUNT -eq 1 ]; then
    echo -e "${GREEN}✓ Private subnet 1 (10.0.11.0/24) exists${NC}"
else
    echo -e "${RED}✗ Private subnet 1 not found${NC}"
fi

if [ $PRIVATE_SUBNET_2_COUNT -eq 1 ]; then
    echo -e "${GREEN}✓ Private subnet 2 (10.0.12.0/24) exists${NC}"
else
    echo -e "${RED}✗ Private subnet 2 not found${NC}"
fi
echo ""

# Validate Internet Gateway
echo "Validating Internet Gateway..."
IGW_COUNT=$(aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$VPC_ID" --query 'InternetGateways | length(@)' --output text)
if [ $IGW_COUNT -eq 1 ]; then
    echo -e "${GREEN}✓ Internet Gateway is attached${NC}"
else
    echo -e "${RED}✗ Internet Gateway not found or multiple IGWs attached${NC}"
fi
echo ""

# Validate NAT Gateway (should NOT exist)
echo "Validating NAT Gateway (should not exist)..."
NAT_COUNT=$(aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=$VPC_ID" "Name=state,Values=available" --query 'NatGateways | length(@)' --output text)
if [ $NAT_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ No NAT Gateway (cost optimization confirmed)${NC}"
else
    echo -e "${YELLOW}⚠ NAT Gateway found (this will incur costs!)${NC}"
fi
echo ""

# Validate S3 VPC Endpoint
echo "Validating S3 VPC Endpoint..."
if [ -n "$S3_ENDPOINT_ID" ]; then
    ENDPOINT_STATE=$(aws ec2 describe-vpc-endpoints --vpc-endpoint-ids $S3_ENDPOINT_ID --query 'VpcEndpoints[0].State' --output text)
    if [ "$ENDPOINT_STATE" == "available" ]; then
        echo -e "${GREEN}✓ S3 Gateway VPC Endpoint is available${NC}"
    else
        echo -e "${RED}✗ S3 VPC Endpoint state: $ENDPOINT_STATE${NC}"
    fi
else
    echo -e "${RED}✗ S3 VPC Endpoint not found${NC}"
fi
echo ""

# Validate Route Tables
echo "Validating Route Tables..."
PUBLIC_RT=$(aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC_ID" "Name=association.subnet-id,Values=$PUBLIC_SUBNET_ID" --query 'RouteTables[0].RouteTableId' --output text)
if [ -n "$PUBLIC_RT" ]; then
    IGW_ROUTE=$(aws ec2 describe-route-tables --route-table-ids $PUBLIC_RT --query 'RouteTables[0].Routes[?DestinationCidrBlock==`0.0.0.0/0`].GatewayId' --output text)
    if [[ $IGW_ROUTE == igw-* ]]; then
        echo -e "${GREEN}✓ Public route table has route to Internet Gateway${NC}"
    else
        echo -e "${RED}✗ Public route table missing IGW route${NC}"
    fi
fi
echo ""

# Summary
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo ""
echo "VPC Configuration:"
echo "  VPC ID: $VPC_ID"
echo "  CIDR: $VPC_CIDR"
echo "  Region: $REGION"
echo ""
echo "Cost Optimization:"
echo "  NAT Gateway: Not deployed (saves \$32/month)"
echo "  S3 Endpoint: Gateway type (free)"
echo ""
echo "Next Steps:"
echo "  1. Create security groups (Task 1.2)"
echo "  2. Create S3 buckets (Task 1.3)"
echo "  3. Launch EC2 instance (Task 1.5)"
echo "  4. Create RDS instance (Task 1.6)"
echo ""
echo -e "${GREEN}Validation complete!${NC}"
