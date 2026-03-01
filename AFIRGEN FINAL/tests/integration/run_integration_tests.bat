@echo off
REM Script to run integration tests with proper environment setup

echo ==========================================
echo AFIRGen Integration Tests
echo ==========================================
echo.

if "%1" NEQ "--skip-check" (
    echo WARNING: Integration tests will call real AWS services and incur costs!
    echo.
    echo Estimated cost per test run: $0.50 - $2.00
    echo.
    set /p confirm="Do you want to continue? (yes/no): "
    
    if /i NOT "%confirm%"=="yes" (
        echo Integration tests cancelled.
        exit /b 0
    )
)

echo.
echo Checking environment variables...
echo.

REM Check required environment variables
if "%AWS_REGION%"=="" (
    echo ERROR: AWS_REGION not set
    set missing=1
) else (
    echo OK: AWS_REGION is set
)

if "%S3_BUCKET_NAME%"=="" (
    echo ERROR: S3_BUCKET_NAME not set
    set missing=1
) else (
    echo OK: S3_BUCKET_NAME is set
)

if "%VECTOR_DB_TYPE%"=="" (
    echo ERROR: VECTOR_DB_TYPE not set
    set missing=1
) else (
    echo OK: VECTOR_DB_TYPE is set
)

REM Check vector DB specific variables
if "%VECTOR_DB_TYPE%"=="opensearch" (
    if "%OPENSEARCH_ENDPOINT%"=="" (
        echo ERROR: OPENSEARCH_ENDPOINT not set
        set missing=1
    ) else (
        echo OK: OPENSEARCH_ENDPOINT is set
    )
)

if "%VECTOR_DB_TYPE%"=="aurora_pgvector" (
    if "%AURORA_HOST%"=="" (
        echo ERROR: AURORA_HOST not set
        set missing=1
    ) else (
        echo OK: AURORA_HOST is set
    )
)

if defined missing (
    echo.
    echo Please set missing environment variables and try again.
    exit /b 1
)

echo.
echo All required environment variables are set
echo.

echo Checking AWS credentials...
aws sts get-caller-identity >nul 2>&1
if errorlevel 1 (
    echo ERROR: AWS credentials are not configured or invalid
    exit /b 1
)
echo OK: AWS credentials are valid
echo.

echo Installing test dependencies...
pip install -q -r tests/requirements-test.txt

echo.
echo Running integration tests...
echo.

REM Run pytest with integration marker
pytest tests/integration/ --integration -v --tb=short --color=yes %*

if errorlevel 1 (
    echo.
    echo ==========================================
    echo Some integration tests failed
    echo ==========================================
    exit /b 1
) else (
    echo.
    echo ==========================================
    echo All integration tests passed!
    echo ==========================================
    exit /b 0
)
