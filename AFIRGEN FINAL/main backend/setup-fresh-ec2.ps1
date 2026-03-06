# Fresh EC2 Setup Script for AFIRGen Backend
# This script creates a new EC2 instance with proper configuration

$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "AFIRGen Backend - Fresh EC2 Setup"
Write-Host "============================================================"
Write-Host ""

# Configuration
$REGION = "us-east-1"
$INSTANCE_TYPE = "t3.small"  # 2 vCPUs, 2 GB RAM (Free Tier eligible)
$AMI_ID = "ami-0e2c8caa4b6378d8c"  # Ubuntu 24.04 LTS in us-east-1
$KEY_NAME = "afirgen-key"
$SECURITY_GROUP_NAME = "afirgen-backend-sg"
$IAM_ROLE_NAME = "afirgen-ec2-role"

Write-Host "Configuration:"
Write-Host "  Region: $REGION"
Write-Host "  Instance Type: $INSTANCE_TYPE (Free Tier)"
Write-Host "  AMI: Ubuntu 24.04 LTS"
Write-Host ""

# Step 1: Create SSH Key Pair
Write-Host "Step 1: Creating SSH key pair..."
$keyExists = aws ec2 describe-key-pairs --key-names $KEY_NAME --region $REGION 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Creating new key pair: $KEY_NAME"
    aws ec2 create-key-pair --key-name $KEY_NAME --region $REGION --query 'KeyMaterial' --output text | Out-File -FilePath "$env:USERPROFILE\.ssh\$KEY_NAME.pem" -Encoding ASCII
    
    # Set permissions (Windows)
    icacls "$env:USERPROFILE\.ssh\$KEY_NAME.pem" /inheritance:r
    icacls "$env:USERPROFILE\.ssh\$KEY_NAME.pem" /grant:r "$env:USERNAME`:R"
    
    Write-Host "  ✓ Key pair created: $env:USERPROFILE\.ssh\$KEY_NAME.pem"
} else {
    Write-Host "  ✓ Key pair already exists: $KEY_NAME"
}

# Step 2: Create Security Group
Write-Host ""
Write-Host "Step 2: Creating security group..."
$sgId = aws ec2 describe-security-groups --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" --region $REGION --query 'SecurityGroups[0].GroupId' --output text 2>$null

if ($LASTEXITCODE -ne 0 -or $sgId -eq "None" -or [string]::IsNullOrEmpty($sgId)) {
    Write-Host "  Creating new security group: $SECURITY_GROUP_NAME"
    $sgId = aws ec2 create-security-group --group-name $SECURITY_GROUP_NAME --description "AFIRGen Backend Security Group" --region $REGION --query 'GroupId' --output text
    
    # Add inbound rules
    Write-Host "  Adding inbound rules..."
    
    # SSH (port 22) from your IP
    $myIp = (Invoke-RestMethod -Uri "https://api.ipify.org?format=text").Trim()
    aws ec2 authorize-security-group-ingress --group-id $sgId --protocol tcp --port 22 --cidr "$myIp/32" --region $REGION | Out-Null
    Write-Host "    ✓ SSH (22) from $myIp"
    
    # HTTP API (port 8000) from anywhere
    aws ec2 authorize-security-group-ingress --group-id $sgId --protocol tcp --port 8000 --cidr "0.0.0.0/0" --region $REGION | Out-Null
    Write-Host "    ✓ HTTP API (8000) from anywhere"
    
    Write-Host "  ✓ Security group created: $sgId"
} else {
    Write-Host "  ✓ Security group already exists: $sgId"
}

# Step 3: Create IAM Role for EC2
Write-Host ""
Write-Host "Step 3: Creating IAM role..."
$roleExists = aws iam get-role --role-name $IAM_ROLE_NAME 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Creating IAM role: $IAM_ROLE_NAME"
    
    # Create trust policy
    $trustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@
    
    $trustPolicy | Out-File -FilePath "trust-policy.json" -Encoding ASCII
    aws iam create-role --role-name $IAM_ROLE_NAME --assume-role-policy-document file://trust-policy.json --region $REGION | Out-Null
    
    # Attach policies
    Write-Host "  Attaching policies..."
    aws iam attach-role-policy --role-name $IAM_ROLE_NAME --policy-arn "arn:aws:iam::aws:policy/AmazonBedrockFullAccess" --region $REGION
    aws iam attach-role-policy --role-name $IAM_ROLE_NAME --policy-arn "arn:aws:iam::aws:policy/AmazonTranscribeFullAccess" --region $REGION
    aws iam attach-role-policy --role-name $IAM_ROLE_NAME --policy-arn "arn:aws:iam::aws:policy/AmazonTextractFullAccess" --region $REGION
    aws iam attach-role-policy --role-name $IAM_ROLE_NAME --policy-arn "arn:aws:iam::aws:policy/AmazonS3FullAccess" --region $REGION
    aws iam attach-role-policy --role-name $IAM_ROLE_NAME --policy-arn "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore" --region $REGION
    
    # Create instance profile
    aws iam create-instance-profile --instance-profile-name "$IAM_ROLE_NAME-profile" --region $REGION | Out-Null
    aws iam add-role-to-instance-profile --instance-profile-name "$IAM_ROLE_NAME-profile" --role-name $IAM_ROLE_NAME --region $REGION
    
    Write-Host "  ✓ IAM role created with required policies"
    Write-Host "  Waiting 10 seconds for IAM role to propagate..."
    Start-Sleep -Seconds 10
} else {
    Write-Host "  ✓ IAM role already exists: $IAM_ROLE_NAME"
}

