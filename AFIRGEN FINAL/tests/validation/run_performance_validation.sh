#!/bin/bash
# Performance Validation Runner for Linux/Mac
# This script runs the performance validation against the AFIRGen application

echo "============================================================"
echo "AFIRGen Bedrock Migration - Performance Validation"
echo "============================================================"
echo ""

# Check if URL argument is provided
if [ -z "$1" ]; then
    BASE_URL="http://localhost:8000"
    echo "Using default URL: $BASE_URL"
else
    BASE_URL="$1"
    echo "Using provided URL: $BASE_URL"
fi

echo ""
echo "Checking if application is accessible..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/health)

if [ $? -ne 0 ] || [ "$HTTP_STATUS" != "200" ]; then
    echo ""
    echo "ERROR: Cannot connect to application at $BASE_URL"
    echo "HTTP Status: $HTTP_STATUS"
    echo ""
    echo "Please ensure the application is running:"
    echo "  cd 'AFIRGEN FINAL/main backend'"
    echo "  python agentv5.py"
    echo ""
    exit 1
fi

echo "Application is accessible (HTTP $HTTP_STATUS). Starting performance validation..."
echo ""

# Run the performance validation script
python3 performance_validation.py $BASE_URL

if [ $? -ne 0 ]; then
    echo ""
    echo "============================================================"
    echo "PERFORMANCE VALIDATION FAILED"
    echo "============================================================"
    echo ""
    echo "Please review the output above for details."
    echo "Check the troubleshooting guide in README.md"
    echo ""
    exit 1
else
    echo ""
    echo "============================================================"
    echo "PERFORMANCE VALIDATION COMPLETED"
    echo "============================================================"
    echo ""
    echo "Report saved to: performance_validation_report.json"
    echo ""
fi
