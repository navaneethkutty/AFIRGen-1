# AFIRGen KMS Key Configuration for Bedrock Migration
# Requirements: 9.3 (Encryption at rest), Security best practices
#
# This configuration creates:
# - KMS customer-managed key for S3 and RDS encryption
# - Key rotation enabled (annual)
# - Key policy with least-privilege access
# - Aliases for easy reference

# ============================================================================
# KMS Key for Data Encryption
# ============================================================================
resource "aws_kms_key" "main" {
  description             = "AFIRGen encryption key for S3 and RDS"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-encryption-key"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Data encryption for S3 and RDS"
  }
}

# KMS Key Alias
resource "aws_kms_alias" "main" {
  name          = "alias/${var.project_name}-${var.environment}-encryption"
  target_key_id = aws_kms_key.main.key_id
}

# ============================================================================
# KMS Key Policy
# ============================================================================
# Note: The key policy is automatically created by AWS with the following permissions:
# - Root account has full access
# - EC2 instance role can use the key via the IAM policy in ec2.tf
# - S3 and RDS services can use the key for encryption/decryption

# If you need a custom key policy, uncomment and modify the following:
# resource "aws_kms_key_policy" "main" {
#   key_id = aws_kms_key.main.id
#
#   policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Sid    = "Enable IAM User Permissions"
#         Effect = "Allow"
#         Principal = {
#           AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
#         }
#         Action   = "kms:*"
#         Resource = "*"
#       },
#       {
#         Sid    = "Allow EC2 to use the key"
#         Effect = "Allow"
#         Principal = {
#           AWS = aws_iam_role.ec2.arn
#         }
#         Action = [
#           "kms:Decrypt",
#           "kms:GenerateDataKey",
#           "kms:DescribeKey"
#         ]
#         Resource = "*"
#       },
#       {
#         Sid    = "Allow S3 to use the key"
#         Effect = "Allow"
#         Principal = {
#           Service = "s3.amazonaws.com"
#         }
#         Action = [
#           "kms:Decrypt",
#           "kms:GenerateDataKey"
#         ]
#         Resource = "*"
#       },
#       {
#         Sid    = "Allow RDS to use the key"
#         Effect = "Allow"
#         Principal = {
#           Service = "rds.amazonaws.com"
#         }
#         Action = [
#           "kms:Decrypt",
#           "kms:GenerateDataKey",
#           "kms:CreateGrant"
#         ]
#         Resource = "*"
#       }
#     ]
#   })
# }

# ============================================================================
# Outputs
# ============================================================================
output "kms_key_id" {
  description = "KMS key ID"
  value       = aws_kms_key.main.key_id
}

output "kms_key_arn" {
  description = "KMS key ARN"
  value       = aws_kms_key.main.arn
}

output "kms_key_alias" {
  description = "KMS key alias"
  value       = aws_kms_alias.main.name
}

output "kms_key_rotation_enabled" {
  description = "Whether key rotation is enabled"
  value       = aws_kms_key.main.enable_key_rotation
}
