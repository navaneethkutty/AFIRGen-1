# AFIRGen VPC Endpoints Configuration for Bedrock Migration
# Requirements: 13.3 (VPC endpoints), Cost optimization
#
# This configuration creates VPC endpoints for:
# - S3 (Gateway endpoint - Free)
# - Bedrock Runtime (Interface endpoint)
# - Transcribe (Interface endpoint)
# - Textract (Interface endpoint)
#
# Benefits:
# - Reduced data transfer costs (traffic stays within AWS)
# - Improved security (no internet gateway needed)
# - Lower latency for AWS service calls
#
# Cost: ~$21.60/month for 3 interface endpoints (~$0.01/hour each)

# ============================================================================
# S3 Gateway VPC Endpoint (Free - already in vpc.tf)
# ============================================================================
# Note: S3 Gateway endpoint is defined in vpc.tf to avoid duplication
# It's a Gateway endpoint (free) that routes S3 traffic through the VPC

# ============================================================================
# Security Group for VPC Endpoints (already in vpc.tf)
# ============================================================================
# Note: Security group for VPC endpoints is defined in vpc.tf
# It allows HTTPS (443) from VPC CIDR block

# ============================================================================
# Bedrock Runtime VPC Endpoint (already in vpc.tf)
# ============================================================================
# Note: Bedrock Runtime endpoint is defined in vpc.tf
# Interface endpoint for Claude 3 Sonnet and Titan Embeddings API calls

# ============================================================================
# Transcribe VPC Endpoint (already in vpc.tf)
# ============================================================================
# Note: Transcribe endpoint is defined in vpc.tf
# Interface endpoint for audio transcription API calls

# ============================================================================
# Textract VPC Endpoint (already in vpc.tf)
# ============================================================================
# Note: Textract endpoint is defined in vpc.tf
# Interface endpoint for document OCR API calls

# ============================================================================
# Additional VPC Endpoints (Optional - Uncomment if needed)
# ============================================================================

# CloudWatch Logs VPC Endpoint
# Uncomment if you want to route CloudWatch Logs traffic through VPC
# resource "aws_vpc_endpoint" "logs" {
#   vpc_id              = aws_vpc.main.id
#   service_name        = "com.amazonaws.${var.aws_region}.logs"
#   vpc_endpoint_type   = "Interface"
#   subnet_ids          = [aws_subnet.private_1.id, aws_subnet.private_2.id]
#   security_group_ids  = [aws_security_group.vpc_endpoints.id]
#   private_dns_enabled = true
#
#   tags = {
#     Name        = "${var.project_name}-${var.environment}-logs-endpoint"
#     Environment = var.environment
#     ManagedBy   = "Terraform"
#     Service     = "CloudWatch Logs"
#   }
# }

# CloudWatch Monitoring VPC Endpoint
# Uncomment if you want to route CloudWatch Metrics traffic through VPC
# resource "aws_vpc_endpoint" "monitoring" {
#   vpc_id              = aws_vpc.main.id
#   service_name        = "com.amazonaws.${var.aws_region}.monitoring"
#   vpc_endpoint_type   = "Interface"
#   subnet_ids          = [aws_subnet.private_1.id, aws_subnet.private_2.id]
#   security_group_ids  = [aws_security_group.vpc_endpoints.id]
#   private_dns_enabled = true
#
#   tags = {
#     Name        = "${var.project_name}-${var.environment}-monitoring-endpoint"
#     Environment = var.environment
#     ManagedBy   = "Terraform"
#     Service     = "CloudWatch Monitoring"
#   }
# }

# X-Ray VPC Endpoint
# Uncomment if you want to route X-Ray tracing traffic through VPC
# resource "aws_vpc_endpoint" "xray" {
#   vpc_id              = aws_vpc.main.id
#   service_name        = "com.amazonaws.${var.aws_region}.xray"
#   vpc_endpoint_type   = "Interface"
#   subnet_ids          = [aws_subnet.private_1.id, aws_subnet.private_2.id]
#   security_group_ids  = [aws_security_group.vpc_endpoints.id]
#   private_dns_enabled = true
#
#   tags = {
#     Name        = "${var.project_name}-${var.environment}-xray-endpoint"
#     Environment = var.environment
#     ManagedBy   = "Terraform"
#     Service     = "X-Ray"
#   }
# }

# Secrets Manager VPC Endpoint
# Uncomment if you want to use AWS Secrets Manager for credentials
# resource "aws_vpc_endpoint" "secretsmanager" {
#   vpc_id              = aws_vpc.main.id
#   service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
#   vpc_endpoint_type   = "Interface"
#   subnet_ids          = [aws_subnet.private_1.id, aws_subnet.private_2.id]
#   security_group_ids  = [aws_security_group.vpc_endpoints.id]
#   private_dns_enabled = true
#
#   tags = {
#     Name        = "${var.project_name}-${var.environment}-secretsmanager-endpoint"
#     Environment = var.environment
#     ManagedBy   = "Terraform"
#     Service     = "Secrets Manager"
#   }
# }

# ============================================================================
# Outputs
# ============================================================================
# Note: VPC endpoint outputs are in vpc.tf

# ============================================================================
# Cost Summary
# ============================================================================
# Gateway Endpoints (Free):
# - S3: $0/month
#
# Interface Endpoints (~$0.01/hour each):
# - Bedrock Runtime: ~$7.20/month
# - Transcribe: ~$7.20/month
# - Textract: ~$7.20/month
#
# Total VPC Endpoint Cost: ~$21.60/month
#
# Data Transfer Savings:
# - Eliminates data transfer charges for AWS service API calls
# - Estimated savings: $5-10/month depending on usage
#
# Net Cost: ~$11-16/month (after savings)
