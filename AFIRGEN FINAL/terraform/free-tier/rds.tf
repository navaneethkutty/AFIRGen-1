# AFIRGen Free Tier RDS MySQL Configuration
# Requirements: 5.1, 9.3, 15.1, 15.2
# 
# This configuration creates a db.t3.micro MySQL instance with:
# - 20GB storage (Free Tier limit)
# - Encryption at rest
# - 7-day backup retention with scheduled backup window
# - Optimized parameters for Free Tier (max_connections=50, innodb_buffer_pool_size=512MB)
# - Deployed in private subnets with no public access

# ============================================================================
# RDS Subnet Group (Required - must span at least 2 AZs)
# ============================================================================
resource "aws_db_subnet_group" "main" {
  name        = "${var.project_name}-${var.environment}-db-subnet-group"
  description = "Subnet group for AFIRGen Free Tier RDS instance"
  subnet_ids  = [aws_subnet.private_1.id, aws_subnet.private_2.id]

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-subnet-group"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "RDS"
  }
}

# ============================================================================
# RDS Parameter Group (Custom parameters for Free Tier optimization)
# ============================================================================
resource "aws_db_parameter_group" "main" {
  name        = "${var.project_name}-${var.environment}-mysql8-params"
  family      = "mysql8.0"
  description = "Custom parameter group for AFIRGen Free Tier MySQL 8.0"

  # Requirement 5.1: Optimize for db.t3.micro (1GB RAM)
  parameter {
    name  = "max_connections"
    value = "50"
  }

  parameter {
    name  = "innodb_buffer_pool_size"
    value = "{DBInstanceClassMemory*1024*512/1024/1024/1024}"  # 512MB
  }

  # Enable slow query log for optimization
  parameter {
    name  = "slow_query_log"
    value = "1"
  }

  parameter {
    name  = "long_query_time"
    value = "2"
  }

  # General log disabled to save storage
  parameter {
    name  = "general_log"
    value = "0"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-mysql8-params"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# RDS MySQL Instance (db.t3.micro - Free Tier eligible)
# ============================================================================
resource "aws_db_instance" "main" {
  # Instance Configuration
  identifier     = "${var.project_name}-${var.environment}-mysql"
  engine         = "mysql"
  engine_version = "8.0.35"  # Latest stable MySQL 8.0
  instance_class = "db.t3.micro"  # Free Tier: 750 hours/month

  # Storage Configuration (Requirement 5.1)
  allocated_storage     = 20  # Free Tier limit: 20GB
  max_allocated_storage = 20  # Prevent auto-scaling beyond free tier
  storage_type          = "gp2"
  storage_encrypted     = true  # Requirement 9.3: Encryption at rest

  # Database Configuration
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 3306

  # Network Configuration (Requirement 9.1: Private subnet, no public access)
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Parameter and Option Groups
  parameter_group_name = aws_db_parameter_group.main.name

  # Backup Configuration (Requirements 15.1, 15.2)
  backup_retention_period = 7  # 7-day retention (Free Tier: up to 7 days)
  backup_window           = "03:00-04:00"  # UTC, low-traffic window
  maintenance_window      = "sun:04:00-sun:05:00"  # UTC, after backup

  # High Availability (Disabled for Free Tier)
  multi_az = false  # Not available in Free Tier

  # Deletion Protection
  deletion_protection       = false  # Set to true in production
  skip_final_snapshot       = true   # Set to false in production
  final_snapshot_identifier = "${var.project_name}-${var.environment}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  # Performance Insights (Not available in Free Tier)
  enabled_cloudwatch_logs_exports = ["error", "slowquery"]

  # Auto minor version upgrade
  auto_minor_version_upgrade = true

  # Apply changes immediately (for development)
  apply_immediately = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-mysql"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Engine      = "MySQL 8.0"
    Purpose     = "FIR Database"
  }

  lifecycle {
    # Prevent accidental deletion
    prevent_destroy = false  # Set to true in production
    
    # Ignore password changes (manage via AWS Secrets Manager in production)
    ignore_changes = [password]
  }
}

# ============================================================================
# CloudWatch Alarms for RDS Monitoring
# ============================================================================

# Storage Space Alarm (Requirement 5.2: Alert at 90% capacity)
resource "aws_cloudwatch_metric_alarm" "rds_storage" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-storage-high"
  alarm_description   = "Alert when RDS storage exceeds 90% (18GB of 20GB)"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300  # 5 minutes
  statistic           = "Average"
  threshold           = 2147483648  # 2GB remaining (18GB used)
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  alarm_actions = []  # Add SNS topic ARN for notifications

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-storage-alarm"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# CPU Utilization Alarm
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-cpu-high"
  alarm_description   = "Alert when RDS CPU exceeds 90%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300  # 5 minutes
  statistic           = "Average"
  threshold           = 90
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  alarm_actions = []  # Add SNS topic ARN for notifications

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-cpu-alarm"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Database Connections Alarm (Requirement 12.4: Alert at 40 connections)
resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-connections-high"
  alarm_description   = "Alert when RDS connections exceed 40 (80% of max 50)"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300  # 5 minutes
  statistic           = "Average"
  threshold           = 40
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  alarm_actions = []  # Add SNS topic ARN for notifications

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-connections-alarm"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# Outputs
# ============================================================================
output "rds_instance_id" {
  description = "RDS instance identifier"
  value       = aws_db_instance.main.id
}

output "rds_endpoint" {
  description = "RDS instance endpoint (host:port)"
  value       = aws_db_instance.main.endpoint
}

output "rds_address" {
  description = "RDS instance address (hostname only)"
  value       = aws_db_instance.main.address
}

output "rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.main.db_name
}

output "rds_arn" {
  description = "RDS instance ARN"
  value       = aws_db_instance.main.arn
}

output "rds_resource_id" {
  description = "RDS instance resource ID"
  value       = aws_db_instance.main.resource_id
}

output "rds_subnet_group" {
  description = "RDS subnet group name"
  value       = aws_db_subnet_group.main.name
}

output "rds_parameter_group" {
  description = "RDS parameter group name"
  value       = aws_db_parameter_group.main.name
}

output "rds_security_group" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}

# Connection string for application configuration
output "rds_connection_info" {
  description = "RDS connection information for application configuration"
  value = {
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
    database = aws_db_instance.main.db_name
    username = var.db_username
  }
  sensitive = true
}
