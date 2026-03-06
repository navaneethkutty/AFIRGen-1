# Simple Systemd Service Setup
$INSTANCE_ID = "i-02ecca1d375ab2cec"
$REGION = "us-east-1"

Write-Host "Setting up systemd service..." -ForegroundColor Cyan

# Single command to set everything up
$setupScript = @'
cd "/opt/afirgen-backend/AFIRGEN FINAL/main backend" && \
sudo cp afirgen.service /etc/systemd/system/afirgen.service && \
sudo systemctl daemon-reload && \
sudo systemctl enable afirgen && \
sudo systemctl start afirgen && \
sleep 3 && \
sudo systemctl status afirgen --no-pager
'@

Write-Host "Executing setup commands..." -ForegroundColor Yellow

$commandId = aws ssm send-command `
    --instance-ids $INSTANCE_ID `
    --document-name "AWS-RunShellScript" `
    --parameters "commands=['$setupScript']" `
    --region $REGION `
    --output text `
    --query 'Command.CommandId'

Write-Host "Command ID: $commandId" -ForegroundColor Gray
Write-Host "Waiting for execution..." -ForegroundColor Gray
Start-Sleep -Seconds 8

$output = aws ssm get-command-invocation `
    --command-id $commandId `
    --instance-id $INSTANCE_ID `
    --region $REGION `
    --query 'StandardOutputContent' `
    --output text

Write-Host "`nOutput:" -ForegroundColor Yellow
Write-Host $output

Write-Host "`nTesting health endpoint..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

try {
    $response = Invoke-RestMethod -Uri "http://18.206.148.182:8000/health" -Method Get
    Write-Host "✓ Backend is running!" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor Cyan
} catch {
    Write-Host "✗ Health check failed: $_" -ForegroundColor Red
}
