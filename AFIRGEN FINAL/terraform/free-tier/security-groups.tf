# AFIRGen Free Tier Security Groups Configuration
# Requirements: 9.1, 9.2
# 
# This configuration creates security groups for:
# - EC2 instance (HTTP, HTTPS, SSH access)
# - RDS instance (MySQL access from EC2 only)
#
# Security best practices:
# - SSH access restricted to specific admin IP
# - RDS in private subnet with no public access
# - Minimal port exposure following principle of least privilege

# ============================================================================
# EC2 Security Group
# ============================================================================
resource "aws_security_group" "ec2" {
  name        = "${var.project_name}-${var.environment}-ec2-sg"
  description = "Security group for AFIRGen EC2 instance - allows HTTP, HTTPS, and restricted SSH"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name        = "${var.project_name}-${var.environment}-ec2-sg"
    Purpose     = "EC2 Instance"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Ingress Rules for EC2
resource "aws_vpc_security_group_ingress_rule" "ec2_http" {
  security_group_id = aws_security_group.ec2.id
  description       = "Allow HTTP traffic from internet"
  
  from_port   = 80
  to_port     = 80
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "allow-http"
  }
}

resource "aws_vpc_security_group_ingress_rule" "ec2_https" {
  security_group_id = aws_security_group.ec2.id
  description       = "Allow HTTPS traffic from internet"
  
  from_port   = 443
  to_port     = 443
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "allow-https"
  }
}

resource "aws_vpc_security_group_ingress_rule" "ec2_ssh" {
  security_group_id = aws_security_group.ec2.id
  description       = "Allow SSH access from admin IP only"
  
  from_port   = 22
  to_port     = 22
  ip_protocol = "tcp"
  cidr_ipv4   = var.admin_ip

  tags = {
    Name = "allow-ssh-admin"
  }
}

# Egress Rules for EC2
resource "aws_vpc_security_group_egress_rule" "ec2_all" {
  security_group_id = aws_security_group.ec2.id
  description       = "Allow all outbound traffic"
  
  ip_protocol = "-1"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "allow-all-outbound"
  }
}

# ============================================================================
# RDS Security Group
# ============================================================================
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "Security group for AFIRGen RDS instance - allows MySQL access from EC2 only"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-sg"
    Purpose     = "RDS Instance"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Ingress Rules for RDS
resource "aws_vpc_security_group_ingress_rule" "rds_mysql" {
  security_group_id = aws_security_group.rds.id
  description       = "Allow MySQL access from EC2 security group only"
  
  from_port                    = 3306
  to_port                      = 3306
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ec2.id

  tags = {
    Name = "allow-mysql-from-ec2"
  }
}

# Egress Rules for RDS
resource "aws_vpc_security_group_egress_rule" "rds_all" {
  security_group_id = aws_security_group.rds.id
  description       = "Allow all outbound traffic"
  
  ip_protocol = "-1"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "allow-all-outbound"
  }
}

# ============================================================================
# Outputs
# ============================================================================
output "ec2_security_group_id" {
  description = "Security group ID for EC2 instance"
  value       = aws_security_group.ec2.id
}

output "ec2_security_group_name" {
  description = "Security group name for EC2 instance"
  value       = aws_security_group.ec2.name
}

output "rds_security_group_id" {
  description = "Security group ID for RDS instance"
  value       = aws_security_group.rds.id
}

output "rds_security_group_name" {
  description = "Security group name for RDS instance"
  value       = aws_security_group.rds.name
}

output "security_configuration" {
  description = "Security configuration summary"
  value = {
    ec2_allowed_ports = ["80 (HTTP)", "443 (HTTPS)", "22 (SSH - restricted)"]
    rds_allowed_ports = ["3306 (MySQL - from EC2 only)"]
    ssh_access_cidr   = var.admin_ip
    rds_public_access = false
  }
}
