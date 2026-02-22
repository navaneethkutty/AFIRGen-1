#!/bin/bash
# Comprehensive Deployment Readiness Audit Script
# Runs all checks and generates a detailed report

echo "=========================================="
echo "AFIRGen Deployment Readiness Audit"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track results
PASSED=0
FAILED=0
WARNINGS=0

# Function to print test result
print_result() {
    local status=$1
    local message=$2
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $message"
        ((PASSED++))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}✗${NC} $message"
        ((FAILED++))
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} $message"
        ((WARNINGS++))
    else
        echo -e "${BLUE}ℹ${NC} $message"
    fi
}

# 1. Check Python environment
echo -e "${BLUE}Checking Python Environment...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_result "PASS" "Python installed: $PYTHON_VERSION"
else
    print_result "FAIL" "Python 3 not found"
fi

# 2. Check required Python packages
echo -e "\n${BLUE}Checking Python Dependencies...${NC}"
if [ -f "AFIRGEN FINAL/main backend/requirements.txt" ]; then
    print_result "PASS" "requirements.txt found"
    
    # Check if key packages are listed
    if grep -q "fastapi" "AFIRGEN FINAL/main backend/requirements.txt"; then
        print_result "PASS" "FastAPI listed in requirements"
    else
        print_result "FAIL" "FastAPI not found in requirements"
    fi
    
    if grep -q "uvicorn" "AFIRGEN FINAL/main backend/requirements.txt"; then
        print_result "PASS" "Uvicorn listed in requirements"
    else
        print_result "FAIL" "Uvicorn not found in requirements"
    fi
else
    print_result "FAIL" "requirements.txt not found"
fi

# 3. Check frontend files
echo -e "\n${BLUE}Checking Frontend Files...${NC}"
FRONTEND_FILES=(
    "AFIRGEN FINAL/frontend/index.html"
    "AFIRGEN FINAL/frontend/js/app.js"
    "AFIRGEN FINAL/frontend/js/api.js"
    "AFIRGEN FINAL/frontend/js/ui.js"
    "AFIRGEN FINAL/frontend/css/main.css"
)

for file in "${FRONTEND_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_result "PASS" "Found: $file"
    else
        print_result "FAIL" "Missing: $file"
    fi
done

# 4. Check backend files
echo -e "\n${BLUE}Checking Backend Files...${NC}"
BACKEND_FILES=(
    "AFIRGEN FINAL/main backend/agentv5.py"
    "AFIRGEN FINAL/main backend/infrastructure/database.py"
    "AFIRGEN FINAL/main backend/infrastructure/config.py"
)

for file in "${BACKEND_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_result "PASS" "Found: $file"
    else
        print_result "FAIL" "Missing: $file"
    fi
done

# 5. Check for security issues
echo -e "\n${BLUE}Checking Security Configuration...${NC}"

# Check for .env file
if [ -f "AFIRGEN FINAL/.env" ]; then
    print_result "PASS" ".env file exists"
    
    # Check if it contains required keys
    if grep -q "API_KEY" "AFIRGEN FINAL/.env"; then
        print_result "PASS" "API_KEY configured in .env"
    else
        print_result "WARN" "API_KEY not found in .env"
    fi
else
    print_result "WARN" ".env file not found (may use environment variables)"
fi

# Check gitignore
if [ -f ".gitignore" ]; then
    print_result "PASS" ".gitignore exists"
    
    if grep -q "__pycache__" ".gitignore"; then
        print_result "PASS" "Python cache files ignored"
    else
        print_result "WARN" "Python cache files may not be ignored"
    fi
    
    if grep -q ".env" ".gitignore"; then
        print_result "PASS" ".env file ignored"
    else
        print_result "FAIL" ".env file not ignored - SECURITY RISK"
    fi
else
    print_result "FAIL" ".gitignore missing"
fi

# 6. Check for hardcoded secrets
echo -e "\n${BLUE}Checking for Hardcoded Secrets...${NC}"
if grep -r "password.*=.*['\"]" "AFIRGEN FINAL/main backend" --include="*.py" | grep -v "get_secret" | grep -v "#" > /dev/null; then
    print_result "WARN" "Possible hardcoded passwords found - review manually"
else
    print_result "PASS" "No obvious hardcoded passwords"
fi

# 7. Check Docker configuration
echo -e "\n${BLUE}Checking Docker Configuration...${NC}"
if [ -f "AFIRGEN FINAL/main backend/Dockerfile" ]; then
    print_result "PASS" "Backend Dockerfile exists"
else
    print_result "WARN" "Backend Dockerfile not found"
fi

if [ -f "AFIRGEN FINAL/frontend/Dockerfile" ]; then
    print_result "PASS" "Frontend Dockerfile exists"
else
    print_result "WARN" "Frontend Dockerfile not found"
fi

# 8. Check for console.log statements (production readiness)
echo -e "\n${BLUE}Checking for Debug Statements...${NC}"
CONSOLE_COUNT=$(grep -r "console\.log" "AFIRGEN FINAL/frontend/js" --include="*.js" | wc -l)
if [ "$CONSOLE_COUNT" -gt 20 ]; then
    print_result "WARN" "Found $CONSOLE_COUNT console.log statements - consider removing for production"
else
    print_result "PASS" "Acceptable number of console.log statements ($CONSOLE_COUNT)"
fi

# 9. Check file permissions
echo -e "\n${BLUE}Checking File Permissions...${NC}"
if [ -f "test_deployment_readiness.py" ]; then
    if [ -x "test_deployment_readiness.py" ]; then
        print_result "PASS" "Test script is executable"
    else
        print_result "WARN" "Test script not executable (chmod +x test_deployment_readiness.py)"
    fi
fi

# 10. Check for TODO/FIXME comments
echo -e "\n${BLUE}Checking for Pending Work...${NC}"
TODO_COUNT=$(grep -r "TODO\|FIXME" "AFIRGEN FINAL" --include="*.py" --include="*.js" | wc -l)
if [ "$TODO_COUNT" -gt 0 ]; then
    print_result "WARN" "Found $TODO_COUNT TODO/FIXME comments - review before deployment"
else
    print_result "PASS" "No TODO/FIXME comments found"
fi

# Print summary
echo ""
echo -e "${BLUE}=========================================="
echo "Audit Summary"
echo -e "==========================================${NC}"
TOTAL=$((PASSED + FAILED + WARNINGS))
echo "Total Checks: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}❌ DEPLOYMENT NOT READY - Fix failed checks before deploying${NC}"
    exit 1
elif [ $WARNINGS -gt 5 ]; then
    echo -e "${YELLOW}⚠️  DEPLOYMENT READY WITH WARNINGS - Review warnings before deploying${NC}"
    exit 0
else
    echo -e "${GREEN}✅ DEPLOYMENT READY - All critical checks passed${NC}"
    exit 0
fi
