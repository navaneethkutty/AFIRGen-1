#!/bin/bash
# Simple test script for EC2 backend

BASE_URL="http://18.206.148.182:8000"
API_KEY="dev-test-key-12345678901234567890123456789012"

echo "=========================================="
echo "AFIRGen Backend Test - EC2"
echo "=========================================="
echo ""

# Test 1: Health Check
echo "1. Testing Health Endpoint..."
curl -s -X GET "$BASE_URL/health" \
  -H "X-API-Key: $API_KEY" | python3 -m json.tool
echo ""
echo ""

# Test 2: Process Text Input
echo "2. Testing /process endpoint with text input..."
RESPONSE=$(curl -s -X POST "$BASE_URL/process" \
  -H "X-API-Key: $API_KEY" \
  -F "complaint_text=A person stole my mobile phone at the market yesterday")

echo "$RESPONSE" | python3 -m json.tool
SESSION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', ''))" 2>/dev/null)
echo ""
echo "Session ID: $SESSION_ID"
echo ""

if [ -z "$SESSION_ID" ]; then
    echo "ERROR: Failed to get session_id from /process response"
    exit 1
fi

# Test 3: Poll Session Status
echo "3. Polling session status..."
for i in {1..10}; do
    echo "Poll attempt $i/10..."
    STATUS_RESPONSE=$(curl -s -X GET "$BASE_URL/session/$SESSION_ID" \
      -H "X-API-Key: $API_KEY")
    
    echo "$STATUS_RESPONSE" | python3 -m json.tool
    
    STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null)
    
    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo "✅ FIR generation completed!"
        break
    elif [ "$STATUS" = "error" ]; then
        echo ""
        echo "❌ FIR generation failed"
        break
    fi
    
    sleep 3
done

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="
