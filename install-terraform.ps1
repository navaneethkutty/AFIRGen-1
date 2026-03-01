# Simple Terraform Installer for Windows
# Run this in PowerShell

Write-Host "=========================================="
Write-Host "Installing Terraform for Windows"
Write-Host "=========================================="
Write-Host ""

# Check if Chocolatey is installed
if (Get-Command choco -ErrorAction SilentlyContinue) {
    Write-Host "Using Chocolatey to install Terraform..." -ForegroundColor Yellow
    choco install terraform -y
    Write-Host "✓ Terraform installed via Chocolatey" -ForegroundColor Green
} else {
    Write-Host "Chocolatey not found. Installing Terraform manually..." -ForegroundColor Yellow
    
    # Download Terraform
    $terraformVersion = "1.6.6"
    $downloadUrl = "https://releases.hashicorp.com/terraform/${terraformVersion}/terraform_${terraformVersion}_windows_amd64.zip"
    $zipPath = "$env:TEMP\terraform.zip"
    $installPath = "C:\terraform"
    
    Write-Host "Downloading Terraform $terraformVersion..." -ForegroundColor Cyan
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing
        Write-Host "✓ Download complete" -ForegroundColor Green
    } catch {
        Write-Host "✗ Download failed: $_" -ForegroundColor Red
        exit 1
    }
    
    # Extract
    Write-Host "Extracting Terraform..." -ForegroundColor Cyan
    if (Test-Path $installPath) {
        Remove-Item $installPath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $installPath -Force | Out-Null
    Expand-Archive -Path $zipPath -DestinationPath $installPath -Force
    
    # Add to PATH
    Write-Host "Adding Terraform to PATH..." -ForegroundColor Cyan
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$installPath*") {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$installPath", "User")
        Write-Host "✓ Added to PATH" -ForegroundColor Green
    }
    
    # Update current session PATH
    $env:Path = "$env:Path;$installPath"
    
    # Clean up
    Remove-Item $zipPath -ErrorAction SilentlyContinue
    
    Write-Host "✓ Terraform installed to $installPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "=========================================="
Write-Host "Installation Complete!"
Write-Host "=========================================="
Write-Host ""
Write-Host "Verifying installation..."
terraform --version

Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. If you see the version above, you're ready!"
Write-Host "  2. If not, close and reopen PowerShell"
Write-Host "  3. Then run: make deploy-all"
Write-Host ""
