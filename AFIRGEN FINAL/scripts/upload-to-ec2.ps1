# Upload AFIRGen Code to EC2
# Run this from your local Windows machine

param(
    [Parameter(Mandatory=$true)]
    [string]$KeyFile,
    
    [Parameter(Mandatory=$false)]
    [string]$EC2IP = "98.86.30.145"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AFIRGen Code Upload to EC2" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verify key file exists
if (!(Test-Path $KeyFile)) {
    Write-Host "ERROR: Key file not found: $KeyFile" -ForegroundColor Red
    exit 1
}

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "Project Root: $ProjectRoot" -ForegroundColor Yellow
Write-Host "EC2 IP: $EC2IP" -ForegroundColor Yellow
Write-Host "Key File: $KeyFile" -ForegroundColor Yellow
Write-Host ""

$confirmation = Read-Host "Continue with upload? (y/n)"
if ($confirmation -ne 'y') {
    Write-Host "Aborted." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Step 1: Testing SSH connection..." -ForegroundColor Cyan
try {
    ssh -i $KeyFile -o ConnectTimeout=10 ubuntu@$EC2IP "echo 'Connection successful'"
    Write-Host "✓ SSH connection successful" -ForegroundColor Green
} catch {
    Write-Host "✗ SSH connection failed" -ForegroundColor Red
    Write-Host "Please check:" -ForegroundColor Yellow
    Write-Host "  1. EC2 instance is running" -ForegroundColor Yellow
    Write-Host "  2. Security group allows SSH from your IP" -ForegroundColor Yellow
    Write-Host "  3. Key file has correct permissions" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Step 2: Creating remote directory..." -ForegroundColor Cyan
ssh -i $KeyFile ubuntu@$EC2IP "sudo mkdir -p /opt/afirgen && sudo chown ubuntu:ubuntu /opt/afirgen"
Write-Host "✓ Remote directory created" -ForegroundColor Green

Write-Host ""
Write-Host "Step 3: Uploading application code..." -ForegroundColor Cyan
Write-Host "This may take several minutes..." -ForegroundColor Yellow

# Create list of files to exclude
$ExcludePatterns = @(
    ".git",
    ".hypothesis",
    ".pytest_cache",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.log",
    ".env",
    ".env.local",
    "venv",
    "node_modules",
    "*.md",  # Exclude markdown docs (optional)
    "deployment_*.log"
)

# Build rsync exclude arguments
$ExcludeArgs = $ExcludePatterns | ForEach-Object { "--exclude=$_" }

# Use rsync if available, otherwise use scp
if (Get-Command rsync -ErrorAction SilentlyContinue) {
    Write-Host "Using rsync for faster upload..." -ForegroundColor Yellow
    
    # Upload main backend
    rsync -avz -e "ssh -i $KeyFile" `
        $ExcludeArgs `
        "$ProjectRoot/main backend/" `
        ubuntu@${EC2IP}:/opt/afirgen/main-backend/
    
    # Upload scripts
    rsync -avz -e "ssh -i $KeyFile" `
        $ExcludeArgs `
        "$ProjectRoot/scripts/" `
        ubuntu@${EC2IP}:/opt/afirgen/scripts/
    
    # Upload config files
    scp -i $KeyFile "$ProjectRoot/.env.bedrock" ubuntu@${EC2IP}:/opt/afirgen/.env.bedrock
    scp -i $KeyFile "$ProjectRoot/.env.example" ubuntu@${EC2IP}:/opt/afirgen/.env.example
    
} else {
    Write-Host "Using scp for upload..." -ForegroundColor Yellow
    Write-Host "Note: Install rsync for faster uploads" -ForegroundColor Yellow
    
    # Create temporary directory with only essential files
    $TempDir = "$env:TEMP\afirgen-upload"
    if (Test-Path $TempDir) {
        Remove-Item -Recurse -Force $TempDir
    }
    New-Item -ItemType Directory -Path $TempDir | Out-Null
    
    # Copy essential files
    Write-Host "Preparing files for upload..." -ForegroundColor Yellow
    Copy-Item -Recurse "$ProjectRoot/main backend" "$TempDir/" -Exclude $ExcludePatterns
    Copy-Item -Recurse "$ProjectRoot/scripts" "$TempDir/" -Exclude $ExcludePatterns
    Copy-Item "$ProjectRoot/.env.bedrock" "$TempDir/" -ErrorAction SilentlyContinue
    Copy-Item "$ProjectRoot/.env.example" "$TempDir/" -ErrorAction SilentlyContinue
    
    # Upload using scp
    scp -i $KeyFile -r "$TempDir/*" ubuntu@${EC2IP}:/opt/afirgen/
    
    # Cleanup
    Remove-Item -Recurse -Force $TempDir
}

Write-Host "✓ Code uploaded successfully" -ForegroundColor Green

Write-Host ""
Write-Host "Step 4: Setting permissions..." -ForegroundColor Cyan
ssh -i $KeyFile ubuntu@$EC2IP "chmod +x /opt/afirgen/scripts/*.sh"
Write-Host "✓ Permissions set" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Upload Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Connect to EC2:" -ForegroundColor White
Write-Host "   ssh -i $KeyFile ubuntu@$EC2IP" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Run setup script:" -ForegroundColor White
Write-Host "   cd /opt/afirgen" -ForegroundColor Cyan
Write-Host "   ./scripts/setup-ec2.sh" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Configure environment:" -ForegroundColor White
Write-Host "   nano /opt/afirgen/.env" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Start application:" -ForegroundColor White
Write-Host "   sudo systemctl enable afirgen" -ForegroundColor Cyan
Write-Host "   sudo systemctl start afirgen" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. Verify:" -ForegroundColor White
Write-Host "   curl http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "See QUICK-START-DEPLOYMENT.md for details" -ForegroundColor Yellow
Write-Host ""
