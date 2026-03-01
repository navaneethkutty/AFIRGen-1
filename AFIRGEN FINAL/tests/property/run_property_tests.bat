@echo off
REM Run property-based tests for AFIRGen Bedrock Migration

echo Running Property-Based Tests...
echo ================================
echo.

REM Set Python path
set PYTHONPATH=%PYTHONPATH%;%CD%

REM Run tests with different profiles
if "%1"=="quick" (
    echo Running quick tests (20 examples per test^)...
    set HYPOTHESIS_PROFILE=dev
    python -m pytest tests/property/ -v --tb=short
) else if "%1"=="ci" (
    echo Running CI tests (100 examples per test^)...
    set HYPOTHESIS_PROFILE=ci
    python -m pytest tests/property/ -v --tb=short --hypothesis-show-statistics
) else if "%1"=="debug" (
    echo Running debug tests (10 examples per test, verbose^)...
    set HYPOTHESIS_PROFILE=debug
    python -m pytest tests/property/ -v --tb=long
) else (
    echo Running default tests (50 examples per test^)...
    python -m pytest tests/property/ -v --tb=short
)

echo.
echo ================================
echo Property tests completed!
