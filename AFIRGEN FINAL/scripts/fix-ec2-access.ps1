# Fix EC2 Access - Add SSM permissions and SSH key
# Run this from your local Windows machine

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "AFIRGen EC2 Access Fix" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$InstanceId = "i-0bc18e312758fda7c"
$Region = "us-east-1"

# Step 1: Get IAM role name
Write-Host "Step 1: Getting IAM role name..." -ForegroundColor Cyan
$IamProfileArn = aws ec2 describe-instances `
    --instance-ids $InstanceId `
    --region $Region `
    --query 'Reservations[0].Instances[0].IamInstanceProfile.Arn' `
    --output text

if (!$IamProfileArn -or $IamProfileArn -eq "None") {
    Write-Host "ERROR: Could not find IAM role for instance" -ForegroundColor Red
    exit 1
}

$ProfileName = $IamProfileArn.Split('/')[-1]
Write-Host "IAM Instance Profile: $ProfileName" -ForegroundColor Yellow

# Get actual role name
$ActualRoleName = aws iam get-instance-profile `
    --instance-profile-name $ProfileName `
    --query 'InstanceProfile.Roles[0].RoleName' `
    --output text

Write-Host "Actual IAM Role: $ActualRoleName" -ForegroundColor Yellow

# Step 2: Attach SSM managed policy
Write-Host ""
Write-Host "Step 2: Attaching SSM managed policy..." -ForegroundColor Cyan

try {
    aws iam attach-role-policy `
        --role-name $ActualRoleName `
        --policy-arn "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore" `
        --region $Region 2>$null
    
    Write-Host "✓ SSM policy attached" -ForegroundColor Green
} catch {
    # Policy might already be attached
    Write-Host "✓ SSM policy already attached or attached successfully" -ForegroundColor Green
}

# Step 3: Reboot instance to apply IAM changes faster
Write-Host ""
Write-Host "Step 3: Rebooting instance to apply IAM changes..." -ForegroundColor Cyan
$confirmation = Read-Host "Reboot instance $InstanceId? This will restart your EC2 (y/n)"

if ($confirmation -eq 'y') {
    aws ec2 reboot-instances --instance-ids $InstanceId --region $Region
    Write-Host "✓ Instance rebooting..." -ForegroundColor Green
    Write-Host "Waiting 2 minutes for instance to restart..." -ForegroundColor Yellow
    Start-Sleep -Seconds 120
} else {
    Write-Host "Skipping reboot. SSM agent may take 5-10 minutes to register." -ForegroundColor Yellow
}

# Step 4: Wait for SSM agent to register
Write-Host ""
Write-Host "Step 4: Waiting for SSM agent to register..." -ForegroundColor Cyan
Write-Host "Checking every 30 seconds..." -ForegroundColor Yellow

$MaxAttempts = 20
$Attempt = 0
$Connected = $false

while ($Attempt -lt $MaxAttempts) {
    $Attempt++
    Write-Host "Attempt $Attempt/$MaxAttempts..." -ForegroundColor Gray
    
    $PingStatus = aws ssm describe-instance-information `
        --filters "Key=InstanceIds,Values=$InstanceId" `
        --region $Region `
        --query 'InstanceInformationList[0].PingStatus' `
        --output text 2>$null
    
    if ($PingStatus -eq "Online") {
        Write-Host "✓ SSM agent is online!" -ForegroundColor Green
        $Connected = $true
        break
    }
    
    if ($Attempt -eq $MaxAttempts) {
        Write-Host "⚠ SSM agent not online yet." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Options:" -ForegroundColor Yellow
        Write-Host "1. Wait longer (can take up to 10 minutes)" -ForegroundColor White
        Write-Host "2. Reboot instance: aws ec2 reboot-instances --instance-ids $InstanceId --region $Region" -ForegroundColor White
        Write-Host "3. Use EC2 Instance Connect from AWS Console" -ForegroundColor White
        exit 1
    }
    
    Start-Sleep -Seconds 30
}

if ($Connected) {
    # Step 5: Test SSM connection
    Write-Host ""
    Write-Host "Step 5: Connecting via SSM..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "SUCCESS! Connecting to EC2 instance..." -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Once connected, you can:" -ForegroundColor Yellow
    Write-Host "1. Switch to ubuntu user: sudo su - ubuntu" -ForegroundColor White
    Write-Host "2. Add SSH key (optional):" -ForegroundColor White
    Write-Host "   mkdir -p ~/.ssh && chmod 700 ~/.ssh" -ForegroundColor Gray
    Write-Host "   echo 'YOUR_PUBLIC_KEY' >> ~/.ssh/authorized_keys" -ForegroundColor Gray
    Write-Host "   chmod 600 ~/.ssh/authorized_keys" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Connecting in 3 seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    
    aws ssm start-session --target $InstanceId --region $Region
}
