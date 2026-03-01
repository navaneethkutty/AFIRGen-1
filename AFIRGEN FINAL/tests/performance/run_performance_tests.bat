@echo off
REM Performance Test Runner for AFIRGen Bedrock Migration (Windows)
REM This script runs performance tests and generates reports

setlocal enabledelayedexpansion

echo ==========================================
echo AFIRGen Performance Test Runner
echo ==========================================
echo.

REM Check if --skip-integration-check flag is provided
if "%1" neq "--skip-integration-check" (
    echo Warning: Performance tests will make real AWS API calls
    echo This will incur costs. Continue? (y/n)
    set /p response=
    if /i "!response!" neq "y" (
        echo Aborted.
        exit /b 0
    )
)

REM Check required environment variables
echo Checking environment variables...

set MISSING_VARS=

if "%AWS_REGION%"=="" (
    set MISSING_VARS=!MISSING_VARS! AWS_REGION
)
if "%S3_BUCKET_NAME%"=="" (
    set MISSING_VARS=!MISSING_VARS! S3_BUCKET_NAME
)
if "%VECTOR_DB_TYPE%"=="" (
    set MISSING_VARS=!MISSING_VARS! VECTOR_DB_TYPE
)

if not "!MISSING_VARS!"=="" (
    echo Error: Missing required environment variables:
    echo !MISSING_VARS!
    exit /b 1
)

REM Check vector database specific variables
if "%VECTOR_DB_TYPE%"=="opensearch" (
    if "%OPENSEARCH_ENDPOINT%"=="" (
        echo Error: OPENSEARCH_ENDPOINT not set for opensearch database type
        exit /b 1
    )
) else if "%VECTOR_DB_TYPE%"=="aurora_pgvector" (
    if "%AURORA_HOST%"=="" (
        echo Error: AURORA_HOST not set for aurora_pgvector database type
        exit /b 1
    )
) else (
    echo Error: Invalid VECTOR_DB_TYPE. Must be 'opensearch' or 'aurora_pgvector'
    exit /b 1
)

echo [OK] Environment variables validated
echo.

REM Create results directory
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set RESULTS_DIR=performance_results_%mydate%_%mytime%
mkdir "%RESULTS_DIR%"

echo Results will be saved to: %RESULTS_DIR%
echo.

REM Run latency tests
echo ==========================================
echo Running Latency Tests...
echo ==========================================
pytest tests/performance/test_latency.py --integration -v -s --junitxml="%RESULTS_DIR%/latency_results.xml" --tb=short > "%RESULTS_DIR%/latency_output.log" 2>&1
set LATENCY_EXIT_CODE=%ERRORLEVEL%

REM Display latency test output
type "%RESULTS_DIR%/latency_output.log"

echo.
echo ==========================================
echo Running Concurrency Tests...
echo ==========================================
pytest tests/performance/test_concurrency.py --integration -v -s --junitxml="%RESULTS_DIR%/concurrency_results.xml" --tb=short > "%RESULTS_DIR%/concurrency_output.log" 2>&1
set CONCURRENCY_EXIT_CODE=%ERRORLEVEL%

REM Display concurrency test output
type "%RESULTS_DIR%/concurrency_output.log"

REM Generate summary report
echo.
echo ==========================================
echo Test Summary
echo ==========================================

if %LATENCY_EXIT_CODE% equ 0 (
    echo [OK] Latency tests: PASSED
) else (
    echo [FAIL] Latency tests: FAILED
)

if %CONCURRENCY_EXIT_CODE% equ 0 (
    echo [OK] Concurrency tests: PASSED
) else (
    echo [FAIL] Concurrency tests: FAILED
)

echo.
echo Results saved to: %RESULTS_DIR%
echo.

REM Create summary file
(
echo # Performance Test Summary
echo.
echo **Date:** %date% %time%
echo **AWS Region:** %AWS_REGION%
echo **Vector DB Type:** %VECTOR_DB_TYPE%
echo.
echo ## Test Results
echo.
echo ### Latency Tests
echo - Exit Code: %LATENCY_EXIT_CODE%
if %LATENCY_EXIT_CODE% equ 0 (
    echo - Status: PASSED
) else (
    echo - Status: FAILED
)
echo - Log: latency_output.log
echo - XML Report: latency_results.xml
echo.
echo ### Concurrency Tests
echo - Exit Code: %CONCURRENCY_EXIT_CODE%
if %CONCURRENCY_EXIT_CODE% equ 0 (
    echo - Status: PASSED
) else (
    echo - Status: FAILED
)
echo - Log: concurrency_output.log
echo - XML Report: concurrency_results.xml
echo.
echo ## Files Generated
echo.
echo - `latency_output.log`: Detailed output from latency tests
echo - `concurrency_output.log`: Detailed output from concurrency tests
echo - `latency_results.xml`: JUnit XML report for latency tests
echo - `concurrency_results.xml`: JUnit XML report for concurrency tests
echo.
echo ## Next Steps
echo.
echo 1. Review the log files for detailed performance metrics
echo 2. Check for any failed tests and investigate root causes
echo 3. Compare results with baseline/previous runs
echo 4. Update performance documentation if needed
) > "%RESULTS_DIR%/SUMMARY.md"

echo Summary report created: %RESULTS_DIR%/SUMMARY.md
echo.

REM Exit with failure if any tests failed
if %LATENCY_EXIT_CODE% neq 0 (
    echo Some tests failed. Check the logs for details.
    exit /b 1
)
if %CONCURRENCY_EXIT_CODE% neq 0 (
    echo Some tests failed. Check the logs for details.
    exit /b 1
)

echo All performance tests passed!
exit /b 0
