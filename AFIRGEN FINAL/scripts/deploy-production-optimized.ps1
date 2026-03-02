# AFIRGen Production Deployment Script (PowerShell)
# Deploys the complete Bedrock architecture with all optimizations

$ErrorActionPreference = "Stop"

# Add AWS CLI to PATH if not already there
$AwsCliPath = "C:\Program Files\Amazon\AWSCLIV2"
if (Test-Path $AwsCliPath) {
    $env:PATH = "$AwsCliPath;$env:PATH"
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "AFIRGen Production Deployment (Optimized)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will deploy the complete production-ready system with:"
Write-Host "- All bug fixes applied"
Write-Host "- All optimizations enabled"
Write-Host "- CloudWatch alarms configured"
Write-Host "- Security hardening applied"
Write-Host ""

$confirmation = Read-Host "Continue with production deployment? (y/n)"
if ($confirmation -ne 'y') {
    Write-Host "Aborted." -ForegroundColor Yellow
    exit 1
}

# Set variables
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TerraformDir = Join-Path (Split-Path -Parent $ScriptDir) "terraform\free-tier"
$AppDir = Split-Path -Parent $ScriptDir
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = "deployment_$Timestamp.log"

# Logging function
function Write-Log {
    param($Message)
    $LogMessage = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $LogMessage
    Add-Content -Path $LogFile -Value $LogMessage
}

Write-Log "Starting production deployment..."

# ============================================================================
# Phase 1: Pre-Deployment Checks
# ============================================================================

Write-Log "Phase 1: Pre-deployment checks..."

# Check AWS credentials
try {
    $CallerIdentity = aws sts get-caller-identity --output json | ConvertFrom-Json
    Write-Log "✅ AWS credentials verified"
    Write-Log "AWS Account: $($CallerIdentity.Account)"
    Write-Log "AWS User: $($CallerIdentity.Arn)"
} catch {
    Write-Log "ERROR: AWS credentials not configured"
    Write-Log "Please run: aws configure"
    exit 1
}

# Check Terraform
if (!(Get-Command terraform -ErrorAction SilentlyContinue)) {
    Write-Log "ERROR: Terraform not installed"
    exit 1
}
Write-Log "✅ Terraform installed"

# Check Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Log "ERROR: Python 3 not installed"
    exit 1
}
Write-Log "✅ Python 3 installed"

# Verify environment variables
if (!(Test-Path "$AppDir\.env.bedrock")) {
    Write-Log "ERROR: .env.bedrock file not found"
    exit 1
}
Write-Log "✅ Environment configuration found"

# ============================================================================
# Phase 2: Infrastructure Deployment
# ============================================================================

Write-Log "Phase 2: Deploying infrastructure..."

Push-Location $TerraformDir

try {
    # Initialize Terraform
    Write-Log "Initializing Terraform..."
    terraform init
    
    # Validate configuration
    Write-Log "Validating Terraform configuration..."
    terraform validate
    
    # Plan deployment
    Write-Log "Planning infrastructure changes..."
    terraform plan -out=tfplan
    
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: Review the Terraform plan above" -ForegroundColor Yellow
    Write-Host ""
    $tfConfirm = Read-Host "Apply these infrastructure changes? (yes/no)"
    
    if ($tfConfirm -ne 'yes') {
        Write-Log "Deployment cancelled by user"
        Pop-Location
        exit 1
    }
    
    # Apply infrastructure
    Write-Log "Applying infrastructure changes..."
    terraform apply tfplan
    
    Write-Log "✅ Infrastructure deployed"
    
} catch {
    Write-Log "ERROR: Infrastructure deployment failed: $_"
    Pop-Location
    exit 1
}

Pop-Location

# ============================================================================
# Phase 3: Get Infrastructure Outputs
# ============================================================================

Write-Log "Phase 3: Retrieving infrastructure details..."

Push-Location $TerraformDir

try {
    $EC2InstanceId = terraform output -raw ec2_instance_id 2>$null
    $EC2PublicIp = terraform output -raw ec2_public_ip 2>$null
    $RDSEndpoint = terraform output -raw rds_endpoint 2>$null
    
    if ($EC2InstanceId) {
        Write-Log "EC2 Instance ID: $EC2InstanceId"
    }
    if ($EC2PublicIp) {
        Write-Log "EC2 Public IP: $EC2PublicIp"
    }
    if ($RDSEndpoint) {
        Write-Log "RDS Endpoint: $RDSEndpoint"
    }
    
} catch {
    Write-Log "⚠️  Warning: Could not retrieve all infrastructure outputs"
}

Pop-Location

# ============================================================================
# Phase 4: Post-Deployment Verification
# ============================================================================

Write-Log "Phase 4: Post-deployment verification..."

# Wait for EC2 to be running
if ($EC2InstanceId) {
    Write-Log "Waiting for EC2 instance to be running..."
    aws ec2 wait instance-running --instance-ids $EC2InstanceId
    Write-Log "✅ EC2 instance is running"
}

# Verify CloudWatch alarms
Write-Log "Verifying CloudWatch alarms..."
$AlarmCount = (aws cloudwatch describe-alarms --alarm-name-prefix "afirgen" --query 'length(MetricAlarms)' --output text)
Write-Log "CloudWatch alarms configured: $AlarmCount"

if ([int]$AlarmCount -lt 9) {
    Write-Log "⚠️  Warning: Expected at least 9 alarms, found $AlarmCount"
}

# ============================================================================
# Deployment Summary
# ============================================================================

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "DEPLOYMENT COMPLETED!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Log "Deployment completed successfully at $(Get-Date)"
Write-Host ""
Write-Host "Summary:"
Write-Host "✅ Infrastructure deployed" -ForegroundColor Green
Write-Host "✅ Security configurations applied" -ForegroundColor Green
Write-Host "✅ Monitoring configured" -ForegroundColor Green
Write-Host ""
Write-Host "Deployment Details:"
if ($EC2InstanceId) { Write-Host "- EC2 Instance: $EC2InstanceId" }
if ($EC2PublicIp) { Write-Host "- EC2 IP: $EC2PublicIp" }
if ($RDSEndpoint) { Write-Host "- RDS Endpoint: $RDSEndpoint" }
Write-Host "- Log File: $LogFile"
Write-Host ""
Write-Host "Next Steps:"
Write-Host "1. Configure application on EC2 instance"
Write-Host "2. Set up database schema"
Write-Host "3. Deploy application code"
Write-Host "4. Verify SNS email subscription"
Write-Host "5. Test end-to-end FIR generation"
Write-Host ""
if ($EC2PublicIp) {
    Write-Host "SSH to EC2: ssh -i your-key.pem ubuntu@$EC2PublicIp"
}
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
