# AFIRGen Terraform Variables

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "afirgen"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the ALB (use specific IPs in production)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "enable_vpn_gateway" {
  description = "Enable VPN Gateway for secure access"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}

variable "enable_sts_endpoint" {
  description = "Enable STS VPC endpoint for IAM role assumption"
  type        = bool
  default     = false
}

variable "enable_xray_endpoint" {
  description = "Enable X-Ray VPC endpoint for distributed tracing"
  type        = bool
  default     = false
}

# CloudWatch Configuration
variable "alarm_email" {
  description = "Email address for CloudWatch alarm notifications"
  type        = string
  default     = ""
}

variable "enable_cloudwatch_dashboards" {
  description = "Enable CloudWatch dashboards"
  type        = bool
  default     = true
}

variable "enable_cloudwatch_alarms" {
  description = "Enable CloudWatch alarms"
  type        = bool
  default     = true
}

# Monitoring and Alerting
variable "monthly_budget_threshold" {
  description = "Monthly budget threshold in USD for billing alarms"
  type        = number
  default     = 100
}

variable "alert_email" {
  description = "Email address for receiving alerts and notifications"
  type        = string
  default     = "admin@example.com"
}

# Performance Optimization
variable "enable_s3_transfer_acceleration" {
  description = "Enable S3 Transfer Acceleration for faster uploads"
  type        = bool
  default     = false
}

variable "enable_rds_performance_insights" {
  description = "Enable RDS Performance Insights (may incur additional costs)"
  type        = bool
  default     = false
}

variable "cloudwatch_log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 7
}

# Bedrock Configuration
variable "bedrock_model_id" {
  description = "Bedrock model ID for FIR generation"
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}

variable "bedrock_embeddings_model_id" {
  description = "Bedrock embeddings model ID"
  type        = string
  default     = "amazon.titan-embed-text-v1"
}

# Vector Database Configuration
variable "vector_db_type" {
  description = "Vector database type (opensearch or aurora_pgvector)"
  type        = string
  default     = "aurora_pgvector"
  
  validation {
    condition     = contains(["opensearch", "aurora_pgvector"], var.vector_db_type)
    error_message = "Vector DB type must be opensearch or aurora_pgvector."
  }
}
