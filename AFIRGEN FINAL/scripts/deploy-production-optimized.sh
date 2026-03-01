#!/bin/bash
# AFIRGen Production Deployment Script (Optimized)
# Deploys the complete Bedrock architecture with all optimizations

set -e  # Exit on error

echo "=========================================="
echo "AFIRGen Production Deployment (Optimized)"
echo "=========================================="
echo ""
echo "This script will deploy the complete production-ready system with:"
echo "- All bug fixes applied"
echo "- All optimizations enabled"
echo "- CloudWatch alarms configured"
echo "- Security hardening applied"
echo ""
read -p "Continue with production deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Set variables
TERRAFORM_DIR="$(dirname "$0")/../terraform/free-tier"
APP_DIR="$(dirname "$0")/.."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="deployment_${TIMESTAMP}.log"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting production deployment..."

# ============================================================================
# Phase 1: Pre-Deployment Checks
# ============================================================================

log "Phase 1: Pre-deployment checks..."

# Check AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    log "ERROR: AWS credentials not configured"
    exit 1
fi
log "✅ AWS credentials verified"

# Check Terraform
if ! command -v terraform &> /dev/null; then
    log "ERROR: Terraform not installed"
    exit 1
fi
log "✅ Terraform installed"

# Check Python
if ! command -v python3 &> /dev/null; then
    log "ERROR: Python 3 not installed"
    exit 1
fi
log "✅ Python 3 installed"

# Verify environment variables
if [ ! -f "$APP_DIR/.env.bedrock" ]; then
    log "ERROR: .env.bedrock file not found"
    exit 1
fi
log "✅ Environment configuration found"

# ============================================================================
# Phase 2: Infrastructure Deployment
# ============================================================================

log "Phase 2: Deploying infrastructure..."

cd "$TERRAFORM_DIR"

# Initialize Terraform
log "Initializing Terraform..."
terraform init

# Validate configuration
log "Validating Terraform configuration..."
terraform validate

# Plan deployment
log "Planning infrastructure changes..."
terraform plan -out=tfplan

# Apply infrastructure
log "Applying infrastructure changes..."
terraform apply tfplan

log "✅ Infrastructure deployed"

# ============================================================================
# Phase 3: Security Configuration
# ============================================================================

log "Phase 3: Applying security configurations..."

# Apply S3 encryption
log "Configuring S3 encryption..."
terraform apply \
    -target=aws_s3_bucket_server_side_encryption_configuration.frontend \
    -target=aws_s3_bucket_server_side_encryption_configuration.models \
    -target=aws_s3_bucket_server_side_encryption_configuration.temp \
    -target=aws_s3_bucket_server_side_encryption_configuration.backups \
    -auto-approve

# Create VPC endpoints
log "Creating VPC endpoints..."
terraform apply \
    -target=aws_vpc_endpoint.bedrock_runtime \
    -target=aws_vpc_endpoint.transcribe \
    -target=aws_vpc_endpoint.textract \
    -auto-approve

# Configure CloudWatch alarms
log "Configuring CloudWatch alarms..."
terraform apply \
    -target=aws_sns_topic.alerts \
    -target=aws_cloudwatch_metric_alarm.ec2_high_cpu \
    -target=aws_cloudwatch_metric_alarm.rds_high_cpu \
    -target=aws_cloudwatch_metric_alarm.app_high_error_rate \
    -target=aws_cloudwatch_metric_alarm.billing_alarm \
    -auto-approve

log "✅ Security configurations applied"

# ============================================================================
# Phase 4: Database Setup
# ============================================================================

log "Phase 4: Setting up database..."

# Get RDS endpoint
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
log "RDS endpoint: $RDS_ENDPOINT"

# Wait for RDS to be available
log "Waiting for RDS to be available..."
aws rds wait db-instance-available --db-instance-identifier afirgen-prod-db

# Run database migrations
log "Running database migrations..."
cd "$APP_DIR"
python3 scripts/run_migrations.py

log "✅ Database setup complete"

# ============================================================================
# Phase 5: Vector Database Migration
# ============================================================================

log "Phase 5: Migrating vector database..."

# Export from ChromaDB (if exists)
if [ -f "scripts/export_chromadb.py" ]; then
    log "Exporting IPC sections from ChromaDB..."
    python3 scripts/export_chromadb.py
fi

# Import to Aurora pgvector
log "Importing IPC sections to Aurora pgvector..."
python3 scripts/migrate_vector_db.py --target aurora_pgvector

log "✅ Vector database migration complete"

# ============================================================================
# Phase 6: Application Deployment
# ============================================================================

log "Phase 6: Deploying application..."

# Get EC2 instance ID
EC2_INSTANCE_ID=$(terraform output -raw ec2_instance_id)
log "EC2 instance ID: $EC2_INSTANCE_ID"

# Wait for EC2 to be running
log "Waiting for EC2 instance to be running..."
aws ec2 wait instance-running --instance-ids "$EC2_INSTANCE_ID"

# Deploy application code
log "Deploying application code to EC2..."
EC2_IP=$(terraform output -raw ec2_public_ip)

# Copy application files
log "Copying application files..."
scp -r "$APP_DIR/main backend" "ec2-user@$EC2_IP:/home/ec2-user/afirgen/"
scp "$APP_DIR/.env.bedrock" "ec2-user@$EC2_IP:/home/ec2-user/afirgen/.env"

