#!/bin/bash

###############################################################################
# AFIRGen Frontend - Smoke Tests
# 
# Quick validation tests to verify deployment is working
# 
# Usage: ./scripts/smoke-tests.sh <environment-url>
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
BASE_URL="${1:-http://localhost}"
TIMEOUT=10

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AFIRGen Frontend - Smoke Tests${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Testing: $BASE_URL"
echo ""

PASSED=0
FAILED=0

# Test function
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected="$3"
    
    echo -n "Testing $test_name... "
    
    result=$(eval "$test_command" 2>/dev/null || echo "FAILED")
    
    if [[ "$result" == *"$expected"* ]]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        echo "  Expected: $expected"
        echo "  Got: $result"
        ((FAILED++))
        return 1
    fi
}

# Test 1: Homepage loads
run_test "Homepage loads" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time $TIMEOUT '$BASE_URL'" \
    "200"

# Test 2: HTML content present
run_test "HTML content" \
    "curl -s --max-time $TIMEOUT '$BASE_URL' | grep -o 'AFIRGen'" \
    "AFIRGen"

# Test 3: CSS loads
run_test "CSS loads" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time $TIMEOUT '$BASE_URL/css/main.css'" \
    "200"

# Test 4: JavaScript loads
run_test "JavaScript loads" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time $TIMEOUT '$BASE_URL/js/app.js'" \
    "200"

# Test 5: Service Worker present
run_test "Service Worker" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time $TIMEOUT '$BASE_URL/sw.js'" \
    "200"

# Test 6: Manifest present
run_test "PWA Manifest" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time $TIMEOUT '$BASE_URL/manifest.json'" \
    "200"

# Test 7: Security headers
run_test "Security headers (X-Frame-Options)" \
    "curl -s -I --max-time $TIMEOUT '$BASE_URL' | grep -i 'x-frame-options'" \
    "SAMEORIGIN"

# Test 8: Gzip compression
run_test "Gzip compression" \
    "curl -s -I -H 'Accept-Encoding: gzip' --max-time $TIMEOUT '$BASE_URL/css/main.css' | grep -i 'content-encoding'" \
    "gzip"

# Test 9: Cache headers for static assets
run_test "Cache headers" \
    "curl -s -I --max-time $TIMEOUT '$BASE_URL/css/main.css' | grep -i 'cache-control'" \
    "public"

# Test 10: No cache for HTML
run_test "No cache for HTML" \
    "curl -s -I --max-time $TIMEOUT '$BASE_URL' | grep -i 'cache-control'" \
    "no-store"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Results${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo -e "Total:  $((PASSED + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All smoke tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
