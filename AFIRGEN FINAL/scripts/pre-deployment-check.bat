@echo off
REM Pre-Deployment Verification Script (Windows)
REM Checks all prerequisites before production deployment

setlocal enabledelayedexpansion

echo ==========================================
echo AFIRGen Pre-Deployment Verification
echo ==========================================
echo.

set CHECKS_PASSED=0
set CHECKS_FAILED=0
set WARNINGS=0

echo Running pre-deployment checks...
echo.

REM ============================================================================
REM 1. System Requirements
REM ============================================================================

echo 1. System Requirements
echo ----------------------

REM Check AWS CLI
aws --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [32mAWS CLI: OK[0m
    set /a CHECKS_PASSED+=1
) else (
    echo [31mAWS CLI: FAIL[0m
    set /a CHECKS_FAILED+=1
)

REM Check Terraform
terraform --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [32mTerraform: OK[0m
    set /a CHECKS_PASSED+=1
) else (
    echo [31mTerraform: FAIL[0m
    set /a CHECKS_FAILED+=1
)

REM Check Python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [32mPython: OK[0m
    set /a CHECKS_PASSED+=1
) else (
    echo [31mPython: FAIL[0m
    set /a CHECKS_FAILED+=1
)

REM Check Git
git --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [32mGit: OK[0m
    set /a CHECKS_PASSED+=1
) else (
    echo [31mGit: FAIL[0m
    set /a CHECKS_FAILED+=1
)

echo.

REM ============================================================================
REM 2. AWS Configuration
REM ============================================================================

echo 2. AWS Configuration
echo --------------------

REM Check AWS credentials
aws sts get-caller-identity >nul 2>&1
if %errorlevel% equ 0 (
    echo [32mAWS Credentials: OK[0m
    set /a CHECKS_PASSED+=1
    
    REM Get AWS account
    for /f "tokens=*" %%a in ('aws sts get-caller-identity --query Account --output text 2^>nul') do set AWS_ACCOUNT=%%a
    echo AWS Account: !AWS_ACCOUNT!
) else (
    echo [31mAWS Credentials: FAIL[0m
    set /a CHECKS_FAILED+=1
)

REM Check AWS region
for /f "tokens=*" %%a in ('aws configure get region 2^>nul') do set AWS_REGION=%%a
if "!AWS_REGION!"=="us-east-1" (
    echo [32mAWS Region: OK (us-east-1)[0m
    set /a CHECKS_PASSED+=1
) else (
    echo [33mAWS Region: WARNING (!AWS_REGION! - expected us-east-1)[0m
    set /a WARNINGS+=1
)

echo.

REM ============================================================================
REM 3. Environment Configuration
REM ============================================================================

echo 3. Environment Configuration
echo ----------------------------

if exist ".env.bedrock" (
    echo [32m.env.bedrock: OK[0m
    set /a CHECKS_PASSED+=1
) else (
    echo [31m.env.bedrock: FAIL[0m
    set /a CHECKS_FAILED+=1
)

if exist "terraform\free-tier\terraform.tfvars" (
    echo [32mterraform.tfvars: OK[0m
    set /a CHECKS_PASSED+=1
) else (
    echo [31mterraform.tfvars: FAIL[0m
    set /a CHECKS_FAILED+=1
)

echo.

REM ============================================================================
REM 4. Terraform Validation
REM ============================================================================

echo 4. Terraform Validation
echo -----------------------

cd terraform\free-tier

terraform init -backend=false >nul 2>&1
if %errorlevel% equ 0 (
    echo [32mTerraform init: OK[0m
    set /a CHECKS_PASSED+=1
) else (
    echo [31mTerraform init: FAIL[0m
    set /a CHECKS_FAILED+=1
)

terraform validate >nul 2>&1
if %errorlevel% equ 0 (
    echo [32mTerraform validate: OK[0m
    set /a CHECKS_PASSED+=1
) else (
    echo [31mTerraform validate: FAIL[0m
    set /a CHECKS_FAILED+=1
)

cd ..\..

echo.

REM ============================================================================
REM 5. Code Quality
REM ============================================================================

echo 5. Code Quality
echo ---------------

if exist "tests\api\test_endpoints_minimal.py" (
    python tests\api\test_endpoints_minimal.py >nul 2>&1
    if !errorlevel! equ 0 (
        echo [32mMinimal tests: OK[0m
        set /a CHECKS_PASSED+=1
    ) else (
        echo [31mMinimal tests: FAIL[0m
        set /a CHECKS_FAILED+=1
    )
) else (
    echo [33mMinimal tests: WARNING (not found)[0m
    set /a WARNINGS+=1
)

if exist "bugs.json" (
    echo [32mBug tracking: OK[0m
    set /a CHECKS_PASSED+=1
) else (
    echo [33mBug tracking: WARNING (bugs.json not found)[0m
    set /a WARNINGS+=1
)

echo.

REM ============================================================================
REM 6. Scripts
REM ============================================================================

echo 6. Deployment Scripts
echo ---------------------

if exist "scripts\deploy-production-optimized.sh" (
    echo [32mDeployment script: OK[0m
    set /a CHECKS_PASSED+=1
) else (
    echo [31mDeployment script: FAIL[0m
    set /a CHECKS_FAILED+=1
)

if exist "scripts\rollback-to-gguf.sh" (
    echo [32mRollback script: OK[0m
    set /a CHECKS_PASSED+=1
) else (
    echo [31mRollback script: FAIL[0m
    set /a CHECKS_FAILED+=1
)

echo.

REM ============================================================================
REM 7. Documentation
REM ============================================================================

echo 7. Documentation
echo ----------------

if exist "FINAL-PRODUCTION-READINESS-REPORT.md" (
    echo [32mProduction readiness report: OK[0m
    set /a CHECKS_PASSED+=1
) else (
    echo [31mProduction readiness report: FAIL[0m
    set /a CHECKS_FAILED+=1
)

if exist "PRODUCTION-DEPLOYMENT-README.md" (
    echo [32mDeployment README: OK[0m
    set /a CHECKS_PASSED+=1
) else (
    echo [31mDeployment README: FAIL[0m
    set /a CHECKS_FAILED+=1
)

echo.

REM ============================================================================
REM Summary
REM ============================================================================

echo ==========================================
echo VERIFICATION SUMMARY
echo ==========================================
echo.
echo Checks Passed:  %CHECKS_PASSED%
echo Checks Failed:  %CHECKS_FAILED%
echo Warnings:       %WARNINGS%
echo.

if %CHECKS_FAILED% equ 0 (
    echo [32m==========================================
    echo ALL CHECKS PASSED
    echo ==========================================[0m
    echo.
    echo System is ready for production deployment!
    echo.
    echo Next steps:
    echo 1. Review PRE-DEPLOYMENT-CHECKLIST.md
    echo 2. Notify stakeholders
    echo 3. Run deployment script:
    echo    cd "AFIRGEN FINAL\scripts"
    echo    bash deploy-production-optimized.sh
    echo.
    exit /b 0
) else (
    echo [31m==========================================
    echo DEPLOYMENT BLOCKED
    echo ==========================================[0m
    echo.
    echo Please fix the failed checks before deploying.
    echo.
    echo Common fixes:
    echo - AWS credentials: aws configure
    echo - Terraform: cd terraform\free-tier ^&^& terraform init
    echo - Environment: copy .env.example .env.bedrock
    echo.
    exit /b 1
)
