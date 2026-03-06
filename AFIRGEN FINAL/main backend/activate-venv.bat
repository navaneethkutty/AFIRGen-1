@echo off
REM Batch script to activate virtual environment
REM Usage: activate-venv.bat

echo Activating virtual environment...

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found!
    echo Please create it first with: python -m venv venv
    exit /b 1
)

REM Activate venv
call venv\Scripts\activate.bat

REM Verify activation
if defined VIRTUAL_ENV (
    echo Virtual environment activated successfully!
    python --version
    echo Virtual environment: %VIRTUAL_ENV%
    echo.
    echo To deactivate, run: deactivate
) else (
    echo Failed to activate virtual environment
    exit /b 1
)
