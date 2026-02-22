# AFIRGen Free Tier Terraform Variables

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
  
  validation {
    condition     = can(regex("^us-east-1$", var.aws_region))
    error_message = "Free tier deployment is optimized for us-east-1 region."
  }
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "afirgen"
}

variable "environment" {
  description = "Environment name (should be free-tier)"
  type        = string
  default     = "free-tier"
}

# Network Configuration
# These values are fixed per the design document requirements
# DO NOT MODIFY - changing these may break the free tier architecture

# Security Configuration
variable "admin_ip" {
  description = "Administrator IP address for SSH access (CIDR notation, e.g., 203.0.113.0/32)"
  type        = string
  
  validation {
    condition     = can(cidrhost(var.admin_ip, 0))
    error_message = "admin_ip must be a valid CIDR block (e.g., 203.0.113.0/32)."
  }
}

locals {
  vpc_cidr             = "10.0.0.0/16"
  public_subnet_cidr   = "10.0.1.0/24"
  private_subnet_1_cidr = "10.0.11.0/24"
  private_subnet_2_cidr = "10.0.12.0/24"
  availability_zone_1  = "${var.aws_region}a"
  availability_zone_2  = "${var.aws_region}b"
}
