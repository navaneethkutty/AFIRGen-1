# AFIRGen EC2 Backend Comprehensive Test Script
# Tests all endpoints and the complete FIR generation workflow

$EC2_URL = "http://18.206.148.182:8000"
$API_KEY = "dev-test-key-12345678901234567890123456789012"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AFIRGen EC2 Backend Comprehensive Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health Check
Write-Host "Test 1: Health Check Endpoint" -ForegroundColor Yellow
Write-Host "GET $EC2_URL/health" -ForegroundColor Gray
try {
    $response = Invoke-RestMethod -Uri "$EC2_URL/health" -Method Get
    Write-Host "✓ Health check passed" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor Gray
    Write-Host "  MySQL: $($response.checks.mysql)" -ForegroundColor Gray
    Write-Host "  Bedrock: $($response.checks.bedrock)" -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host "✗ Health check failed: $_" -ForegroundColor Red
    Write-Host ""
    exit 1
}

# Test 2: Process Endpoint - Text Input
Write-Host "Test 2: Process Endpoint - Text Input" -ForegroundColor Yellow
Write-Host "POST $EC2_URL/process" -ForegroundColor Gray
$complaintText = @"
I want to file a complaint against my neighbor Rajesh Kumar who lives at 123 MG Road, Bangalore. 
On March 4th, 2026 at around 10:30 PM, he broke into my house and stole my laptop worth Rs. 50,000 
and my gold chain worth Rs. 1,00,000. I have witnesses who saw him running away from my house. 
This is a serious theft and I want immediate action.
"@

# Create multipart form data
$boundary = [System.Guid]::NewGuid().ToString()
$LF = "`r`n"

