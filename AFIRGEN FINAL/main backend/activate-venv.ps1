# PowerShell script to activate virtual environment
# Usage: .\activate-venv.ps1

Write-Host "Activating virtual environment..." -ForegroundColor Green

# Check if venv exists
if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "Error: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please create it first with: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

# Activate venv
& ".\venv\Scripts\Activate.ps1"

# Verify activation
if ($env:VIRTUAL_ENV) {
    Write-Host "✓ Virtual environment activated successfully!" -ForegroundColor Green
    Write-Host "Python version: $(python --version)" -ForegroundColor Cyan
    Write-Host "Virtual environment: $env:VIRTUAL_ENV" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To deactivate, run: deactivate" -ForegroundColor Yellow
} else {
    Write-Host "✗ Failed to activate virtual environment" -ForegroundColor Red
    exit 1
}
