# Simple AWS CLI Installer for Windows
# Run this in PowerShell (doesn't need Administrator)

Write-Host "=========================================="
Write-Host "Installing AWS CLI for Windows"
Write-Host "=========================================="
Write-Host ""

# Download AWS CLI installer
$installerUrl = "https://awscli.amazonaws.com/AWSCLIV2.msi"
$installerPath = "$env:TEMP\AWSCLIV2.msi"

Write-Host "Downloading AWS CLI installer..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
    Write-Host "✓ Download complete" -ForegroundColor Green
} catch {
    Write-Host "✗ Download failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Installing AWS CLI..." -ForegroundColor Yellow
Write-Host "(This may take a minute and open an installer window)" -ForegroundColor Cyan

try {
    Start-Process msiexec.exe -ArgumentList "/i `"$installerPath`" /qn" -Wait
    Write-Host "✓ AWS CLI installed" -ForegroundColor Green
} catch {
    Write-Host "✗ Installation failed: $_" -ForegroundColor Red
    exit 1
}

# Clean up
Remove-Item $installerPath -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=========================================="
Write-Host "Installation Complete!"
Write-Host "=========================================="
Write-Host ""
Write-Host "IMPORTANT: Close and reopen PowerShell" -ForegroundColor Yellow
Write-Host ""
Write-Host "Then verify installation:"
Write-Host "  aws --version"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Close this PowerShell window"
Write-Host "  2. Open a new PowerShell window"
Write-Host "  3. Run: aws configure"
Write-Host ""
