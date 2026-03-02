# Pre-Deployment Verification Script (PowerShell)
# Checks all prerequisites before production deployment

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "AFIRGen Pre-Deployment Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$ChecksPassed = 0
$ChecksFailed = 0
$Warnings = 0

function Test-Command {
    param($Name, $Command)
    
    Write-Host "Checking $Name... " -NoNewline
    
    try {
        $null = Invoke-Expression $Command 2>&1
        if ($LASTEXITCODE -eq 0 -or $null -eq $LASTEXITCODE) {
            Write-Host "✅ PASS" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ FAIL" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ FAIL" -ForegroundColor Red
        return $false
    }
}

Write-Host "Running pre-deployment checks..." -ForegroundColor Yellow
Write-Host ""

# ============================================================================
# 1. System Requirements
# ============================================================================

Write-Host "1. System Requirements" -ForegroundColor Cyan
Write-Host "----------------------"

if (Test-Command "AWS CLI" "aws --version") { $ChecksPassed++ } else { $ChecksFailed++ }
if (Test-Command "Terraform" "terraform --version") { $ChecksPassed++ } else { $ChecksFailed++ }
if (Test-Command "Python" "python --version") { $ChecksPassed++ } else { $ChecksFailed++ }
if (Test-Command "Git" "git --version") { $ChecksPassed++ } else { $ChecksFailed++ }

Write-Host ""

# ============================================================================
# 2. AWS Configuration
# ============================================================================

Write-Host "2. AWS Configuration" -ForegroundColor Cyan
Write-Host "--------------------"

if (Test-Command "AWS Credentials" "aws sts get-caller-identity") {
    $ChecksPassed++
    
    # Get AWS account
    $AwsAccount = aws sts get-caller-identity --query Account --output text 2>$null
    Write-Host "AWS Account: $AwsAccount"
} else {
    $ChecksFailed++
}

# Check AWS region
$AwsRegion = aws configure get region 2>$null
if ($AwsRegion -eq "us-east-1") {
    Write-Host "AWS Region: ✅ us-east-1" -ForegroundColor Green
    $ChecksPassed++
} else {
    Write-Host "AWS Region: ⚠️  $AwsRegion (expected us-east-1)" -ForegroundColor Yellow
    $Warnings++
}

Write-Host ""

# ============================================================================
# 3. Environment Configuration
# ============================================================================

Write-Host "3. Environment Configuration" -ForegroundColor Cyan
Write-Host "----------------------------"

if (Test-Path ".env.bedrock") {
    Write-Host ".env.bedrock: ✅ OK" -ForegroundColor Green
    $ChecksPassed++
} else {
    Write-Host ".env.bedrock: ❌ FAIL" -ForegroundColor Red
    $ChecksFailed++
}

if (Test-Path "terraform\free-tier\terraform.tfvars") {
    Write-Host "terraform.tfvars: ✅ OK" -ForegroundColor Green
    $ChecksPassed++
} else {
    Write-Host "terraform.tfvars: ❌ FAIL" -ForegroundColor Red
    $ChecksFailed++
}

Write-Host ""

# ============================================================================
# 4. Terraform Validation
# ============================================================================

Write-Host "4. Terraform Validation" -ForegroundColor Cyan
Write-Host "-----------------------"

Push-Location "terraform\free-tier"

if (Test-Command "Terraform init" "terraform init -backend=false") {
    $ChecksPassed++
} else {
    $ChecksFailed++
}

if (Test-Command "Terraform validate" "terraform validate") {
    $ChecksPassed++
} else {
    $ChecksFailed++
}

Pop-Location

Write-Host ""

# ============================================================================
# 5. Code Quality
# ============================================================================

Write-Host "5. Code Quality" -ForegroundColor Cyan
Write-Host "---------------"

if (Test-Path "tests\api\test_endpoints_minimal.py") {
    Write-Host "Running minimal tests... " -NoNewline
    try {
        $process = Start-Process -FilePath "python" -ArgumentList "tests\api\test_endpoints_minimal.py" -NoNewWindow -Wait -PassThru
        $exitCode = $process.ExitCode
        if ($exitCode -eq 0) {
            Write-Host "✅ PASS" -ForegroundColor Green
            $ChecksPassed++
        } else {
            Write-Host "❌ FAIL (exit code: $exitCode)" -ForegroundColor Red
            $ChecksFailed++
        }
    } catch {
        Write-Host "❌ FAIL (error: $_)" -ForegroundColor Red
        $ChecksFailed++
    }
} else {
    Write-Host "Minimal tests: ⚠️  WARNING (not found)" -ForegroundColor Yellow
    $Warnings++
}

if (Test-Path "bugs.json") {
    Write-Host "Bug tracking: ✅ OK" -ForegroundColor Green
    $ChecksPassed++
} else {
    Write-Host "Bug tracking: ⚠️  WARNING (bugs.json not found)" -ForegroundColor Yellow
    $Warnings++
}

Write-Host ""

# ============================================================================
# 6. Scripts
# ============================================================================

Write-Host "6. Deployment Scripts" -ForegroundColor Cyan
Write-Host "---------------------"

if (Test-Path "scripts\deploy-production-optimized.sh") {
    Write-Host "Deployment script: ✅ OK" -ForegroundColor Green
    $ChecksPassed++
} else {
    Write-Host "Deployment script: ❌ FAIL" -ForegroundColor Red
    $ChecksFailed++
}

if (Test-Path "scripts\rollback-to-gguf.sh") {
    Write-Host "Rollback script: ✅ OK" -ForegroundColor Green
    $ChecksPassed++
} else {
    Write-Host "Rollback script: ❌ FAIL" -ForegroundColor Red
    $ChecksFailed++
}

Write-Host ""

# ============================================================================
# 7. Documentation
# ============================================================================

Write-Host "7. Documentation" -ForegroundColor Cyan
Write-Host "----------------"

if (Test-Path "FINAL-PRODUCTION-READINESS-REPORT.md") {
    Write-Host "Production readiness report: ✅ OK" -ForegroundColor Green
    $ChecksPassed++
} else {
    Write-Host "Production readiness report: ❌ FAIL" -ForegroundColor Red
    $ChecksFailed++
}

if (Test-Path "PRODUCTION-DEPLOYMENT-README.md") {
    Write-Host "Deployment README: ✅ OK" -ForegroundColor Green
    $ChecksPassed++
} else {
    Write-Host "Deployment README: ❌ FAIL" -ForegroundColor Red
    $ChecksFailed++
}

Write-Host ""

# ============================================================================
# Summary
# ============================================================================

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "VERIFICATION SUMMARY" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Checks Passed:  " -NoNewline
Write-Host $ChecksPassed -ForegroundColor Green
Write-Host "Checks Failed:  " -NoNewline
Write-Host $ChecksFailed -ForegroundColor Red
Write-Host "Warnings:       " -NoNewline
Write-Host $Warnings -ForegroundColor Yellow
Write-Host ""

$TotalChecks = $ChecksPassed + $ChecksFailed
if ($TotalChecks -gt 0) {
    $SuccessRate = [math]::Round(($ChecksPassed / $TotalChecks) * 100, 1)
    Write-Host "Success Rate: $SuccessRate%"
    Write-Host ""
}

if ($ChecksFailed -eq 0) {
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "✅ ALL CHECKS PASSED" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "System is ready for production deployment!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "1. Review PRE-DEPLOYMENT-CHECKLIST.md"
    Write-Host "2. Notify stakeholders"
    Write-Host "3. Run deployment script:"
    Write-Host "   cd 'AFIRGEN FINAL\scripts'"
    Write-Host "   bash deploy-production-optimized.sh"
    Write-Host ""
    exit 0
} else {
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host "❌ DEPLOYMENT BLOCKED" -ForegroundColor Red
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please fix the failed checks before deploying." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Common fixes:"
    Write-Host "- AWS credentials: aws configure"
    Write-Host "- Terraform: cd terraform\free-tier; terraform init"
    Write-Host "- Environment: copy .env.example .env.bedrock"
    Write-Host ""
    exit 1
}
