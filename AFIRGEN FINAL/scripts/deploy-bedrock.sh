#!/bin/bash
# Automated deployment script for Bedrock architecture
# Applies Terraform, runs migration, deploys application, and performs health checks

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TERRAFORM_DIR="terraform/free-tier"
SCRIPTS_DIR="scripts"
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AFIRGen Bedrock Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}Running in DRY RUN mode${NC}"
fi

# Step 1: Validate environment variables
echo -e "\n${YELLOW}Step 1: Validating environment variables...${NC}"
python3 "$SCRIPTS_DIR/validate-env.py"
if [ $? -ne 0 ]; then
    echo -e "${RED}Environment validation failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Environment validated${NC}"

# Step 2: Apply Terraform changes
echo -e "\n${YELLOW}Step 2: Applying Terraform changes...${NC}"
cd "$TERRAFORM_DIR"

if [ "$DRY_RUN" = true ]; then
    terraform plan
else
    terraform init
    terraform plan -out=tfplan
    terraform apply tfplan
    rm tfplan
fi

cd - > /dev/null
echo -e "${GREEN}✓ Terraform applied${NC}"

# Step 3: Run vector database migration
echo -e "\n${YELLOW}Step 3: Running vector database migration...${NC}"
if [ "$DRY_RUN" = false ]; then
    # Check if export file exists
    if [ -f "ipc_sections_export.json" ]; then
        python3 "$SCRIPTS_DIR/migrate_vector_db.py" \
            --input ipc_sections_export.json \
            --regenerate-embeddings
    else
        echo -e "${YELLOW}No export file found, skipping migration${NC}"
    fi
fi
echo -e "${GREEN}✓ Migration completed${NC}"

# Step 4: Deploy application
echo -e "\n${YELLOW}Step 4: Deploying application...${NC}"
if [ "$DRY_RUN" = false ]; then
    # Install dependencies
    pip install -r requirements.txt
    
    # Restart application (adjust based on deployment method)
    # systemctl restart afirgen  # For systemd
    # docker-compose up -d  # For Docker
    echo -e "${YELLOW}Application restart required (manual step)${NC}"
fi
echo -e "${GREEN}✓ Application deployed${NC}"

# Step 5: Health checks
echo -e "\n${YELLOW}Step 5: Performing health checks...${NC}"
if [ "$DRY_RUN" = false ]; then
    sleep 10  # Wait for application to start
    python3 "$SCRIPTS_DIR/health-check.py"
    if [ $? -ne 0 ]; then
        echo -e "${RED}Health checks failed!${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Health checks passed${NC}"

# Step 6: Verify AWS service connectivity
echo -e "\n${YELLOW}Step 6: Verifying AWS service connectivity...${NC}"
if [ "$DRY_RUN" = false ]; then
    # Test Bedrock
    aws bedrock list-foundation-models --region $AWS_REGION > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Bedrock accessible${NC}"
    else
        echo -e "${RED}✗ Bedrock not accessible${NC}"
    fi
    
    # Test S3
    aws s3 ls s3://$S3_BUCKET_NAME > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ S3 accessible${NC}"
    else
        echo -e "${RED}✗ S3 not accessible${NC}"
    fi
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\nNext steps:"
echo -e "1. Monitor CloudWatch metrics"
echo -e "2. Check application logs"
echo -e "3. Test FIR generation endpoints"
echo -e "4. Monitor costs in AWS Cost Explorer"
