# AFIRGen Free Tier VPC Deployment Validation Script (PowerShell)
# This script verifies that the VPC networking infrastructure is correctly deployed

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "AFIRGen Free Tier VPC Validation" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if AWS CLI is installed
try {
    $null = aws --version
    Write-Host "✓ AWS CLI is installed" -ForegroundColor Green
} catch {
    Write-Host "✗ AWS CLI is not installed" -ForegroundColor Red
    exit 1
}

# Check if Terraform is installed
try {
    $null = terraform version
    Write-Host "✓ Terraform is installed" -ForegroundColor Green
} catch {
    Write-Host "✗ Terraform is not installed" -ForegroundColor Red
    exit 1
}

# Check AWS credentials
try {
    $null = aws sts get-caller-identity
    Write-Host "✓ AWS credentials are configured" -ForegroundColor Green
} catch {
    Write-Host "✗ AWS credentials are not configured" -ForegroundColor Red
    exit 1
}

$AccountId = aws sts get-caller-identity --query Account --output text
$Region = aws configure get region
Write-Host "  Account ID: $AccountId"
Write-Host "  Region: $Region"
Write-Host ""

# Get Terraform outputs
Write-Host "Retrieving Terraform outputs..."
try {
    $VpcId = terraform output -raw vpc_id 2>$null
    $PublicSubnetId = terraform output -raw public_subnet_id 2>$null
    $S3EndpointId = terraform output -raw s3_endpoint_id 2>$null
} catch {
    Write-Host "✗ Failed to retrieve Terraform outputs" -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrEmpty($VpcId)) {
    Write-Host "✗ VPC not found. Has Terraform been applied?" -ForegroundColor Red
    exit 1
}
Write-Host "✓ VPC found: $VpcId" -ForegroundColor Green
Write-Host ""

# Validate VPC CIDR
Write-Host "Validating VPC configuration..."
$VpcCidr = aws ec2 describe-vpcs --vpc-ids $VpcId --query 'Vpcs[0].CidrBlock' --output text
if ($VpcCidr -eq "10.0.0.0/16") {
    Write-Host "✓ VPC CIDR is correct: $VpcCidr" -ForegroundColor Green
} else {
    Write-Host "✗ VPC CIDR is incorrect: $VpcCidr (expected 10.0.0.0/16)" -ForegroundColor Red
}

# Validate DNS settings
$DnsHostnames = aws ec2 describe-vpc-attribute --vpc-id $VpcId --attribute enableDnsHostnames --query 'EnableDnsHostnames.Value' --output text
$DnsSupport = aws ec2 describe-vpc-attribute --vpc-id $VpcId --attribute enableDnsSupport --query 'EnableDnsSupport.Value' --output text
if ($DnsHostnames -eq "True" -and $DnsSupport -eq "True") {
    Write-Host "✓ DNS hostnames and support are enabled" -ForegroundColor Green
} else {
    Write-Host "✗ DNS settings are incorrect" -ForegroundColor Red
}
Write-Host ""

# Validate subnets
Write-Host "Validating subnets..."
$Subnets = aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VpcId" --query 'Subnets[*].[SubnetId,CidrBlock,AvailabilityZone,MapPublicIpOnLaunch]' --output text

$PublicSubnetCount = ($Subnets | Select-String "10.0.1.0/24").Matches.Count
$PrivateSubnet1Count = ($Subnets | Select-String "10.0.11.0/24").Matches.Count
$PrivateSubnet2Count = ($Subnets | Select-String "10.0.12.0/24").Matches.Count

if ($PublicSubnetCount -eq 1) {
    Write-Host "✓ Public subnet (10.0.1.0/24) exists" -ForegroundColor Green
} else {
    Write-Host "✗ Public subnet not found" -ForegroundColor Red
}

if ($PrivateSubnet1Count -eq 1) {
    Write-Host "✓ Private subnet 1 (10.0.11.0/24) exists" -ForegroundColor Green
} else {
    Write-Host "✗ Private subnet 1 not found" -ForegroundColor Red
}

if ($PrivateSubnet2Count -eq 1) {
    Write-Host "✓ Private subnet 2 (10.0.12.0/24) exists" -ForegroundColor Green
} else {
    Write-Host "✗ Private subnet 2 not found" -ForegroundColor Red
}
Write-Host ""

# Validate Internet Gateway
Write-Host "Validating Internet Gateway..."
$IgwCount = aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$VpcId" --query 'InternetGateways | length(@)' --output text
if ($IgwCount -eq "1") {
    Write-Host "✓ Internet Gateway is attached" -ForegroundColor Green
} else {
    Write-Host "✗ Internet Gateway not found or multiple IGWs attached" -ForegroundColor Red
}
Write-Host ""

# Validate NAT Gateway (should NOT exist)
Write-Host "Validating NAT Gateway (should not exist)..."
$NatCount = aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=$VpcId" "Name=state,Values=available" --query 'NatGateways | length(@)' --output text
if ($NatCount -eq "0") {
    Write-Host "✓ No NAT Gateway (cost optimization confirmed)" -ForegroundColor Green
} else {
    Write-Host "⚠ NAT Gateway found (this will incur costs!)" -ForegroundColor Yellow
}
Write-Host ""

# Validate S3 VPC Endpoint
Write-Host "Validating S3 VPC Endpoint..."
if (-not [string]::IsNullOrEmpty($S3EndpointId)) {
    $EndpointState = aws ec2 describe-vpc-endpoints --vpc-endpoint-ids $S3EndpointId --query 'VpcEndpoints[0].State' --output text
    if ($EndpointState -eq "available") {
        Write-Host "✓ S3 Gateway VPC Endpoint is available" -ForegroundColor Green
    } else {
        Write-Host "✗ S3 VPC Endpoint state: $EndpointState" -ForegroundColor Red
    }
} else {
    Write-Host "✗ S3 VPC Endpoint not found" -ForegroundColor Red
}
Write-Host ""

# Validate Route Tables
Write-Host "Validating Route Tables..."
$PublicRt = aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VpcId" "Name=association.subnet-id,Values=$PublicSubnetId" --query 'RouteTables[0].RouteTableId' --output text
if (-not [string]::IsNullOrEmpty($PublicRt)) {
    $IgwRoute = aws ec2 describe-route-tables --route-table-ids $PublicRt --query 'RouteTables[0].Routes[?DestinationCidrBlock==`0.0.0.0/0`].GatewayId' --output text
    if ($IgwRoute -like "igw-*") {
        Write-Host "✓ Public route table has route to Internet Gateway" -ForegroundColor Green
    } else {
        Write-Host "✗ Public route table missing IGW route" -ForegroundColor Red
    }
}
Write-Host ""

# Summary
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Validation Summary" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "VPC Configuration:"
Write-Host "  VPC ID: $VpcId"
Write-Host "  CIDR: $VpcCidr"
Write-Host "  Region: $Region"
Write-Host ""
Write-Host "Cost Optimization:"
Write-Host "  NAT Gateway: Not deployed (saves `$32/month)"
Write-Host "  S3 Endpoint: Gateway type (free)"
Write-Host ""
Write-Host "Next Steps:"
Write-Host "  1. Create security groups (Task 1.2)"
Write-Host "  2. Create S3 buckets (Task 1.3)"
Write-Host "  3. Launch EC2 instance (Task 1.5)"
Write-Host "  4. Create RDS instance (Task 1.6)"
Write-Host ""
Write-Host "Validation complete!" -ForegroundColor Green
