# AFIRGen IAM Policies for Bedrock Migration
# Requirements: 9.1 (Least privilege), 9.2 (IAM roles), Bedrock migration
#
# This configuration creates IAM policies for:
# - S3 access (models, temp files, backups)
# - Bedrock access (Claude 3 Sonnet, Titan Embeddings)
# - Transcribe access (10 Indian languages)
# - Textract access (document OCR)
# - CloudWatch Logs and Metrics
# - X-Ray tracing
# - KMS encryption/decryption
# - OpenSearch Serverless (conditional)
# - RDS IAM authentication (conditional)

# ============================================================================
# Data Sources
# ============================================================================
data "aws_caller_identity" "current" {}

# ============================================================================
# IAM Role for EC2 Instance
# ============================================================================
resource "aws_iam_role" "ec2" {
  name = "${var.project_name}-${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-ec2-role"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "EC2 instance role for AFIRGen Bedrock"
  }
}

# ============================================================================
# IAM Policy: S3 Access
# ============================================================================
resource "aws_iam_role_policy" "ec2_s3" {
  name = "${var.project_name}-${var.environment}-ec2-s3-policy"
  role = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ObjectAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.models.arn}/*",
          "${aws_s3_bucket.temp.arn}/*",
          "${aws_s3_bucket.backups.arn}/*"
        ]
      },
      {
        Sid    = "S3BucketAccess"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.models.arn,
          aws_s3_bucket.temp.arn,
          aws_s3_bucket.backups.arn
        ]
      }
    ]
  })
}

# ============================================================================
# IAM Policy: Bedrock Access (Claude 3 Sonnet + Titan Embeddings)
# ============================================================================
resource "aws_iam_role_policy" "ec2_bedrock" {
  name = "${var.project_name}-${var.environment}-ec2-bedrock-policy"
  role = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockModelAccess"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v1"
        ]
      },
      {
        Sid    = "BedrockListModels"
        Effect = "Allow"
        Action = [
          "bedrock:ListFoundationModels",
          "bedrock:GetFoundationModel"
        ]
        Resource = "*"
      }
    ]
  })
}

# ============================================================================
# IAM Policy: Transcribe Access (10 Indian Languages)
# ============================================================================
resource "aws_iam_role_policy" "ec2_transcribe" {
  name = "${var.project_name}-${var.environment}-ec2-transcribe-policy"
  role = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "TranscribeJobManagement"
        Effect = "Allow"
        Action = [
          "transcribe:StartTranscriptionJob",
          "transcribe:GetTranscriptionJob",
          "transcribe:DeleteTranscriptionJob",
          "transcribe:ListTranscriptionJobs"
        ]
        Resource = "*"
      }
    ]
  })
}

# ============================================================================
# IAM Policy: Textract Access (Document OCR)
# ============================================================================
resource "aws_iam_role_policy" "ec2_textract" {
  name = "${var.project_name}-${var.environment}-ec2-textract-policy"
  role = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "TextractDocumentAnalysis"
        Effect = "Allow"
        Action = [
          "textract:DetectDocumentText",
          "textract:AnalyzeDocument",
          "textract:GetDocumentAnalysis",
          "textract:GetDocumentTextDetection"
        ]
        Resource = "*"
      }
    ]
  })
}

# ============================================================================
# IAM Policy: CloudWatch Logs and Metrics
# ============================================================================
resource "aws_iam_role_policy" "ec2_cloudwatch" {
  name = "${var.project_name}-${var.environment}-ec2-cloudwatch-policy"
  role = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchMetrics"
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "AFIRGen/Bedrock"
          }
        }
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams",
          "logs:DescribeLogGroups"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/afirgen/*"
      },
      {
        Sid    = "XRayTracing"
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets"
        ]
        Resource = "*"
      }
    ]
  })
}

# ============================================================================
# IAM Policy: KMS Encryption/Decryption
# ============================================================================
resource "aws_iam_role_policy" "ec2_kms" {
  name = "${var.project_name}-${var.environment}-ec2-kms-policy"
  role = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "KMSEncryptionDecryption"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.main.arn
        Condition = {
          StringEquals = {
            "kms:ViaService" = [
              "s3.${var.aws_region}.amazonaws.com",
              "rds.${var.aws_region}.amazonaws.com"
            ]
          }
        }
      }
    ]
  })
}

# ============================================================================
# IAM Policy: OpenSearch Serverless (Conditional)
# ============================================================================
resource "aws_iam_role_policy" "ec2_opensearch" {
  count = var.vector_db_type == "opensearch" ? 1 : 0
  name  = "${var.project_name}-${var.environment}-ec2-opensearch-policy"
  role  = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "OpenSearchServerlessAccess"
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = "*"
      },
      {
        Sid    = "OpenSearchServerlessCollectionAccess"
        Effect = "Allow"
        Action = [
          "aoss:ListCollections",
          "aoss:BatchGetCollection"
        ]
        Resource = "*"
      }
    ]
  })
}

# ============================================================================
# IAM Policy: RDS IAM Authentication (Conditional - for Aurora pgvector)
# ============================================================================
resource "aws_iam_role_policy" "ec2_rds_connect" {
  count = var.vector_db_type == "aurora_pgvector" ? 1 : 0
  name  = "${var.project_name}-${var.environment}-ec2-rds-connect-policy"
  role  = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RDSIAMAuthentication"
        Effect = "Allow"
        Action = [
          "rds-db:connect"
        ]
        Resource = "arn:aws:rds-db:${var.aws_region}:${data.aws_caller_identity.current.account_id}:dbuser:*/*"
      }
    ]
  })
}

# ============================================================================
# IAM Instance Profile
# ============================================================================
resource "aws_iam_instance_profile" "ec2" {
  name = "${var.project_name}-${var.environment}-ec2-profile"
  role = aws_iam_role.ec2.name

  tags = {
    Name        = "${var.project_name}-${var.environment}-ec2-profile"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# Outputs
# ============================================================================
output "ec2_iam_role_name" {
  description = "IAM role name for EC2 instance"
  value       = aws_iam_role.ec2.name
}

output "ec2_iam_role_arn" {
  description = "IAM role ARN for EC2 instance"
  value       = aws_iam_role.ec2.arn
}

output "ec2_instance_profile_name" {
  description = "IAM instance profile name"
  value       = aws_iam_instance_profile.ec2.name
}

output "ec2_instance_profile_arn" {
  description = "IAM instance profile ARN"
  value       = aws_iam_instance_profile.ec2.arn
}

output "iam_policies_attached" {
  description = "List of IAM policies attached to EC2 role"
  value = [
    "S3 Access",
    "Bedrock Access (Claude 3 Sonnet + Titan Embeddings)",
    "Transcribe Access (10 Indian Languages)",
    "Textract Access (Document OCR)",
    "CloudWatch Logs and Metrics",
    "X-Ray Tracing",
    "KMS Encryption/Decryption",
    var.vector_db_type == "opensearch" ? "OpenSearch Serverless Access" : null,
    var.vector_db_type == "aurora_pgvector" ? "RDS IAM Authentication" : null
  ]
}