# Step 4: Create User Data Script
Write-Host ""
Write-Host "Step 4: Preparing user data script..."
$userData = @"
#!/bin/bash
set -e

# Update system
apt-get update
apt-get upgrade -y

# Install dependencies
apt-get install -y python3.11 python3.11-venv python3-pip git mysql-client

# Create deployment directory
mkdir -p /opt/afirgen-backend
cd /opt/afirgen-backend

# Clone repository
git clone https://github.com/navaneethkutty/AFIRGen-1.git .

# Navigate to backend
cd "AFIRGEN FINAL/main backend"

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cat > .env << 'EOF'
AWS_REGION=us-east-1
S3_BUCKET_NAME=afirgen-storage-bucket
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
DB_HOST=afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com
DB_PORT=3306
DB_USER=admin
DB_PASSWORD=Prathiush12.
DB_NAME=afirgen
API_KEY=dev-test-key-12345678901234567890123456789012
RATE_LIMIT_PER_MINUTE=100
MAX_FILE_SIZE_MB=10
TRANSCRIBE_TIMEOUT_SECONDS=180
BEDROCK_TIMEOUT_SECONDS=60
MAX_RETRIES=2
RETRY_DELAY_SECONDS=2
EOF

# Create logs directory
mkdir -p logs

# Install systemd service
cp afirgen.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable afirgen
systemctl start afirgen

echo "Setup complete!"
"@

$userData | Out-File -FilePath "user-data.sh" -Encoding ASCII
Write-Host "  ✓ User data script prepared"

# Step 5: Launch EC2 Instance
Write-Host ""
Write-Host "Step 5: Launching EC2 instance..."
Write-Host "  Instance type: $INSTANCE_TYPE"
Write-Host "  This may take a few minutes..."

$instanceId = aws ec2 run-instances `
    --image-id $AMI_ID `
    --instance-type $INSTANCE_TYPE `
    --key-name $KEY_NAME `
    --security-group-ids $sgId `
    --iam-instance-profile "Name=$IAM_ROLE_NAME-profile" `
    --user-data file://user-data.sh `
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=AFIRGen-Backend}]" `
    --region $REGION `
    --query 'Instances[0].InstanceId' `
    --output text

Write-Host "  ✓ Instance launched: $instanceId"
Write-Host "  Waiting for instance to be running..."

# Wait for instance to be running
aws ec2 wait instance-running --instance-ids $instanceId --region $REGION

# Get public IP
$publicIp = aws ec2 describe-instances --instance-ids $instanceId --region $REGION --query 'Reservations[0].Instances[0].PublicIpAddress' --output text

Write-Host "  ✓ Instance is running!"
Write-Host ""
Write-Host "============================================================"
Write-Host "Setup Complete!"
Write-Host "============================================================"
Write-Host ""
Write-Host "Instance Details:"
Write-Host "  Instance ID: $instanceId"
Write-Host "  Public IP: $publicIp"
Write-Host "  Instance Type: $INSTANCE_TYPE"
Write-Host "  SSH Key: $env:USERPROFILE\.ssh\$KEY_NAME.pem"
Write-Host ""
Write-Host "The instance is now starting up and installing the backend."
Write-Host "This process takes about 5-10 minutes."
Write-Host ""
Write-Host "SSH Connection:"
Write-Host "  ssh -i `"$env:USERPROFILE\.ssh\$KEY_NAME.pem`" ubuntu@$publicIp"
Write-Host ""
Write-Host "Wait 5-10 minutes, then test:"
Write-Host "  curl http://${publicIp}:8000/health"
Write-Host ""
Write-Host "View logs via SSH:"
Write-Host "  sudo journalctl -u afirgen -f"
Write-Host ""
Write-Host "Update RDS security group to allow this EC2 instance:"
Write-Host "  1. Go to RDS Console"
Write-Host "  2. Select your database"
Write-Host "  3. Click on the security group"
Write-Host "  4. Add inbound rule: Type=MySQL/Aurora, Source=$sgId"
Write-Host ""

# Cleanup temp files
Remove-Item -Path "trust-policy.json" -ErrorAction SilentlyContinue
Remove-Item -Path "user-data.sh" -ErrorAction SilentlyContinue

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
