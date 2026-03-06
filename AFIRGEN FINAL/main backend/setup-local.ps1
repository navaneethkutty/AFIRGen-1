# PowerShell script for complete local setup
# Usage: .\setup-local.ps1

Write-Host "=== AFIRGen Backend Local Setup ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python version
Write-Host "Step 1: Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "  $pythonVersion" -ForegroundColor Green

if ($pythonVersion -notmatch "Python 3\.(1[1-9]|[2-9]\d)") {
    Write-Host "  Warning: Python 3.11+ recommended" -ForegroundColor Yellow
}

# Step 2: Create virtual environment if it doesn't exist
Write-Host ""
Write-Host "Step 2: Checking virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path ".\venv")) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
    Write-Host "  ✓ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "  ✓ Virtual environment already exists" -ForegroundColor Green
}

# Step 3: Activate virtual environment
Write-Host ""
Write-Host "Step 3: Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

if ($env:VIRTUAL_ENV) {
    Write-Host "  ✓ Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "  ✗ Failed to activate virtual environment" -ForegroundColor Red
    exit 1
}

# Step 4: Upgrade pip
Write-Host ""
Write-Host "Step 4: Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
Write-Host "  ✓ Pip upgraded" -ForegroundColor Green

# Step 5: Install dependencies
Write-Host ""
Write-Host "Step 5: Installing dependencies..." -ForegroundColor Yellow
if (Test-Path ".\requirements.txt") {
    pip install -r requirements.txt
    Write-Host "  ✓ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "  ✗ requirements.txt not found" -ForegroundColor Red
    exit 1
}

# Step 6: Check .env file
Write-Host ""
Write-Host "Step 6: Checking environment configuration..." -ForegroundColor Yellow
if (Test-Path ".\.env") {
    Write-Host "  ✓ .env file exists" -ForegroundColor Green
} else {
    Write-Host "  ⚠ .env file not found" -ForegroundColor Yellow
    Write-Host "  Creating .env from .env.example..." -ForegroundColor Cyan
    if (Test-Path ".\.env.example") {
        Copy-Item ".\.env.example" ".\.env"
        Write-Host "  ✓ .env file created" -ForegroundColor Green
        Write-Host "  ⚠ Please edit .env file with your configuration" -ForegroundColor Yellow
    } else {
        Write-Host "  ✗ .env.example not found" -ForegroundColor Red
    }
}

# Step 7: Create logs directory
Write-Host ""
Write-Host "Step 7: Creating logs directory..." -ForegroundColor Yellow
if (-not (Test-Path ".\logs")) {
    New-Item -ItemType Directory -Path ".\logs" | Out-Null
    Write-Host "  ✓ Logs directory created" -ForegroundColor Green
} else {
    Write-Host "  ✓ Logs directory already exists" -ForegroundColor Green
}

# Summary
Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Edit .env file with your AWS and database credentials" -ForegroundColor White
Write-Host "  2. Run tests: pytest -v" -ForegroundColor White
Write-Host "  3. Start backend: uvicorn agentv5:app --host 0.0.0.0 --port 8000 --reload" -ForegroundColor White
Write-Host ""
Write-Host "For detailed instructions, see LOCAL-TESTING-GUIDE.md" -ForegroundColor Cyan
Write-Host ""
