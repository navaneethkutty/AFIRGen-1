#!/bin/bash
# Pre-Deployment Verification Script
# Checks all prerequisites before production deployment

set -e

echo "=========================================="
echo "AFIRGen Pre-Deployment Verification"
echo "=========================================="
echo ""

CHECKS_PASSED=0
CHECKS_FAILED=0
WARNINGS=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check function
check() {
    local name="$1"
    local command="$2"
    
    echo -n "Checking $name... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((CHECKS_FAILED++))
        return 1
    fi
}

# Warning function
warn() {
    local name="$1"
    local message="$2"
    
    echo -e "${YELLOW}⚠️  WARNING: $name${NC}"
    echo "   $message"
    ((WARNINGS++))
}

echo "Running pre-deployment checks..."
echo ""

# ============================================================================
# 1. System Requirements
# ============================================================================

echo "1. System Requirements"
echo "----------------------"

check "AWS CLI" "command -v aws"
check "Terraform" "command -v terraform"
check "Python 3" "command -v python3"
check "SSH" "command -v ssh"
check "Git" "command -v git"

echo ""

# ============================================================================
# 2. AWS Configuration
# ============================================================================

echo "2. AWS Configuration"
echo "--------------------"

check "AWS Credentials" "aws sts get-caller-identity"

# Check AWS region
AWS_REGION=$(aws configure get region)
if [ "$AWS_REGION" = "us-east-1" ]; then
    echo -e "AWS Region: ${GREEN}✅ us-east-1${NC}"
    ((CHECKS_PASSED++))
else
    echo -e "AWS Region: ${YELLOW}⚠️  $AWS_REGION (expected us-east-1)${NC}"
    ((WARNINGS++))
fi

# Check AWS account
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")
echo "AWS Account: $AWS_ACCOUNT"

echo ""

# ============================================================================
# 3. Environment Configuration
# ============================================================================

echo "3. Environment Configuration"
echo "----------------------------"

APP_DIR="$(dirname "$0")/.."

check ".env.bedrock file" "test -f '$APP_DIR/.env.bedrock'"
check "terraform.tfvars" "test -f '$APP_DIR/terraform/free-tier/terraform.tfvars'"

echo ""

# ============================================================================
# 4. Terraform Validation
# ============================================================================

echo "4. Terraform Validation"
echo "-----------------------"

cd "$APP_DIR/terraform/free-tier"

check "Terraform init" "terraform init -backend=false"
check "Terraform validate" "terraform validate"

cd - > /dev/null

echo ""

# ============================================================================
# 5. Code Quality
# ============================================================================

echo "5. Code Quality"
echo "---------------"

cd "$APP_DIR"

# Check if minimal tests exist
if [ -f "tests/api/test_endpoints_minimal.py" ]; then
    echo -n "Running minimal tests... "
    if python3 tests/api/test_endpoints_minimal.py > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((CHECKS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((CHECKS_FAILED++))
    fi
else
    warn "Minimal tests" "test_endpoints_minimal.py not found"
fi

# Check bugs.json
if [ -f "bugs.json" ]; then
    BUGS_FIXED=$(python3 -c "import json; data=json.load(open('bugs.json')); print(sum(1 for b in data if b['status']=='Fixed'))" 2>/dev/null || echo "0")
    TOTAL_BUGS=$(python3 -c "import json; print(len(json.load(open('bugs.json'))))" 2>/dev/null || echo "0")
    
    if [ "$BUGS_FIXED" = "$TOTAL_BUGS" ] && [ "$TOTAL_BUGS" -gt 0 ]; then
        echo -e "Bugs Fixed: ${GREEN}✅ $BUGS_FIXED/$TOTAL_BUGS${NC}"
        ((CHECKS_PASSED++))
    else
        echo -e "Bugs Fixed: ${RED}❌ $BUGS_FIXED/$TOTAL_BUGS${NC}"
        ((CHECKS_FAILED++))
    fi
else
    warn "Bug tracking" "bugs.json not found"
fi

cd - > /dev/null

echo ""

# ============================================================================
# 6. Dependencies
# ============================================================================

echo "6. Dependencies"
echo "---------------"

cd "$APP_DIR"

if [ -f "requirements.txt" ]; then
    echo -n "Checking Python dependencies... "
    if pip3 install --dry-run -r requirements.txt > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((CHECKS_PASSED++))
    else
        echo -e "${YELLOW}⚠️  Some packages may not be available${NC}"
        ((WARNINGS++))
    fi
else
    warn "Dependencies" "requirements.txt not found"
fi

cd - > /dev/null

echo ""

# ============================================================================
# 7. Scripts
# ============================================================================

echo "7. Deployment Scripts"
echo "---------------------"

check "Deployment script exists" "test -f '$APP_DIR/scripts/deploy-production-optimized.sh'"
check "Deployment script executable" "test -x '$APP_DIR/scripts/deploy-production-optimized.sh'"
check "Rollback script exists" "test -f '$APP_DIR/scripts/rollback-to-gguf.sh'"
check "Rollback script executable" "test -x '$APP_DIR/scripts/rollback-to-gguf.sh'"

echo ""

# ============================================================================
# 8. Documentation
# ============================================================================

echo "8. Documentation"
echo "----------------"

check "Production readiness report" "test -f '$APP_DIR/FINAL-PRODUCTION-READINESS-REPORT.md'"
check "Deployment README" "test -f '$APP_DIR/PRODUCTION-DEPLOYMENT-README.md'"
check "Bug fix report" "test -f '$APP_DIR/COMPLETE-BUG-FIX-REPORT.md'"

echo ""

# ============================================================================
# Summary
# ============================================================================

echo "=========================================="
echo "VERIFICATION SUMMARY"
echo "=========================================="
echo ""
echo -e "Checks Passed:  ${GREEN}$CHECKS_PASSED${NC}"
echo -e "Checks Failed:  ${RED}$CHECKS_FAILED${NC}"
echo -e "Warnings:       ${YELLOW}$WARNINGS${NC}"
echo ""

TOTAL_CHECKS=$((CHECKS_PASSED + CHECKS_FAILED))
if [ $TOTAL_CHECKS -gt 0 ]; then
    SUCCESS_RATE=$((CHECKS_PASSED * 100 / TOTAL_CHECKS))
    echo "Success Rate: $SUCCESS_RATE%"
    echo ""
fi

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}=========================================="
    echo "✅ ALL CHECKS PASSED"
    echo "==========================================${NC}"
    echo ""
    echo "System is ready for production deployment!"
    echo ""
    echo "Next steps:"
    echo "1. Review PRE-DEPLOYMENT-CHECKLIST.md"
    echo "2. Notify stakeholders"
    echo "3. Run deployment script:"
    echo "   cd 'AFIRGEN FINAL/scripts'"
    echo "   ./deploy-production-optimized.sh"
    echo ""
    exit 0
else
    echo -e "${RED}=========================================="
    echo "❌ DEPLOYMENT BLOCKED"
    echo "==========================================${NC}"
    echo ""
    echo "Please fix the failed checks before deploying."
    echo ""
    echo "Common fixes:"
    echo "- AWS credentials: aws configure"
    echo "- Terraform: terraform init"
    echo "- Environment: cp .env.example .env.bedrock"
    echo ""
    exit 1
fi