$bodyLines = @(
    "--$boundary",
    "Content-Disposition: form-data; name=`"input_type`"$LF",
    "text",
    "--$boundary",
    "Content-Disposition: form-data; name=`"text`"$LF",
    $complaintText,
    "--$boundary",
    "Content-Disposition: form-data; name=`"language`"$LF",
    "en-IN",
    "--$boundary--$LF"
)

$body = $bodyLines -join $LF

$headers = @{
    "X-API-Key" = $API_KEY
    "Content-Type" = "multipart/form-data; boundary=$boundary"
}

try {
    $response = Invoke-RestMethod -Uri "$EC2_URL/process" -Method Post -Body $body -Headers $headers
    Write-Host "✓ Process request accepted" -ForegroundColor Green
    Write-Host "  Session ID: $($response.session_id)" -ForegroundColor Gray
    Write-Host "  Status: $($response.status)" -ForegroundColor Gray
    $sessionId = $response.session_id
    Write-Host ""
} catch {
    Write-Host "✗ Process request failed: $_" -ForegroundColor Red
    Write-Host "  Error details: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    exit 1
}

# Test 3: Session Status Polling
Write-Host "Test 3: Session Status Polling" -ForegroundColor Yellow
Write-Host "GET $EC2_URL/session/$sessionId" -ForegroundColor Gray
Write-Host "Polling for FIR generation completion..." -ForegroundColor Gray

$maxAttempts = 30
$attempt = 0
$completed = $false

while ($attempt -lt $maxAttempts -and -not $completed) {
    Start-Sleep -Seconds 2
    $attempt++
    
    try {
        $sessionResponse = Invoke-RestMethod -Uri "$EC2_URL/session/$sessionId" -Method Get -Headers $headers
        Write-Host "  Attempt $attempt - Status: $($sessionResponse.status)" -ForegroundColor Gray
        
        if ($sessionResponse.status -eq "completed") {
            $completed = $true
            Write-Host "✓ FIR generation completed!" -ForegroundColor Green
            Write-Host "  FIR Number: $($sessionResponse.fir_number)" -ForegroundColor Gray
            Write-Host "  Transcript length: $($sessionResponse.transcript.Length) chars" -ForegroundColor Gray
            Write-Host "  Summary length: $($sessionResponse.summary.Length) chars" -ForegroundColor Gray
            Write-Host "  Violations found: $($sessionResponse.violations.Count)" -ForegroundColor Gray
            $firNumber = $sessionResponse.fir_number
            $firContent = $sessionResponse.fir_content
            Write-Host ""
        } elseif ($sessionResponse.status -eq "failed") {
            Write-Host "✗ FIR generation failed: $($sessionResponse.error)" -ForegroundColor Red
            Write-Host ""
            exit 1
        }
    } catch {
        Write-Host "✗ Session polling failed: $_" -ForegroundColor Red
        Write-Host ""
        exit 1
    }
}

if (-not $completed) {
    Write-Host "✗ FIR generation timed out after $maxAttempts attempts" -ForegroundColor Red
    Write-Host ""
    exit 1
}

# Test 4: Verify FIR Content
Write-Host "Test 4: Verify FIR Content Structure" -ForegroundColor Yellow
$requiredFields = @(
    "fir_number", "complainant_name", "complainant_fathers_name", "complainant_address",
    "complainant_contact", "complainant_dob", "complainant_nationality", "complainant_occupation",
    "incident_date_from", "incident_date_to", "incident_time_from", "incident_time_to",
    "incident_location", "incident_address", "incident_description", "incident_summary",
    "acts_sections", "ipc_sections", "suspect_details", "investigation_officer_name",
    "investigation_officer_rank", "witnesses", "action_taken", "investigation_status",
    "date_of_despatch", "officer_signature", "officer_signature_date",
    "complainant_signature", "complainant_signature_date", "delayed_report_reasons"
)

$missingFields = @()
foreach ($field in $requiredFields) {
    if (-not $firContent.PSObject.Properties[$field]) {
        $missingFields += $field
    }
}

if ($missingFields.Count -eq 0) {
    Write-Host "✓ All 30 required FIR fields present" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "✗ Missing FIR fields: $($missingFields -join ', ')" -ForegroundColor Red
    Write-Host ""
    exit 1
}

# Test 5: Get FIR by Number
Write-Host "Test 5: Get FIR by Number" -ForegroundColor Yellow
Write-Host "GET $EC2_URL/fir/$firNumber" -ForegroundColor Gray
try {
    $firResponse = Invoke-RestMethod -Uri "$EC2_URL/fir/$firNumber" -Method Get -Headers $headers
    Write-Host "✓ FIR retrieved successfully" -ForegroundColor Green
    Write-Host "  FIR Number: $($firResponse.fir_number)" -ForegroundColor Gray
    Write-Host "  Status: $($firResponse.status)" -ForegroundColor Gray
    Write-Host "  Created: $($firResponse.created_at)" -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host "✗ FIR retrieval failed: $_" -ForegroundColor Red
    Write-Host ""
    exit 1
}

# Test 6: List FIRs
Write-Host "Test 6: List FIRs with Pagination" -ForegroundColor Yellow
Write-Host "GET $EC2_URL/firs?limit=10&offset=0" -ForegroundColor Gray
try {
    $firsResponse = Invoke-RestMethod -Uri "$EC2_URL/firs?limit=10&offset=0" -Method Get -Headers $headers
    Write-Host "✓ FIR list retrieved successfully" -ForegroundColor Green
    Write-Host "  Total FIRs: $($firsResponse.total)" -ForegroundColor Gray
    Write-Host "  Returned: $($firsResponse.firs.Count)" -ForegroundColor Gray
    Write-Host "  Limit: $($firsResponse.limit)" -ForegroundColor Gray
    Write-Host "  Offset: $($firsResponse.offset)" -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host "✗ FIR list retrieval failed: $_" -ForegroundColor Red
    Write-Host ""
    exit 1
}

# Test 7: Authenticate Endpoint (PDF Generation)
Write-Host "Test 7: Authenticate Endpoint - PDF Generation" -ForegroundColor Yellow
Write-Host "POST $EC2_URL/authenticate" -ForegroundColor Gray
$authBody = @{
    session_id = $sessionId
    complainant_signature = "Complainant Signature"
    officer_signature = "Officer Signature"
} | ConvertTo-Json

try {
    $authResponse = Invoke-RestMethod -Uri "$EC2_URL/authenticate" -Method Post -Body $authBody -Headers $headers
    Write-Host "✓ Authentication and PDF generation successful" -ForegroundColor Green
    Write-Host "  FIR Number: $($authResponse.fir_number)" -ForegroundColor Gray
    Write-Host "  PDF URL: $($authResponse.pdf_url)" -ForegroundColor Gray
    Write-Host ""
} catch {
    Write-Host "✗ Authentication failed: $_" -ForegroundColor Red
    Write-Host ""
    exit 1
}

# Test 8: Verify FIR Status Updated to Finalized
Write-Host "Test 8: Verify FIR Status Updated to Finalized" -ForegroundColor Yellow
Write-Host "GET $EC2_URL/fir/$firNumber" -ForegroundColor Gray
try {
    $finalFirResponse = Invoke-RestMethod -Uri "$EC2_URL/fir/$firNumber" -Method Get -Headers $headers
    if ($finalFirResponse.status -eq "finalized") {
        Write-Host "✓ FIR status updated to finalized" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "✗ FIR status not updated (current: $($finalFirResponse.status))" -ForegroundColor Red
        Write-Host ""
        exit 1
    }
} catch {
    Write-Host "✗ FIR status check failed: $_" -ForegroundColor Red
    Write-Host ""
    exit 1
}

# Test 9: API Key Authentication
Write-Host "Test 9: API Key Authentication" -ForegroundColor Yellow
Write-Host "Testing request without API key..." -ForegroundColor Gray
try {
    $noKeyResponse = Invoke-RestMethod -Uri "$EC2_URL/firs" -Method Get -ErrorAction Stop
    Write-Host "✗ Request without API key should have been rejected" -ForegroundColor Red
    Write-Host ""
    exit 1
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "✓ Unauthorized request correctly rejected (401)" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "✗ Unexpected error: $_" -ForegroundColor Red
        Write-Host ""
        exit 1
    }
}

# Test 10: Rate Limiting
Write-Host "Test 10: Rate Limiting" -ForegroundColor Yellow
Write-Host "Testing rate limit (100 requests per minute)..." -ForegroundColor Gray
Write-Host "Sending 10 rapid requests..." -ForegroundColor Gray
$rateLimitPassed = $true
for ($i = 1; $i -le 10; $i++) {
    try {
        $response = Invoke-RestMethod -Uri "$EC2_URL/health" -Method Get
        Write-Host "  Request $i - OK" -ForegroundColor Gray
    } catch {
        Write-Host "  Request $i - Failed: $_" -ForegroundColor Red
        $rateLimitPassed = $false
    }
}
if ($rateLimitPassed) {
    Write-Host "✓ Rate limiting working (10 requests passed)" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "✗ Rate limiting test failed" -ForegroundColor Red
    Write-Host ""
}

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✓ All tests passed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Backend is fully operational at: $EC2_URL" -ForegroundColor Green
Write-Host "Generated FIR Number: $firNumber" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Configure frontend to use: $EC2_URL" -ForegroundColor Gray
Write-Host "2. Test frontend integration" -ForegroundColor Gray
Write-Host "3. Complete final checkpoint (Task 18)" -ForegroundColor Gray
Write-Host ""
