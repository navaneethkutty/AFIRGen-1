# Add your local IP to RDS security group
# This script helps you update the RDS security group to allow local access

$MY_IP = "49.206.13.189"
$REGION = "us-east-1"

Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host "Add Local IP to RDS Security Group"
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""
Write-Host "Your public IP: $MY_IP"
Write-Host "AWS Region: $REGION"
Write-Host ""

# Get RDS instance details
Write-Host "Fetching RDS instance details..."
$rdsInfo = aws rds describe-db-instances `
    --db-instance-identifier afirgen-free-tier-mysql `
    --region $REGION `
    --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' `
    --output text

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to fetch RDS details. Make sure AWS CLI is configured."
    exit 1
}

Write-Host "✓ Found security group: $rdsInfo"
Write-Host ""

# Add inbound rule
Write-Host "Adding inbound rule for MySQL (port 3306)..."
Write-Host "  Source: $MY_IP/32"
Write-Host ""

$result = aws ec2 authorize-security-group-ingress `
    --group-id $rdsInfo `
    --protocol tcp `
    --port 3306 `
    --cidr "$MY_IP/32" `
    --region $REGION 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Successfully added inbound rule!"
    Write-Host ""
    Write-Host "You can now connect to RDS from your local machine."
    Write-Host "Run: python start_backend.py"
} else {
    if ($result -match "already exists") {
        Write-Host "✓ Rule already exists - your IP is already allowed!"
        Write-Host ""
        Write-Host "You can now connect to RDS from your local machine."
        Write-Host "Run: python start_backend.py"
    } else {
        Write-Host "✗ Failed to add inbound rule:"
        Write-Host $result
        Write-Host ""
        Write-Host "Please add the rule manually via AWS Console:"
        Write-Host "1. Go to: https://console.aws.amazon.com/ec2/v2/home?region=$REGION#SecurityGroups:"
        Write-Host "2. Find security group: $rdsInfo"
        Write-Host "3. Add inbound rule: Type=MySQL/Aurora, Port=3306, Source=$MY_IP/32"
    }
}

Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
