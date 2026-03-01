# AFIRGen Windows Tool Installation Script
# Run this in PowerShell as Administrator

Write-Host "=========================================="
Write-Host "AFIRGen Tool Installation for Windows"
Write-Host "=========================================="
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Check if Chocolatey is installed
Write-Host "Checking for Chocolatey package manager..."
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Chocolatey..." -ForegroundColor Yellow
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    Write-Host "✓ Chocolatey installed" -ForegroundColor Green
} else {
    Write-Host "✓ Chocolatey already installed" -ForegroundColor Green
}

Write-Host ""

# Install Terraform
Write-Host "Installing Terraform..."
if (Get-Command terraform -ErrorAction SilentlyContinue) {
    Write-Host "✓ Terraform already installed" -ForegroundColor Green
    terraform --version
} else {
    choco install terraform -y
    Write-Host "✓ Terraform installed" -ForegroundColor Green
}

Write-Host ""

# Install AWS CLI
Write-Host "Installing AWS CLI..."
if (Get-Command aws -ErrorAction SilentlyContinue) {
    Write-Host "✓ AWS CLI already installed" -ForegroundColor Green
    aws --version
} else {
    choco install awscli -y
    Write-Host "✓ AWS CLI installed" -ForegroundColor Green
}

Write-Host ""

# Install Make
Write-Host "Installing Make..."
if (Get-Command make -ErrorAction SilentlyContinue) {
    Write-Host "✓ Make already installed" -ForegroundColor Green
    make --version
} else {
    choco install make -y
    Write-Host "✓ Make installed" -ForegroundColor Green
}

Write-Host ""

# Install Python (needed for HuggingFace downloads)
Write-Host "Installing Python..."
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "✓ Python already installed" -ForegroundColor Green
    python --version
} else {
    choco install python -y
    Write-Host "✓ Python installed" -ForegroundColor Green
}

Write-Host ""
Write-Host "=========================================="
Write-Host "Installation Complete!"
Write-Host "=========================================="
Write-Host ""
Write-Host "IMPORTANT: Close and reopen PowerShell for changes to take effect" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Close this PowerShell window"
Write-Host "2. Open a new PowerShell window (normal, not admin)"
Write-Host "3. Navigate to your project: cd 'C:\Users\knith\OneDrive\Desktop\AFIRGen-1'"
Write-Host "4. Run: make setup-aws"
Write-Host "5. Run: make deploy-all"
Write-Host ""
