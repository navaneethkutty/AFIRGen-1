@echo off
REM Upload AFIRGen Code to EC2 (Windows Batch)
REM Usage: upload-to-ec2.bat path\to\your-key.pem

setlocal enabledelayedexpansion

echo ==========================================
echo AFIRGen Code Upload to EC2
echo ==========================================
echo.

REM Check if key file is provided
if "%~1"=="" (
    echo ERROR: Please provide SSH key file path
    echo Usage: upload-to-ec2.bat path\to\your-key.pem
    exit /b 1
)

set KEY_FILE=%~1
set EC2_IP=98.86.30.145

REM Verify key file exists
if not exist "%KEY_FILE%" (
    echo ERROR: Key file not found: %KEY_FILE%
    exit /b 1
)

echo Key File: %KEY_FILE%
echo EC2 IP: %EC2_IP%
echo.

set /p CONFIRM="Continue with upload? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Aborted.
    exit /b 0
)

echo.
echo Step 1: Testing SSH connection...
ssh -i "%KEY_FILE%" -o ConnectTimeout=10 ubuntu@%EC2_IP% "echo Connection successful"
if errorlevel 1 (
    echo ERROR: SSH connection failed
    echo Please check:
    echo   1. EC2 instance is running
    echo   2. Security group allows SSH from your IP
    echo   3. Key file has correct permissions
    exit /b 1
)
echo [OK] SSH connection successful
echo.

echo Step 2: Creating remote directory...
ssh -i "%KEY_FILE%" ubuntu@%EC2_IP% "sudo mkdir -p /opt/afirgen && sudo chown ubuntu:ubuntu /opt/afirgen"
echo [OK] Remote directory created
echo.

echo Step 3: Uploading application code...
echo This may take several minutes...
echo.

REM Get script directory
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM Upload main backend
echo Uploading main backend...
scp -i "%KEY_FILE%" -r "%PROJECT_ROOT%\main backend" ubuntu@%EC2_IP%:/opt/afirgen/

REM Upload scripts
echo Uploading scripts...
scp -i "%KEY_FILE%" -r "%PROJECT_ROOT%\scripts" ubuntu@%EC2_IP%:/opt/afirgen/

REM Upload config files
echo Uploading config files...
scp -i "%KEY_FILE%" "%PROJECT_ROOT%\.env.bedrock" ubuntu@%EC2_IP%:/opt/afirgen/.env.bedrock 2>nul
scp -i "%KEY_FILE%" "%PROJECT_ROOT%\.env.example" ubuntu@%EC2_IP%:/opt/afirgen/.env.example 2>nul

echo [OK] Code uploaded successfully
echo.

echo Step 4: Setting permissions...
ssh -i "%KEY_FILE%" ubuntu@%EC2_IP% "chmod +x /opt/afirgen/scripts/*.sh"
echo [OK] Permissions set
echo.

echo ==========================================
echo Upload Complete!
echo ==========================================
echo.
echo Next steps:
echo.
echo 1. Connect to EC2:
echo    ssh -i "%KEY_FILE%" ubuntu@%EC2_IP%
echo.
echo 2. Run setup script:
echo    cd /opt/afirgen
echo    ./scripts/setup-ec2.sh
echo.
echo 3. Configure environment:
echo    nano /opt/afirgen/.env
echo.
echo 4. Start application:
echo    sudo systemctl enable afirgen
echo    sudo systemctl start afirgen
echo.
echo 5. Verify:
echo    curl http://localhost:8000/health
echo.
echo See QUICK-START-DEPLOYMENT.md for details
echo.

endlocal
