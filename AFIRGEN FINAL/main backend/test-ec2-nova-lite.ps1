# Test AFIRGen Backend on EC2 with Nova Lite
# Run this in a fresh PowerShell terminal

$BASE_URL = "http://18.206.148.182:8000"
$API_KEY = "dev-test-key-12345678901234567890123456789012"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "AFIRGen Backend Test - EC2 (Nova Lite)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health Check
Write-Host "1. Testing Health Endpoint..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-RestMethod -Uri "$BASE_URL/health" -Method Get -Headers @{"X-API-Key"=$API_KEY}
    Write-Host "✅ Health check passed" -ForegroundColor Green
    $healthResponse | ConvertTo-Json -Depth 10
} catch {
    Write-Host "❌ Health check failed: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 2: Process Text Input
Write-Host "2. Testing /process endpoint with text input..." -ForegroundColor Yellow
try {
    $form = @{
        input_type = "text"
        text = "A person stole my mobile phone at the market yesterday. The thief was wearing a red jacket."
    }
    
    $processResponse = Invoke-RestMethod -Uri "$BASE_URL/process" -Method Post -Headers @{"X-API-Key"=$API_KEY} -Form $form
    Write-Host "✅ Process request submitted" -ForegroundColor Green
    $processResponse | ConvertTo-Json -Depth 10
    
    $sessionId = $processResponse.session_id
    Write-Host ""
    Write-Host "Session ID: $sessionId" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Process request failed: $_" -ForegroundColor Red
    Write-Host "Response: $($_.Exception.Response)" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 3: Poll Session Status
Write-Host "3. Polling session status (max 10 attempts)..." -ForegroundColor Yellow
$maxAttempts = 10
$completed = $false

for ($i = 1; $i -le $maxAttempts; $i++) {
    Write-Host "Poll attempt $i/$maxAttempts..." -ForegroundColor Gray
    
    try {
        $statusResponse = Invoke-RestMethod -Uri "$BASE_URL/session/$sessionId" -Method Get -Headers @{"X-API-Key"=$API_KEY}
        
        $status = $statusResponse.status
        Write-Host "Status: $status" -ForegroundColor Cyan
        
        if ($status -eq "completed") {
            Write-Host ""
            Write-Host "✅ FIR generation completed!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Full Response:" -ForegroundColor Yellow
            $statusResponse | ConvertTo-Json -Depth 10
            $completed = $true
            break
        } elseif ($status -eq "error") {
            Write-Host ""
            Write-Host "❌ FIR generation failed" -ForegroundColor Red
            Write-Host "Error: $($statusResponse.error)" -ForegroundColor Red
            break
        }
        
        Start-Sleep -Seconds 3
    } catch {
        Write-Host "❌ Status check failed: $_" -ForegroundColor Red
        break
    }
}

if (-not $completed) {
    Write-Host ""
    Write-Host "⚠️  FIR generation did not complete within timeout" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Test Complete" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
