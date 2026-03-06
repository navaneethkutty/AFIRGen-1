# Setup Systemd Service for AFIRGen Backend
# This script configures the backend to run as a systemd service on EC2

$INSTANCE_ID = "i-02ecca1d375ab2cec"
$REGION = "us-east-1"

Write-Host "=== Setting Up AFIRGen Systemd Service ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Creating systemd service file..." -ForegroundColor Yellow

$command = @'
cd "/opt/afirgen-backend/AFIRGEN FINAL/main backend" && \
sudo bash -c 'cat > /etc/systemd/system/afirgen.service << "EOF"
[Unit]
Description=AFIRGen Backend Service - Automated FIR Generation
Documentation=https://github.com/your-repo/afirgen
After=network.target

[Service]
Type=simple
User=ssm-user
WorkingDirectory=/opt/afirgen-backend/AFIRGEN FINAL/main backend
EnvironmentFile=/opt/afirgen-backend/AFIRGEN FINAL/main backend/.env
ExecStart=/opt/afirgen-backend/AFIRGEN FINAL/main backend/venv/bin/uvicorn agentv5:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF'
'@

try {
    $commandId = aws ssm send-command `
        --instance-ids $INSTANCE_ID `
        --document-name "AWS-RunShellScript" `
        --parameters "commands=[$command]" `
        --region $REGION `
        --output text `
        --query 'Command.CommandId'
    
    Write-Host "  Command sent: $commandId" -ForegroundColor Gray
    Start-Sleep -Seconds 3
    
    $output = aws ssm get-command-invocation `
        --command-id $commandId `
        --instance-id $INSTANCE_ID `
        --region $REGION `
        --query 'StandardOutputContent' `
        --output text
    
    Write-Host "✓ Service file created" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to create service file: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 2: Reloading systemd daemon..." -ForegroundColor Yellow

$command = "sudo systemctl daemon-reload"

try {
    $commandId = aws ssm send-command `
        --instance-ids $INSTANCE_ID `
        --document-name "AWS-RunShellScript" `
        --parameters "commands=[$command]" `
        --region $REGION `
        --output text `
        --query 'Command.CommandId'
    
    Start-Sleep -Seconds 2
    Write-Host "✓ Systemd daemon reloaded" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to reload daemon: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 3: Enabling service to start on boot..." -ForegroundColor Yellow

$command = "sudo systemctl enable afirgen"

try {
    $commandId = aws ssm send-command `
        --instance-ids $INSTANCE_ID `
        --document-name "AWS-RunShellScript" `
        --parameters "commands=[$command]" `
        --region $REGION `
        --output text `
        --query 'Command.CommandId'
    
    Start-Sleep -Seconds 2
    Write-Host "✓ Service enabled" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to enable service: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 4: Starting the service..." -ForegroundColor Yellow

$command = "sudo systemctl start afirgen"

try {
    $commandId = aws ssm send-command `
        --instance-ids $INSTANCE_ID `
        --document-name "AWS-RunShellScript" `
        --parameters "commands=[$command]" `
        --region $REGION `
        --output text `
        --query 'Command.CommandId'
    
    Start-Sleep -Seconds 3
    Write-Host "✓ Service started" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to start service: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 5: Checking service status..." -ForegroundColor Yellow

$command = "sudo systemctl status afirgen --no-pager"

try {
    $commandId = aws ssm send-command `
        --instance-ids $INSTANCE_ID `
        --document-name "AWS-RunShellScript" `
        --parameters "commands=[$command]" `
        --region $REGION `
        --output text `
        --query 'Command.CommandId'
    
    Start-Sleep -Seconds 3
    
    $output = aws ssm get-command-invocation `
        --command-id $commandId `
        --instance-id $INSTANCE_ID `
        --region $REGION `
        --query 'StandardOutputContent' `
        --output text
    
    Write-Host $output -ForegroundColor Gray
    
    if ($output -match "active \(running\)") {
        Write-Host "`n✓ Service is running!" -ForegroundColor Green
    } else {
        Write-Host "`n⚠ Service may not be running properly" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Failed to check status: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Step 6: Testing health endpoint..." -ForegroundColor Yellow

Start-Sleep -Seconds 5

try {
    $response = Invoke-RestMethod -Uri "http://18.206.148.182:8000/health" -Method Get
    Write-Host "✓ Backend is responding!" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor Gray
    Write-Host "  MySQL: $($response.checks.mysql)" -ForegroundColor Gray
    Write-Host "  Bedrock: $($response.checks.bedrock)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Health check failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "The AFIRGen backend is now running as a systemd service!" -ForegroundColor Green
Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor Yellow
Write-Host "  Check status:  aws ssm start-session --target $INSTANCE_ID --region $REGION" -ForegroundColor White
Write-Host "                 sudo systemctl status afirgen" -ForegroundColor White
Write-Host "  View logs:     sudo journalctl -u afirgen -f" -ForegroundColor White
Write-Host "  Restart:       sudo systemctl restart afirgen" -ForegroundColor White
Write-Host "  Stop:          sudo systemctl stop afirgen" -ForegroundColor White
Write-Host ""
Write-Host "Backend URL: http://18.206.148.182:8000" -ForegroundColor Cyan
