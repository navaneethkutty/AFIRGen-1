# AFIRGen S3 Buckets Configuration
# Creates S3 buckets for frontend hosting, ML models, temporary files, and backups
# All buckets configured to stay within AWS Free Tier limits (5GB total storage)

# Get current AWS account ID for unique bucket naming
locals {
  account_id = data.aws_caller_identity.current.account_id
}

# ============================================================================
# Frontend Bucket - Static Website Hosting
# ============================================================================
# Stores frontend static files (HTML, CSS, JS) served via CloudFront
# Requirements: 10.1, 9.4

resource "aws_s3_bucket" "frontend" {
  bucket = "afirgen-frontend-${local.account_id}"

  tags = {
    Name        = "AFIRGen Frontend"
    Purpose     = "Static website hosting"
    Requirement = "10.1"
  }
}

# Enable versioning for frontend bucket
resource "aws_s3_bucket_versioning" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Configure website hosting
resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

# Enable SSE-S3 encryption for frontend bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy to delete old versions after 7 days
resource "aws_s3_bucket_lifecycle_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
}

# Block public access (CloudFront will access via OAI)
resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ============================================================================
# Models Bucket - ML Model Storage
# ============================================================================
# Stores quantized GGUF models, Whisper, and OCR models (~5GB total)
# Requirements: 10.1, 3.3, 9.4

resource "aws_s3_bucket" "models" {
  bucket = "afirgen-models-${local.account_id}"

  tags = {
    Name        = "AFIRGen ML Models"
    Purpose     = "ML model storage"
    Requirement = "10.1, 3.3"
  }
}

# Enable versioning for models bucket
resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable SSE-S3 encryption for models bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "models" {
  bucket = aws_s3_bucket.models.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ============================================================================
# Temporary Files Bucket - Short-lived Uploads
# ============================================================================
# Stores temporary audio/image uploads with 1-day expiration
# Requirements: 10.2, 9.4

resource "aws_s3_bucket" "temp" {
  bucket = "afirgen-temp-${local.account_id}"

  tags = {
    Name        = "AFIRGen Temporary Files"
    Purpose     = "Temporary file uploads"
    Requirement = "10.2"
  }
}

# Enable SSE-S3 encryption for temp bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "temp" {
  bucket = aws_s3_bucket.temp.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy to delete files after 1 day
resource "aws_s3_bucket_lifecycle_configuration" "temp" {
  bucket = aws_s3_bucket.temp.id

  rule {
    id     = "delete-after-1-day"
    status = "Enabled"

    expiration {
      days = 1
    }

    # Also delete incomplete multipart uploads after 1 day
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "temp" {
  bucket = aws_s3_bucket.temp.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ============================================================================
# Backups Bucket - Database Backups with Glacier Transition
# ============================================================================
# Stores RDS backups with transition to Glacier after 30 days
# Requirements: 10.3, 9.4

resource "aws_s3_bucket" "backups" {
  bucket = "afirgen-backups-${local.account_id}"

  tags = {
    Name        = "AFIRGen Database Backups"
    Purpose     = "Database backup storage"
    Requirement = "10.3"
  }
}

# Enable versioning for backups bucket
resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable SSE-S3 encryption for backups bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy: Glacier transition after 30 days, delete after 90 days
resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "glacier-transition-and-expiration"
    status = "Enabled"

    # Transition to Glacier after 30 days
    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    # Delete after 90 days total
    expiration {
      days = 90
    }

    # Handle noncurrent versions
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ============================================================================
# Outputs
# ============================================================================

output "s3_buckets" {
  description = "S3 bucket names and ARNs"
  value = {
    frontend = {
      name                = aws_s3_bucket.frontend.id
      arn                 = aws_s3_bucket.frontend.arn
      website_endpoint    = aws_s3_bucket_website_configuration.frontend.website_endpoint
      website_domain      = aws_s3_bucket_website_configuration.frontend.website_domain
    }
    models = {
      name = aws_s3_bucket.models.id
      arn  = aws_s3_bucket.models.arn
    }
    temp = {
      name = aws_s3_bucket.temp.id
      arn  = aws_s3_bucket.temp.arn
    }
    backups = {
      name = aws_s3_bucket.backups.id
      arn  = aws_s3_bucket.backups.arn
    }
  }
}

output "s3_bucket_names" {
  description = "S3 bucket names for easy reference"
  value = {
    frontend = aws_s3_bucket.frontend.id
    models   = aws_s3_bucket.models.id
    temp     = aws_s3_bucket.temp.id
    backups  = aws_s3_bucket.backups.id
  }
}
