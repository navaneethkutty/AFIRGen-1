# CloudWatch Alarms for Production Monitoring
# Creates alarms for critical metrics with SNS notifications

# ============================================================================
# SNS Topic for Alerts
# ============================================================================

resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-${var.environment}-alerts"

  tags = {
    Name        = "${var.project_name}-${var.environment}-alerts"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email  # Define in variables.tf
}

# ============================================================================
# EC2 Instance Alarms
# ============================================================================

# High CPU utilization alarm
resource "aws_cloudwatch_metric_alarm" "ec2_high_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-ec2-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"  # 5 minutes
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors EC2 CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    InstanceId = aws_instance.main.id
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-ec2-high-cpu"
    Environment = var.environment
  }
}

# Instance status check failed
resource "aws_cloudwatch_metric_alarm" "ec2_status_check" {
  alarm_name          = "${var.project_name}-${var.environment}-ec2-status-check"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = "60"
  statistic           = "Maximum"
  threshold           = "0"
  alarm_description   = "This metric monitors EC2 instance status checks"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    InstanceId = aws_instance.main.id
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-ec2-status"
    Environment = var.environment
  }
}

# ============================================================================
# RDS Database Alarms
# ============================================================================

# High CPU utilization
resource "aws_cloudwatch_metric_alarm" "rds_high_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors RDS CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-high-cpu"
    Environment = var.environment
  }
}

# Low free storage space
resource "aws_cloudwatch_metric_alarm" "rds_low_storage" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "2000000000"  # 2GB in bytes
  alarm_description   = "This metric monitors RDS free storage space"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-low-storage"
    Environment = var.environment
  }
}

# High database connections
resource "aws_cloudwatch_metric_alarm" "rds_high_connections" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-high-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"  # Adjust based on max_connections
  alarm_description   = "This metric monitors RDS database connections"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-connections"
    Environment = var.environment
  }
}

# ============================================================================
# Application Alarms (Custom Metrics)
# ============================================================================

# High error rate
resource "aws_cloudwatch_metric_alarm" "app_high_error_rate" {
  alarm_name          = "${var.project_name}-${var.environment}-app-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ErrorRate"
  namespace           = "AFIRGen/Bedrock"
  period              = "300"
  statistic           = "Average"
  threshold           = "5"  # 5% error rate
  alarm_description   = "This metric monitors application error rate"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-${var.environment}-app-error-rate"
    Environment = var.environment
  }
}

# High latency
resource "aws_cloudwatch_metric_alarm" "app_high_latency" {
  alarm_name          = "${var.project_name}-${var.environment}-app-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Latency"
  namespace           = "AFIRGen/Bedrock"
  period              = "300"
  statistic           = "Average"
  threshold           = "5000"  # 5 seconds
  alarm_description   = "This metric monitors application latency"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-${var.environment}-app-latency"
    Environment = var.environment
  }
}

# Low success rate
resource "aws_cloudwatch_metric_alarm" "app_low_success_rate" {
  alarm_name          = "${var.project_name}-${var.environment}-app-low-success-rate"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "SuccessRate"
  namespace           = "AFIRGen/Bedrock"
  period              = "300"
  statistic           = "Average"
  threshold           = "95"  # 95% success rate
  alarm_description   = "This metric monitors application success rate"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-${var.environment}-app-success-rate"
    Environment = var.environment
  }
}

# ============================================================================
# Cost Anomaly Alarm
# ============================================================================

# Billing alarm for cost control
resource "aws_cloudwatch_metric_alarm" "billing_alarm" {
  alarm_name          = "${var.project_name}-${var.environment}-billing-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "21600"  # 6 hours
  statistic           = "Maximum"
  threshold           = var.monthly_budget_threshold  # Define in variables.tf
  alarm_description   = "This metric monitors estimated AWS charges"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    Currency = "USD"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-billing"
    Environment = var.environment
  }
}

# ============================================================================
# Outputs
# ============================================================================

output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}

output "alarm_names" {
  description = "List of CloudWatch alarm names"
  value = [
    aws_cloudwatch_metric_alarm.ec2_high_cpu.alarm_name,
    aws_cloudwatch_metric_alarm.ec2_status_check.alarm_name,
    aws_cloudwatch_metric_alarm.rds_high_cpu.alarm_name,
    aws_cloudwatch_metric_alarm.rds_low_storage.alarm_name,
    aws_cloudwatch_metric_alarm.rds_high_connections.alarm_name,
    aws_cloudwatch_metric_alarm.app_high_error_rate.alarm_name,
    aws_cloudwatch_metric_alarm.app_high_latency.alarm_name,
    aws_cloudwatch_metric_alarm.app_low_success_rate.alarm_name,
    aws_cloudwatch_metric_alarm.billing_alarm.alarm_name
  ]
}
