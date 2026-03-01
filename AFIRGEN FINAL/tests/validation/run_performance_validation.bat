@echo off
REM Performance Validation Runner for Windows
REM This script runs the performance validation against the AFIRGen application

echo ============================================================
echo AFIRGen Bedrock Migration - Performance Validation
echo ============================================================
echo.

REM Check if URL argument is provided
if "%1"=="" (
    set BASE_URL=http://localhost:8000
    echo Using default URL: %BASE_URL%
) else (
    set BASE_URL=%1
    echo Using provided URL: %BASE_URL%
)

echo.
echo Checking if application is accessible...
curl -s -o nul -w "HTTP Status: %%{http_code}\n" %BASE_URL%/health

if errorlevel 1 (
    echo.
    echo ERROR: Cannot connect to application at %BASE_URL%
    echo.
    echo Please ensure the application is running:
    echo   cd "AFIRGEN FINAL/main backend"
    echo   python agentv5.py
    echo.
    pause
    exit /b 1
)

echo.
echo Application is accessible. Starting performance validation...
echo.

REM Run the performance validation script
python performance_validation.py %BASE_URL%

if errorlevel 1 (
    echo.
    echo ============================================================
    echo PERFORMANCE VALIDATION FAILED
    echo ============================================================
    echo.
    echo Please review the output above for details.
    echo Check the troubleshooting guide in README.md
    echo.
) else (
    echo.
    echo ============================================================
    echo PERFORMANCE VALIDATION COMPLETED
    echo ============================================================
    echo.
    echo Report saved to: performance_validation_report.json
    echo.
)

pause
