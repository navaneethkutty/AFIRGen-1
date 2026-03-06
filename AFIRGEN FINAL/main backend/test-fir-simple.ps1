# Simple FIR Generation Test
$API_BASE = "http://18.206.148.182:8000"
$API_KEY = "dev-test-key-12345678901234567890123456789012"

Write-Host "Testing FIR Generation..." -ForegroundColor Cyan

# Create a temporary file with the request JSON
$requestJson = @{
    input_type = "text"
    text = "I want to report a theft. Yesterday at 3 PM, someone broke into my house at 123 Main Street, Mumbai and stole my laptop, phone, and jewelry worth Rs 50,000. I saw a man in a black hoodie running away. My name is Rajesh Kumar."
    language = "en-IN"
} | ConvertTo-Json

$tempFile = [System.IO.Path]::GetTempFileName()
$requestJson | Out-File -FilePath $tempFile -Encoding utf8 -NoNewline

try {
    # Use curl for proper multipart/form-data handling
    $curlCommand = "curl -X POST `"$API_BASE/process`" -H `"X-API-Key: $API_KEY`" -F `"request=@$tempFile;type=application/json`""
    
    Write-Host "Sending request..." -ForegroundColor Yellow
    $response = Invoke-Expression $curlCommand | ConvertFrom-Json
    
    Write-Host "✓ FIR Generation Started" -ForegroundColor Green
    Write-Host "  Session ID: $($response.session_id)" -ForegroundColor Gray
    Write-Host "  Status: $($response.status)" -ForegroundColor Gray
    
    $sessionId = $response.session_id
    
    # Poll for completion
    Write-Host "`nPolling for completion..." -ForegroundColor Yellow
    $maxAttempts = 30
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        Start-Sleep -Seconds 3
        $attempt++
        
        $sessionResponse = Invoke-RestMethod -Uri "$API_BASE/session/$sessionId" -Method Get -Headers @{"X-API-Key" = $API_KEY}
        
        Write-Host "  Attempt $attempt - Status: $($sessionResponse.status)" -ForegroundColor Gray
        
        if ($sessionResponse.status -eq "completed") {
            Write-Host "`n✓ FIR Generation Completed!" -ForegroundColor Green
            Write-Host "  FIR Number: $($sessionResponse.fir_number)" -ForegroundColor Cyan
            Write-Host "  Transcript: $($sessionResponse.transcript.Substring(0, [Math]::Min(100, $sessionResponse.transcript.Length)))..." -ForegroundColor Gray
            
            if ($sessionResponse.fir_content) {
                $firContent = $sessionResponse.fir_content | ConvertFrom-Json
                $fieldCount = ($firContent.PSObject.Properties | Measure-Object).Count
                Write-Host "  FIR Fields: $fieldCount" -ForegroundColor Gray
                
                if ($fieldCount -ge 25) {
                    Write-Host "  ✓ FIR has sufficient fields" -ForegroundColor Green
                }
            }
            break
        } elseif ($sessionResponse.status -eq "failed") {
            Write-Host "`n✗ FIR Generation Failed" -ForegroundColor Red
            Write-Host "  Error: $($sessionResponse.error)" -ForegroundColor Red
            break
        }
    }
    
} catch {
    Write-Host "✗ Error: $_" -ForegroundColor Red
} finally {
    Remove-Item $tempFile -ErrorAction SilentlyContinue
}
