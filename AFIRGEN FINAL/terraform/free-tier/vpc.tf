# AFIRGen Free Tier VPC Configuration
# Requirements: 13.1, 13.3
# 
# This configuration creates a simplified network architecture to avoid NAT Gateway costs:
# - VPC with CIDR 10.0.0.0/16
# - Public subnet (10.0.1.0/24) for EC2 instance
# - Private subnets (10.0.11.0/24, 10.0.12.0/24) for RDS
# - Internet Gateway for public subnet
# - S3 Gateway VPC Endpoint for free S3 access from private subnets
# - NO NAT Gateway (saves $32/month)

# ============================================================================
# VPC
# ============================================================================
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "afirgen-free-tier-vpc"
    Environment = "free-tier"
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# Internet Gateway
# ============================================================================
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "afirgen-free-tier-igw"
    Environment = "free-tier"
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# Public Subnet (for EC2 instance)
# ============================================================================
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = {
    Name        = "afirgen-free-tier-public-subnet"
    Type        = "Public"
    Environment = "free-tier"
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# Private Subnets (for RDS - requires 2 AZs for subnet group)
# ============================================================================
resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "${var.aws_region}a"

  tags = {
    Name        = "afirgen-free-tier-private-subnet-1"
    Type        = "Private"
    Purpose     = "RDS"
    Environment = "free-tier"
    ManagedBy   = "Terraform"
  }
}

resource "aws_subnet" "private_2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.12.0/24"
  availability_zone = "${var.aws_region}b"

  tags = {
    Name        = "afirgen-free-tier-private-subnet-2"
    Type        = "Private"
    Purpose     = "RDS"
    Environment = "free-tier"
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# Route Tables
# ============================================================================

# Public Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "afirgen-free-tier-public-rt"
    Type        = "Public"
    Environment = "free-tier"
    ManagedBy   = "Terraform"
  }
}

# Public Route to Internet Gateway
resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

# Associate Public Subnet with Public Route Table
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Private Route Table (no NAT Gateway - cost optimization)
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "afirgen-free-tier-private-rt"
    Type        = "Private"
    Environment = "free-tier"
    ManagedBy   = "Terraform"
  }
}

# Associate Private Subnets with Private Route Table
resource "aws_route_table_association" "private_1" {
  subnet_id      = aws_subnet.private_1.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_2" {
  subnet_id      = aws_subnet.private_2.id
  route_table_id = aws_route_table.private.id
}

# ============================================================================
# S3 Gateway VPC Endpoint (Free - for S3 access from private subnets)
# ============================================================================
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${var.aws_region}.s3"
  
  route_table_ids = [
    aws_route_table.private.id,
    aws_route_table.public.id
  ]

  tags = {
    Name        = "afirgen-free-tier-s3-endpoint"
    Environment = "free-tier"
    ManagedBy   = "Terraform"
    Cost        = "Free"
  }
}

# ============================================================================
# Outputs
# ============================================================================
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_id" {
  description = "Public subnet ID"
  value       = aws_subnet.public.id
}

output "public_subnet_cidr" {
  description = "Public subnet CIDR"
  value       = aws_subnet.public.cidr_block
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = [aws_subnet.private_1.id, aws_subnet.private_2.id]
}

output "private_subnet_cidrs" {
  description = "List of private subnet CIDRs"
  value       = [aws_subnet.private_1.cidr_block, aws_subnet.private_2.cidr_block]
}

output "internet_gateway_id" {
  description = "Internet Gateway ID"
  value       = aws_internet_gateway.main.id
}

output "s3_endpoint_id" {
  description = "S3 Gateway VPC Endpoint ID"
  value       = aws_vpc_endpoint.s3.id
}
