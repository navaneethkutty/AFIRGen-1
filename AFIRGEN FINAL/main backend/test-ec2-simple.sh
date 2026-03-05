#!/bin/bash
# AFIRGen EC2 Backend Simple Test Script

EC2_URL="http://18.206.148.182:8000"
API_KEY="dev-test-key-12345678901234567890123456789012"

echo "========================================"
echo "AFIRGen EC2 Backend Test"
echo "========================================"
echo ""

# Test 1: Health Check
echo "Test 1: Health Check"
curl -s "$EC2_URL/health" | python3 -m json.tool
echo ""

# Test 2: Process Text Input
echo "Test 2: Process Text Input"
COMPLAINT="I want to file a complaint against Rajesh Kumar. On March 4th 2026 at 10:30 PM, he broke into my house and stole my laptop worth Rs. 50,000."

SESSION_RESPONSE=$(curl -s -X POST "$EC2_URL/process" \
  -H "X-API-Key: $API_KEY" \
  -F "input_type=text" \
  -F "text=$COMPLAINT" \
  -F "language=en-IN")

echo "$SESSION_RESPONSE" | python3 -m json.tool
SESSION_ID=$(echo "$SESSION_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
echo "Session ID: $SESSION_ID"
echo ""

# Test 3: Poll Session Status
echo "Test 3: Polling Session Status (max 60 seconds)..."
for i in {1..30}; do
  sleep 2
  STATUS_RESPONSE=$(curl -s "$EC2_URL/session/$SESSION_ID" -H "X-API-Key: $API_KEY")
  STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "error")
  
  echo "  Attempt $i - Status: $STATUS"
  
  if [ "$STATUS" = "completed" ]; then
    echo "✓ FIR Generation Completed!"
    echo "$STATUS_RESPONSE" | python3 -m json.tool
    FIR_NUMBER=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['fir_number'])")
    echo "FIR Number: $FIR_NUMBER"
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "✗ FIR Generation Failed"
    echo "$STATUS_RESPONSE" | python3 -m json.tool
    exit 1
  fi
done
echo ""

# Test 4: Get FIR by Number
echo "Test 4: Get FIR by Number"
curl -s "$EC2_URL/fir/$FIR_NUMBER" -H "X-API-Key: $API_KEY" | python3 -m json.tool
echo ""

# Test 5: List FIRs
echo "Test 5: List FIRs"
curl -s "$EC2_URL/firs?limit=5" -H "X-API-Key: $API_KEY" | python3 -m json.tool
echo ""

# Test 6: Authenticate (Generate PDF)
echo "Test 6: Authenticate and Generate PDF"
curl -s -X POST "$EC2_URL/authenticate" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\", \"complainant_signature\": \"Complainant\", \"officer_signature\": \"Officer\"}" | python3 -m json.tool
echo ""

echo "========================================"
echo "All Tests Completed!"
echo "========================================"
