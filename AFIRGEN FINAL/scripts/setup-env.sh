#!/bin/bash
# setup-env.sh
# Automated script to generate .env file with secure keys

set -e  # Exit on error

echo "=========================================="
echo "AFIRGen Environment Setup Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

ENV_FILE="${ENV_FILE:-.env}"

# Check if .env already exists
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Warning: $ENV_FILE already exists${NC}"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# Function to generate secure random key
generate_key() {
    openssl rand -hex 32
}

# Get RDS endpoint from Terraform output (if available)
RDS_ENDPOINT=""
if command -v terraform &> /dev/null; then
    if [ -f "terraform.tfstate" ] || [ -f "../terraform/free-tier/terraform.tfstate" ]; then
        echo -e "${YELLOW}Fetching RDS endpoint from Terraform...${NC}"
        RDS_ENDPOINT=$(terraform output -raw rds_endpoint 2>/dev/null || echo "")
        if [ -n "$RDS_ENDPOINT" ]; then
            echo -e "${GREEN}✓ Found RDS endpoint: $RDS_ENDPOINT${NC}"
        fi
    fi
fi

# Get EC2 public IP from Terraform output (if available)
EC2_IP=""
if command -v terraform &> /dev/null; then
    if [ -f "terraform.tfstate" ] || [ -f "../terraform/free-tier/terraform.tfstate" ]; then
        echo -e "${YELLOW}Fetching EC2 IP from Terraform...${NC}"
        EC2_IP=$(terraform output -raw ec2_public_ip 2>/dev/null || echo "")
        if [ -n "$EC2_IP" ]; then
            echo -e "${GREEN}✓ Found EC2 IP: $EC2_IP${NC}"
        fi
    fi
fi

# Prompt for RDS endpoint if not found
if [ -z "$RDS_ENDPOINT" ]; then
    echo ""
    echo -e "${YELLOW}Enter RDS endpoint (or press Enter for localhost):${NC}"
    read -r RDS_ENDPOINT
    RDS_ENDPOINT=${RDS_ENDPOINT:-localhost}
fi

# Prompt for MySQL password
echo ""
echo -e "${YELLOW}Enter MySQL password (or press Enter to generate):${NC}"
read -rs MYSQL_PASSWORD
echo
if [ -z "$MYSQL_PASSWORD" ]; then
    MYSQL_PASSWORD=$(generate_key)
    echo -e "${GREEN}✓ Generated MySQL password${NC}"
fi

# Generate secure keys
echo ""
echo -e "${YELLOW}Generating secure keys...${NC}"
FIR_AUTH_KEY=$(generate_key)
API_KEY=$(generate_key)
echo -e "${GREEN}✓ Keys generated${NC}"

# Determine CORS origins
if [ -n "$EC2_IP" ]; then
    CORS_ORIGINS="http://${EC2_IP},https://${EC2_IP},http://${EC2_IP}:8000"
    API_BASE_URL="http://${EC2_IP}:8000"
else
    CORS_ORIGINS="http://localhost:3000,http://localhost:8000"
    API_BASE_URL="http://localhost:8000"
fi

# Create .env file
echo ""
echo -e "${YELLOW}Creating $ENV_FILE...${NC}"

cat > "$ENV_FILE" << EOF
# AFIRGen Environment Configuration
# Generated on $(date)

# MySQL Database Configuration
MYSQL_HOST=${RDS_ENDPOINT}
MYSQL_PORT=3306
MYSQL_USER=admin
MYSQL_PASSWORD=${MYSQL_PASSWORD}
MYSQL_DB=fir_db

# Application Configuration
PORT=8000
FIR_AUTH_KEY=${FIR_AUTH_KEY}
API_KEY=${API_KEY}

# Model Server Configuration
MODEL_SERVER_PORT=8001
ASR_OCR_PORT=8002

# CORS Configuration
CORS_ORIGINS=${CORS_ORIGINS}

# Rate Limiting Configuration
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Security Configuration
ENFORCE_HTTPS=false
SESSION_TIMEOUT=3600

# Frontend Configuration
API_BASE_URL=${API_BASE_URL}
ENVIRONMENT=production
ENABLE_DEBUG=false
FRONTEND_PORT=80

# Backup Configuration
BACKUP_RETENTION_DAYS=7

# AWS Configuration
AWS_REGION=us-east-1
USE_AWS_SECRETS=false
EOF

echo -e "${GREEN}✓ $ENV_FILE created successfully${NC}"
echo ""

# Display important information
echo "=========================================="
echo "Configuration Summary"
echo "=========================================="
echo ""
echo "MySQL Host: ${RDS_ENDPOINT}"
echo "MySQL User: admin"
echo "MySQL Password: ${MYSQL_PASSWORD:0:8}... (saved in .env)"
echo ""
echo "API Key: ${API_KEY:0:16}... (saved in .env)"
echo "Auth Key: ${FIR_AUTH_KEY:0:16}... (saved in .env)"
echo ""
echo "API Base URL: ${API_BASE_URL}"
echo "CORS Origins: ${CORS_ORIGINS}"
echo ""
echo -e "${GREEN}=========================================="
echo "Environment setup complete!"
echo "==========================================${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT: Keep your .env file secure!${NC}"
echo "Add it to .gitignore to prevent committing secrets."
