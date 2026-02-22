# AFIRGen AWS Free Tier Infrastructure - Main Configuration
# This configuration deploys the AFIRGen system using only AWS Free Tier services
# to achieve zero-cost deployment during the 12-month free tier period.

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "AFIRGen"
      Environment = "free-tier"
      ManagedBy   = "Terraform"
      CostCenter  = "free-tier"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Outputs
output "deployment_summary" {
  description = "Summary of deployed free tier resources"
  value = {
    vpc_id              = aws_vpc.main.id
    vpc_cidr            = aws_vpc.main.cidr_block
    public_subnet_id    = aws_subnet.public.id
    private_subnet_ids  = [aws_subnet.private_1.id, aws_subnet.private_2.id]
    internet_gateway_id = aws_internet_gateway.main.id
    s3_endpoint_id      = aws_vpc_endpoint.s3.id
    ec2_security_group  = aws_security_group.ec2.id
    rds_security_group  = aws_security_group.rds.id
    account_id          = data.aws_caller_identity.current.account_id
    region              = data.aws_region.current.name
  }
}

output "network_configuration" {
  description = "Network configuration details"
  value = {
    vpc_cidr            = "10.0.0.0/16"
    public_subnet_cidr  = "10.0.1.0/24"
    private_subnet_1    = "10.0.11.0/24"
    private_subnet_2    = "10.0.12.0/24"
    availability_zone_1 = "${var.aws_region}a"
    availability_zone_2 = "${var.aws_region}b"
  }
}
