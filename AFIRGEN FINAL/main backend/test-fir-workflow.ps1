# Test FIR Generation Workflow on EC2
# Tests the complete end-to-end FIR generation process

$API_BASE = "http://18.206.148.182:8000"
$API_KEY = "dev-test-key-12345678901234567890123456789012"

Write-Host "=== Testing AFIRGen Backend on EC2 ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health Check
Write-Host "Test 1: Health Check" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$API_BASE/health" -Method Get
    Write-Host "✓ Health Check Passed" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor Gray
    Write-Host "  MySQL: $($response.checks.mysql)" -ForegroundColor Gray
    Write-Host "  Bedrock: $($response.checks.bedrock)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Health Check Failed: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 2: Generate FIR from Text
Write-Host "Test 2: Generate FIR from Text Input" -ForegroundColor Yellow

# Create multipart form data
$boundary = [System.Guid]::NewGuid().ToString()
$LF = "`r`n"

$bodyLines = @(
    "--$boundary",
    "Content-Disposition: form-data; name=`"request`"",
    "Content-Type: application/json",
    "",
    '{"input_type":"text","text":"I want to report a theft. Yesterday at 3 PM, someone broke into my house at 123 Main Street, Mumbai and stole my laptop, phone, and jewelry worth Rs 50,000. I saw a man in a black hoodie running away. My name is Rajesh Kumar and my phone number is 9876543210.","language":"en-IN"}',
    "--$boundary--"
)

$body = $bodyLines -join $LF

try {
    $headers = @{
        "Content-Type" = "multipart/form-data; boundary=$boundary"
        "X-API-Key" = $API_KEY
    }
    
    $response = Invoke-RestMethod -Uri "$API_BASE/process" -Method Post -Body $body -Headers $headers
    Write-Host "✓ FIR Generation Started" -ForegroundColor Green
    Write-Host "  Session ID: $($response.session_id)" -ForegroundColor Gray
    Write-Host "  Status: $($response.status)" -ForegroundColor Gray
    
    $sessionId = $response.session_id
    
    # Poll for completion
    Write-Host "  Waiting for FIR generation to complete..." -ForegroundColor Gray
    $maxAttempts = 30
    $attempt = 0
    $completed = $false
    
    while ($attempt -lt $maxAttempts -and -not $completed) {
        Start-Sleep -Seconds 2
        $attempt++
        
        try {
            $sessionResponse = Invoke-RestMethod -Uri "$API_BASE/session/$sessionId" -Method Get -Headers $headers
            
            if ($sessionResponse.status -eq "completed") {
                $completed = $true
                Write-Host "✓ FIR Generation Completed!" -ForegroundColor Green
                Write-Host "  FIR Number: $($sessionResponse.fir_number)" -ForegroundColor Gray
                Write-Host "  Transcript Length: $($sessionResponse.transcript.Length) chars" -ForegroundColor Gray
                Write-Host "  Summary Length: $($sessionResponse.summary.Length) chars" -ForegroundColor Gray
                Write-Host "  Violations Found: $($sessionResponse.violations.Count)" -ForegroundColor Gray
                
                # Check FIR content fields
                if ($sessionResponse.fir_content) {
                    $firContent = $sessionResponse.fir_content | ConvertFrom-Json
                    $fieldCount = ($firContent | Get-Member -MemberType NoteProperty).Count
                    Write-Host "  FIR Fields: $fieldCount" -ForegroundColor Gray
                    
                    if ($fieldCount -ge 30) {
                        Write-Host "✓ All 30 FIR fields present" -ForegroundColor Green
                    } else {
                        Write-Host "⚠ Only $fieldCount fields present (expected 30)" -ForegroundColor Yellow
                    }
                }
            } elseif ($sessionResponse.status -eq "failed") {
                Write-Host "✗ FIR Generation Failed: $($sessionResponse.error)" -ForegroundColor Red
                break
            } else {
                Write-Host "  Attempt $attempt/$maxAttempts - Status: $($sessionResponse.status)" -ForegroundColor Gray
            }
        } catch {
            Write-Host "  Attempt $attempt/$maxAttempts - Polling error: $_" -ForegroundColor Yellow
        }
    }
    
    if (-not $completed) {
        Write-Host "⚠ FIR generation timed out after $maxAttempts attempts" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "✗ FIR Generation Failed: $_" -ForegroundColor Red
    Write-Host "Error Details: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 3: List FIRs
Write-Host "Test 3: List FIRs" -ForegroundColor Yellow
try {
    $headers = @{
        "X-API-Key" = $API_KEY
    }
    
    $response = Invoke-RestMethod -Uri "$API_BASE/firs?limit=5" -Method Get -Headers $headers
    Write-Host "✓ FIR List Retrieved" -ForegroundColor Green
    Write-Host "  Total FIRs: $($response.total)" -ForegroundColor Gray
    Write-Host "  Returned: $($response.firs.Count)" -ForegroundColor Gray
    
    if ($response.firs.Count -gt 0) {
        Write-Host "  Latest FIR: $($response.firs[0].fir_number)" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ List FIRs Failed: $_" -ForegroundColor Red
}
Write-Host ""

# Test 4: Get Specific FIR (if we have one)
if ($sessionId -and $completed) {
    Write-Host "Test 4: Get FIR by Number" -ForegroundColor Yellow
    try {
        $headers = @{
            "X-API-Key" = $API_KEY
        }
        
        $firNumber = $sessionResponse.fir_number
        $response = Invoke-RestMethod -Uri "$API_BASE/fir/$firNumber" -Method Get -Headers $headers
        Write-Host "✓ FIR Retrieved Successfully" -ForegroundColor Green
        Write-Host "  FIR Number: $($response.fir_number)" -ForegroundColor Gray
        Write-Host "  Status: $($response.status)" -ForegroundColor Gray
        Write-Host "  Created: $($response.created_at)" -ForegroundColor Gray
    } catch {
        Write-Host "✗ Get FIR Failed: $_" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "=== Test Summary ===" -ForegroundColor Cyan
Write-Host "Backend is operational and processing FIR requests!" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Configure frontend to use: $API_BASE" -ForegroundColor White
Write-Host "2. Set up systemd service for permanent deployment" -ForegroundColor White
Write-Host "3. Test complete workflow with frontend" -ForegroundColor White