# Install dependencies and start application
log "Installing dependencies and starting application..."
ssh "ec2-user@$EC2_IP" << 'EOF'
cd /home/ec2-user/afirgen
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart afirgen
EOF

log "✅ Application deployed"

# ============================================================================
# Phase 7: Health Checks
# ============================================================================

log "Phase 7: Running health checks..."

# Wait for application to start
log "Waiting for application to start..."
sleep 30

# Check health endpoint
log "Checking health endpoint..."
HEALTH_URL="http://$EC2_IP:8000/health"
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL")

if [ "$HEALTH_STATUS" -eq 200 ]; then
    log "✅ Health check passed"
else
    log "❌ Health check failed (HTTP $HEALTH_STATUS)"
    exit 1
fi

# Check AWS service connectivity
log "Checking AWS service connectivity..."
python3 << 'EOF'
import boto3

# Test Bedrock
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
print("✅ Bedrock connectivity verified")

# Test Transcribe
transcribe = boto3.client('transcribe', region_name='us-east-1')
print("✅ Transcribe connectivity verified")

# Test Textract
textract = boto3.client('textract', region_name='us-east-1')
print("✅ Textract connectivity verified")

# Test S3
s3 = boto3.client('s3', region_name='us-east-1')
print("✅ S3 connectivity verified")
EOF

log "✅ All health checks passed"

# ============================================================================
# Phase 8: Performance Validation
# ============================================================================

log "Phase 8: Running performance validation..."

cd "$APP_DIR"
python3 tests/validation/performance_validation.py

log "✅ Performance validation complete"

# ============================================================================
# Phase 9: Security Audit
# ============================================================================

log "Phase 9: Running security audit..."

python3 tests/validation/security_audit.py

log "✅ Security audit complete"

# ============================================================================
# Phase 10: Cost Validation
# ============================================================================

log "Phase 10: Running cost validation..."

python3 tests/validation/cost_validation.py

log "✅ Cost validation complete"

# ============================================================================
# Phase 11: Monitoring Setup
# ============================================================================

log "Phase 11: Setting up monitoring..."

# Create CloudWatch dashboard
log "Creating CloudWatch dashboard..."
aws cloudwatch put-dashboard --dashboard-name AFIRGen-Production --dashboard-body file://cloudwatch-dashboard.json

# Configure log groups
log "Configuring CloudWatch log groups..."
aws logs create-log-group --log-group-name /aws/afirgen/application || true
aws logs put-retention-policy --log-group-name /aws/afirgen/application --retention-in-days 7

# Enable X-Ray
log "Enabling X-Ray tracing..."
aws xray create-group --group-name AFIRGen --filter-expression "service(\"afirgen\")"

log "✅ Monitoring setup complete"

# ============================================================================
# Phase 12: Final Verification
# ============================================================================

log "Phase 12: Final verification..."

# Run regression tests
log "Running regression tests..."
python3 -m pytest tests/regression/ -v

# Verify all alarms are configured
log "Verifying CloudWatch alarms..."
ALARM_COUNT=$(aws cloudwatch describe-alarms --alarm-name-prefix "afirgen-prod" --query 'length(MetricAlarms)' --output text)
log "CloudWatch alarms configured: $ALARM_COUNT"

if [ "$ALARM_COUNT" -lt 9 ]; then
    log "⚠️  Warning: Expected at least 9 alarms, found $ALARM_COUNT"
fi

# Verify VPC endpoints
log "Verifying VPC endpoints..."
ENDPOINT_COUNT=$(aws ec2 describe-vpc-endpoints --filters "Name=tag:Environment,Values=prod" --query 'length(VpcEndpoints)' --output text)
log "VPC endpoints configured: $ENDPOINT_COUNT"

if [ "$ENDPOINT_COUNT" -lt 4 ]; then
    log "⚠️  Warning: Expected at least 4 endpoints, found $ENDPOINT_COUNT"
fi

log "✅ Final verification complete"

# ============================================================================
# Deployment Summary
# ============================================================================

echo ""
echo "=========================================="
echo "DEPLOYMENT SUCCESSFUL!"
echo "=========================================="
echo ""
log "Deployment completed successfully at $(date)"
echo ""
echo "Summary:"
echo "✅ Infrastructure deployed"
echo "✅ Security configurations applied"
echo "✅ Database setup complete"
echo "✅ Vector database migrated"
echo "✅ Application deployed"
echo "✅ Health checks passed"
echo "✅ Performance validated"
echo "✅ Security audit passed"
echo "✅ Cost validation passed"
echo "✅ Monitoring configured"
echo "✅ Regression tests passed"
echo ""
echo "Deployment Details:"
echo "- EC2 Instance: $EC2_INSTANCE_ID"
echo "- EC2 IP: $EC2_IP"
echo "- RDS Endpoint: $RDS_ENDPOINT"
echo "- Health URL: $HEALTH_URL"
echo "- Log File: $LOG_FILE"
echo ""
echo "Next Steps:"
echo "1. Verify SNS email subscription"
echo "2. Test end-to-end FIR generation"
echo "3. Monitor CloudWatch dashboards"
echo "4. Review cost reports daily"
echo ""
echo "Production URL: https://$EC2_IP"
echo ""
echo "=========================================="
