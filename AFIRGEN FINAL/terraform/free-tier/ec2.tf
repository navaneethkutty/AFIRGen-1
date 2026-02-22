# AFIRGen Free Tier EC2 Instance Configuration
# Requirements: 2.1, 2.5
# 
# This configuration creates:
# - EC2 t2.micro instance (1 vCPU, 1GB RAM - free tier eligible)
# - 30GB gp3 EBS volume
# - IAM role for S3 access
# - Elastic IP
# - User data script for automated setup

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
  }
}

# IAM Policy for S3 Access
resource "aws_iam_role_policy" "ec2_s3" {
  name = "${var.project_name}-${var.environment}-ec2-s3-policy"
  role = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
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
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
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

# IAM Policy for CloudWatch Logs and Metrics
resource "aws_iam_role_policy" "ec2_cloudwatch" {
  name = "${var.project_name}-${var.environment}-ec2-cloudwatch-policy"
  role = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Instance Profile
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
# EC2 Instance
# ============================================================================
resource "aws_instance" "main" {
  ami           = var.ami_id
  instance_type = "t2.micro"  # Free tier: 750 hours/month, 1 vCPU, 1GB RAM

  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.ec2.id]
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.ec2.name

  # 30GB gp3 EBS volume (free tier eligible)
  root_block_device {
    volume_size           = 30
    volume_type           = "gp3"
    delete_on_termination = true
    encrypted             = true

    tags = {
      Name        = "${var.project_name}-${var.environment}-root-volume"
      Environment = var.environment
    }
  }

  # User data script for automated setup
  user_data = templatefile("${path.module}/user-data.sh", {
    aws_region      = var.aws_region
    models_bucket   = aws_s3_bucket.models.id
    temp_bucket     = aws_s3_bucket.temp.id
    backups_bucket  = aws_s3_bucket.backups.id
    rds_endpoint    = aws_db_instance.main.address
    db_name         = var.db_name
    db_username     = var.db_username
    db_password     = var.db_password
  })

  # Enable detailed monitoring (free tier: 10 metrics)
  monitoring = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-ec2"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Main application server"
  }

  lifecycle {
    ignore_changes = [
      ami,  # Prevent replacement on AMI updates
      user_data  # Prevent replacement on user data changes
    ]
  }
}

# ============================================================================
# Elastic IP
# ============================================================================
resource "aws_eip" "main" {
  instance = aws_instance.main.id
  domain   = "vpc"

  tags = {
    Name        = "${var.project_name}-${var.environment}-eip"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  depends_on = [aws_internet_gateway.main]
}

# ============================================================================
# Outputs
# ============================================================================
output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.main.id
}

output "ec2_instance_type" {
  description = "EC2 instance type"
  value       = aws_instance.main.instance_type
}

output "ec2_private_ip" {
  description = "EC2 instance private IP address"
  value       = aws_instance.main.private_ip
}

output "ec2_public_ip" {
  description = "EC2 instance public IP address (Elastic IP)"
  value       = aws_eip.main.public_ip
}

output "ec2_elastic_ip" {
  description = "Elastic IP address"
  value       = aws_eip.main.public_ip
}

output "ec2_iam_role" {
  description = "IAM role attached to EC2 instance"
  value       = aws_iam_role.ec2.name
}

output "ec2_configuration" {
  description = "EC2 configuration summary"
  value = {
    instance_type = "t2.micro"
    vcpu          = 1
    memory_gb     = 1
    storage_gb    = 30
    storage_type  = "gp3"
    monitoring    = "enabled"
    free_tier     = true
  }
}
