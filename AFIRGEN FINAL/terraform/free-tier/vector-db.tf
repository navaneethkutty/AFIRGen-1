# AFIRGen Vector Database Configuration
# Supports both OpenSearch Serverless and Aurora PostgreSQL with pgvector
# Default: Aurora pgvector (more cost-effective at ~$43/month vs OpenSearch at ~$346/month)

# ============================================================================
# Aurora PostgreSQL with pgvector (Recommended)
# ============================================================================

# Security Group for Aurora pgvector
resource "aws_security_group" "vector_db" {
  count       = var.vector_db_type == "aurora_pgvector" ? 1 : 0
  name        = "${var.project_name}-${var.environment}-vector-db-sg"
  description = "Security group for Aurora pgvector database"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-vector-db-sg"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# DB Subnet Group for Aurora
resource "aws_db_subnet_group" "vector" {
  count      = var.vector_db_type == "aurora_pgvector" ? 1 : 0
  name       = "${var.project_name}-${var.environment}-vector-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]

  tags = {
    Name        = "${var.project_name}-${var.environment}-vector-subnet-group"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Aurora Serverless v2 Cluster for pgvector
resource "aws_rds_cluster" "vector" {
  count                  = var.vector_db_type == "aurora_pgvector" ? 1 : 0
  cluster_identifier     = "${var.project_name}-${var.environment}-vector-cluster"
  engine                 = "aurora-postgresql"
  engine_mode            = "provisioned"
  engine_version         = "15.4"
  database_name          = var.vector_db_name
  master_username        = var.vector_db_username
  master_password        = var.vector_db_password
  db_subnet_group_name   = aws_db_subnet_group.vector[0].name
  vpc_security_group_ids = [aws_security_group.vector_db[0].id]

  # Serverless v2 scaling configuration
  serverlessv2_scaling_configuration {
    min_capacity = 0.5 # Minimum ACU (Aurora Capacity Units)
    max_capacity = 1.0 # Maximum ACU
  }

  # Backup configuration
  backup_retention_period = 7
  preferred_backup_window = "03:00-04:00"

  # Maintenance window
  preferred_maintenance_window = "sun:04:00-sun:05:00"

  # Encryption
  storage_encrypted = true

  # Skip final snapshot for demo environment
  skip_final_snapshot = true

  # Enable deletion protection in production
  deletion_protection = false

  tags = {
    Name        = "${var.project_name}-${var.environment}-vector-cluster"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Vector database with pgvector"
  }
}

# Aurora Serverless v2 Instance
resource "aws_rds_cluster_instance" "vector" {
  count              = var.vector_db_type == "aurora_pgvector" ? 1 : 0
  identifier         = "${var.project_name}-${var.environment}-vector-instance"
  cluster_identifier = aws_rds_cluster.vector[0].id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.vector[0].engine
  engine_version     = aws_rds_cluster.vector[0].engine_version

  # Performance Insights
  performance_insights_enabled = false # Disable to reduce costs

  tags = {
    Name        = "${var.project_name}-${var.environment}-vector-instance"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# OpenSearch Serverless (Alternative - Higher Cost)
# ============================================================================

# OpenSearch Serverless Collection
resource "aws_opensearchserverless_collection" "vector" {
  count = var.vector_db_type == "opensearch" ? 1 : 0
  name  = "${var.project_name}-${var.environment}-ipc-sections"
  type  = "VECTORSEARCH"

  tags = {
    Name        = "${var.project_name}-${var.environment}-opensearch-collection"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Vector search for IPC sections"
  }
}

# OpenSearch Serverless Security Policy (Encryption)
resource "aws_opensearchserverless_security_policy" "encryption" {
  count = var.vector_db_type == "opensearch" ? 1 : 0
  name  = "${var.project_name}-${var.environment}-encryption-policy"
  type  = "encryption"

  policy = jsonencode({
    Rules = [
      {
        ResourceType = "collection"
        Resource = [
          "collection/${var.project_name}-${var.environment}-ipc-sections"
        ]
      }
    ]
    AWSOwnedKey = true
  })
}

# OpenSearch Serverless Network Policy
resource "aws_opensearchserverless_security_policy" "network" {
  count = var.vector_db_type == "opensearch" ? 1 : 0
  name  = "${var.project_name}-${var.environment}-network-policy"
  type  = "network"

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/${var.project_name}-${var.environment}-ipc-sections"
          ]
        }
      ]
      AllowFromPublic = false
      SourceVPCEs     = []
    }
  ])
}

# OpenSearch Serverless Access Policy
resource "aws_opensearchserverless_access_policy" "vector" {
  count = var.vector_db_type == "opensearch" ? 1 : 0
  name  = "${var.project_name}-${var.environment}-access-policy"
  type  = "data"

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/${var.project_name}-${var.environment}-ipc-sections"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
        },
        {
          ResourceType = "index"
          Resource = [
            "index/${var.project_name}-${var.environment}-ipc-sections/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
        }
      ]
      Principal = [
        aws_iam_role.ec2.arn
      ]
    }
  ])
}

# ============================================================================
# Outputs
# ============================================================================

output "vector_db_type" {
  description = "Type of vector database deployed"
  value       = var.vector_db_type
}

# Aurora pgvector outputs
output "vector_db_endpoint" {
  description = "Vector database endpoint (Aurora pgvector)"
  value       = var.vector_db_type == "aurora_pgvector" ? aws_rds_cluster.vector[0].endpoint : null
}

output "vector_db_reader_endpoint" {
  description = "Vector database reader endpoint (Aurora pgvector)"
  value       = var.vector_db_type == "aurora_pgvector" ? aws_rds_cluster.vector[0].reader_endpoint : null
}

output "vector_db_port" {
  description = "Vector database port (Aurora pgvector)"
  value       = var.vector_db_type == "aurora_pgvector" ? aws_rds_cluster.vector[0].port : null
}

output "vector_db_name" {
  description = "Vector database name"
  value       = var.vector_db_type == "aurora_pgvector" ? aws_rds_cluster.vector[0].database_name : null
}

# OpenSearch outputs
output "opensearch_collection_endpoint" {
  description = "OpenSearch Serverless collection endpoint"
  value       = var.vector_db_type == "opensearch" ? aws_opensearchserverless_collection.vector[0].collection_endpoint : null
}

output "opensearch_collection_id" {
  description = "OpenSearch Serverless collection ID"
  value       = var.vector_db_type == "opensearch" ? aws_opensearchserverless_collection.vector[0].id : null
}

output "vector_db_configuration" {
  description = "Vector database configuration summary"
  value = var.vector_db_type == "aurora_pgvector" ? {
    type           = "Aurora PostgreSQL with pgvector"
    engine_version = "15.4"
    min_capacity   = "0.5 ACU"
    max_capacity   = "1.0 ACU"
    estimated_cost = "$43.20/month"
    } : {
    type           = "OpenSearch Serverless"
    min_ocu        = "2 OCU"
    estimated_cost = "$345.60/month"
  }
}
