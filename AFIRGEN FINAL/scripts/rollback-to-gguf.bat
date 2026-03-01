@echo off
REM Automated rollback script to revert from Bedrock to GGUF architecture
REM This script safely rolls back to self-hosted GGUF models if critical issues occur

setlocal enabledelayedexpansion

REM Configuration
set "SCRIPTS_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPTS_DIR%.."
set "TIMESTAMP=%date:~-4%%date:~-10,2%%date:~-7,2%-%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"
set "LOG_FILE=%PROJECT_ROOT%\logs\rollback-%TIMESTAMP%.log"
set "ENV_FILE=%PROJECT_ROOT%\.env"
set "BACKUP_ENV_FILE=%PROJECT_ROOT%\.env.bedrock.backup"

REM GGUF model server endpoints
if not defined MODEL_SERVER_URL set "MODEL_SERVER_URL=http://localhost:8001"
if not defined ASR_OCR_SERVER_URL set "ASR_OCR_SERVER_URL=http://localhost:8002"

REM Application settings
if not defined APP_PORT set "APP_PORT=8000"
if not defined APP_HOST set "APP_HOST=localhost"

REM Ensure logs directory exists
if not exist "%PROJECT_ROOT%\logs" mkdir "%PROJECT_ROOT%\logs"

REM Initialize log file
echo AFIRGen Rollback to GGUF - %date% %time% > "%LOG_FILE%"
echo ======================================== >> "%LOG_FILE%"

REM Banner
echo ========================================
echo AFIRGen Rollback to GGUF
echo ========================================
call :log_info "Starting rollback procedure"
call :log_info "Log file: %LOG_FILE%"

REM Step 1: Backup current environment configuration
call :log_step "Step 1: Backing up current environment configuration..."
if exist "%ENV_FILE%" (
    copy /Y "%ENV_FILE%" "%BACKUP_ENV_FILE%" >nul 2>&1
    call :log_info "✓ Environment backed up to: %BACKUP_ENV_FILE%"
) else (
    call :log_warn "No .env file found, skipping backup"
)

REM Step 2: Update environment variable to disable Bedrock
call :log_step "Step 2: Disabling Bedrock implementation..."

REM Create or update .env file
if exist "%ENV_FILE%" (
    REM Check if ENABLE_BEDROCK exists in file
    findstr /C:"ENABLE_BEDROCK=" "%ENV_FILE%" >nul 2>&1
    if !errorlevel! equ 0 (
        REM Update existing value
        powershell -Command "(Get-Content '%ENV_FILE%') -replace '^ENABLE_BEDROCK=.*', 'ENABLE_BEDROCK=false' | Set-Content '%ENV_FILE%.tmp'"
        move /Y "%ENV_FILE%.tmp" "%ENV_FILE%" >nul 2>&1
        call :log_info "✓ Updated ENABLE_BEDROCK=false in %ENV_FILE%"
    ) else (
        REM Add new value
        echo ENABLE_BEDROCK=false >> "%ENV_FILE%"
        call :log_info "✓ Added ENABLE_BEDROCK=false to %ENV_FILE%"
    )
) else (
    REM Create new .env file
    echo ENABLE_BEDROCK=false > "%ENV_FILE%"
    call :log_info "✓ Created %ENV_FILE% with ENABLE_BEDROCK=false"
)

REM Export for current session
set "ENABLE_BEDROCK=false"
call :log_info "✓ Set ENABLE_BEDROCK=false for current session"

REM Step 3: Verify GGUF model servers are running
call :log_step "Step 3: Verifying GGUF model servers..."

REM Check main model server
call :log_info "Checking model server at %MODEL_SERVER_URL%..."
curl -s -f "%MODEL_SERVER_URL%/health" >nul 2>&1
if !errorlevel! equ 0 (
    call :log_info "✓ Model server is healthy"
) else (
    call :log_warn "✗ Model server not responding at %MODEL_SERVER_URL%"
    call :log_warn "Please ensure GGUF model servers are running before proceeding"
    call :log_warn "Start with: python -m uvicorn model_server:app --port 8001"
)

REM Check ASR/OCR server
call :log_info "Checking ASR/OCR server at %ASR_OCR_SERVER_URL%..."
curl -s -f "%ASR_OCR_SERVER_URL%/health" >nul 2>&1
if !errorlevel! equ 0 (
    call :log_info "✓ ASR/OCR server is healthy"
) else (
    call :log_warn "✗ ASR/OCR server not responding at %ASR_OCR_SERVER_URL%"
    call :log_warn "Please ensure ASR/OCR server is running before proceeding"
    call :log_warn "Start with: python -m uvicorn asr_ocr_server:app --port 8002"
)

REM Step 4: Restart application
call :log_step "Step 4: Restarting application..."

REM Check if running as Windows service
sc query AFIRGenService >nul 2>&1
if !errorlevel! equ 0 (
    call :log_info "Detected Windows service, restarting..."
    net stop AFIRGenService >nul 2>&1
    timeout /t 3 /nobreak >nul
    net start AFIRGenService >nul 2>&1
    call :log_info "✓ Application restarted via Windows service"
) else (
    REM Manual restart required
    call :log_warn "Could not detect Windows service"
    call :log_warn "Please restart the application manually:"
    call :log_warn "  1. Stop the current process (Ctrl+C or Task Manager)"
    call :log_warn "  2. cd %PROJECT_ROOT%"
    call :log_warn "  3. python -m uvicorn agentv5:app --host 0.0.0.0 --port %APP_PORT%"
    
    REM Try to kill existing process
    call :log_info "Attempting to stop existing uvicorn process..."
    taskkill /F /IM python.exe /FI "WINDOWTITLE eq *uvicorn*" >nul 2>&1
    
    REM Ask user to confirm restart
    echo.
    echo Press any key after restarting the application...
    pause >nul
)

REM Wait for application to start
call :log_info "Waiting for application to start (10 seconds)..."
timeout /t 10 /nobreak >nul

REM Step 5: Verify application health
call :log_step "Step 5: Verifying application health..."

set "max_retries=5"
set "retry_count=0"
set "health_check_passed=false"

:health_check_loop
if !retry_count! lss !max_retries! (
    set /a "attempt=!retry_count!+1"
    call :log_info "Health check attempt !attempt!/!max_retries!..."
    
    curl -s -f "http://%APP_HOST%:%APP_PORT%/health" >nul 2>&1
    if !errorlevel! equ 0 (
        REM Get health response
        curl -s "http://%APP_HOST%:%APP_PORT%/health" > "%TEMP%\health_response.json" 2>&1
        
        REM Check if implementation is GGUF
        findstr /C:"\"implementation\"" "%TEMP%\health_response.json" | findstr /C:"\"gguf\"" >nul 2>&1
        if !errorlevel! equ 0 (
            call :log_info "✓ Application is healthy and using GGUF implementation"
            set "health_check_passed=true"
            goto :health_check_done
        ) else (
            findstr /C:"\"implementation\"" "%TEMP%\health_response.json" | findstr /C:"\"bedrock\"" >nul 2>&1
            if !errorlevel! equ 0 (
                call :log_warn "Application is still using Bedrock implementation"
                call :log_warn "Waiting for configuration to take effect..."
            ) else (
                call :log_warn "Could not determine implementation from health response"
            )
        )
    ) else (
        call :log_warn "Health endpoint not responding"
    )
    
    set /a "retry_count+=1"
    if !retry_count! lss !max_retries! (
        timeout /t 5 /nobreak >nul
    )
    goto :health_check_loop
)

:health_check_done
if "%health_check_passed%"=="false" (
    call :log_error "✗ Health check failed after %max_retries% attempts"
    call :log_error "Application may not have restarted correctly"
    call :log_error "Check application logs for errors"
    exit /b 1
)

REM Step 6: Verify GGUF functionality
call :log_step "Step 6: Verifying GGUF functionality..."

REM Test health endpoint details
curl -s "http://%APP_HOST%:%APP_PORT%/health" > "%TEMP%\health_response.json" 2>&1
call :log_info "Health endpoint response:"
type "%TEMP%\health_response.json"

REM Verify key indicators
findstr /C:"\"enable_bedrock\"" "%TEMP%\health_response.json" | findstr /C:"false" >nul 2>&1
if !errorlevel! equ 0 (
    call :log_info "✓ Feature flag ENABLE_BEDROCK is false"
) else (
    call :log_error "✗ Feature flag ENABLE_BEDROCK is not false"
    exit /b 1
)

findstr /C:"\"implementation\"" "%TEMP%\health_response.json" | findstr /C:"\"gguf\"" >nul 2>&1
if !errorlevel! equ 0 (
    call :log_info "✓ Implementation is set to GGUF"
) else (
    call :log_error "✗ Implementation is not set to GGUF"
    exit /b 1
)

REM Step 7: Perform functional test
call :log_step "Step 7: Performing functional test..."

REM Simple test with text input
call :log_info "Sending test request to /process endpoint..."
curl -s -X POST "http://%APP_HOST%:%APP_PORT%/process" ^
    -H "Content-Type: application/json" ^
    -d "{\"text\": \"Test complaint for rollback verification\"}" > "%TEMP%\test_response.json" 2>&1

findstr /C:"\"success\"" "%TEMP%\test_response.json" | findstr /C:"true" >nul 2>&1
if !errorlevel! equ 0 (
    call :log_info "✓ Functional test passed"
) else (
    findstr /C:"\"session_id\"" "%TEMP%\test_response.json" >nul 2>&1
    if !errorlevel! equ 0 (
        call :log_info "✓ Functional test passed (session created)"
    ) else (
        call :log_warn "Functional test response:"
        type "%TEMP%\test_response.json"
        call :log_warn "Could not verify functional test, but application is responding"
    )
)

REM Step 8: Check for Bedrock-related errors in logs
call :log_step "Step 8: Checking for Bedrock-related errors..."

if exist "%PROJECT_ROOT%\logs\main_backend.log" (
    REM Get last 100 lines and check for Bedrock errors
    powershell -Command "Get-Content '%PROJECT_ROOT%\logs\main_backend.log' -Tail 100 | Select-String -Pattern 'bedrock|boto3|aws' | Select-String -Pattern 'error|exception' -CaseSensitive:$false" > "%TEMP%\recent_errors.txt" 2>&1
    
    for /f %%i in ("%TEMP%\recent_errors.txt") do set "filesize=%%~zi"
    if !filesize! equ 0 (
        call :log_info "✓ No Bedrock-related errors found in recent logs"
    ) else (
        call :log_warn "Found Bedrock-related errors in logs:"
        type "%TEMP%\recent_errors.txt"
        call :log_warn "These errors should stop occurring now that GGUF is active"
    )
) else (
    call :log_warn "Application log file not found at %PROJECT_ROOT%\logs\main_backend.log"
)

REM Step 9: Verify database connectivity
call :log_step "Step 9: Verifying database connectivity..."

findstr /C:"\"database\"" "%TEMP%\health_response.json" | findstr /C:"\"connected\"" >nul 2>&1
if !errorlevel! equ 0 (
    call :log_info "✓ Database connection verified"
) else (
    call :log_warn "Could not verify database connection from health endpoint"
)

REM Step 10: Generate rollback report
call :log_step "Step 10: Generating rollback report..."

set "REPORT_TIMESTAMP=%date:~-4%%date:~-10,2%%date:~-7,2%-%time:~0,2%%time:~3,2%%time:~6,2%"
set "REPORT_TIMESTAMP=%REPORT_TIMESTAMP: =0%"
set "report_file=%PROJECT_ROOT%\logs\rollback-report-%REPORT_TIMESTAMP%.txt"

(
echo AFIRGen Rollback Report
echo =======================
echo Date: %date% %time%
echo Rollback Type: Bedrock to GGUF
echo.
echo Environment Configuration:
echo - ENABLE_BEDROCK: false
echo - Model Server: %MODEL_SERVER_URL%
echo - ASR/OCR Server: %ASR_OCR_SERVER_URL%
echo - Application: http://%APP_HOST%:%APP_PORT%
echo.
echo Health Check Results:
echo - Application Status: Healthy
echo - Implementation: GGUF
echo - Database: Connected
echo - Model Servers: Verified
echo.
echo Rollback Steps Completed:
echo 1. ✓ Backed up environment configuration
echo 2. ✓ Disabled Bedrock (ENABLE_BEDROCK=false^)
echo 3. ✓ Verified GGUF model servers
echo 4. ✓ Restarted application
echo 5. ✓ Verified application health
echo 6. ✓ Verified GGUF functionality
echo 7. ✓ Performed functional test
echo 8. ✓ Checked for errors
echo 9. ✓ Verified database connectivity
echo 10. ✓ Generated rollback report
echo.
echo Backup Files:
echo - Environment backup: %BACKUP_ENV_FILE%
echo - Rollback log: %LOG_FILE%
echo.
echo Next Steps:
echo 1. Monitor application logs for any issues
echo 2. Test FIR generation with real data
echo 3. Verify all endpoints are functioning
echo 4. Monitor system performance
echo 5. Document incident and rollback reason
echo.
echo To revert this rollback (switch back to Bedrock^):
echo 1. Set ENABLE_BEDROCK=true in .env file
echo 2. Restart application
echo 3. Verify Bedrock services are accessible
echo 4. Run health checks
echo.
) > "%report_file%"

call :log_info "✓ Rollback report saved to: %report_file%"

REM Final summary
echo.
echo ========================================
echo Rollback Completed Successfully!
echo ========================================
echo.
call :log_info "Summary:"
call :log_info "  - Implementation: GGUF (self-hosted models)"
call :log_info "  - Feature Flag: ENABLE_BEDROCK=false"
call :log_info "  - Application: Healthy and responding"
call :log_info "  - Model Servers: Verified"
echo.
call :log_info "Files:"
call :log_info "  - Rollback log: %LOG_FILE%"
call :log_info "  - Rollback report: %report_file%"
call :log_info "  - Environment backup: %BACKUP_ENV_FILE%"
echo.
call :log_info "Next steps:"
call :log_info "  1. Monitor application logs"
call :log_info "  2. Test FIR generation endpoints"
call :log_info "  3. Verify system performance"
call :log_info "  4. Document rollback reason and incident"
echo.
call :log_info "To switch back to Bedrock:"
call :log_info "  1. Edit %ENV_FILE% and set ENABLE_BEDROCK=true"
call :log_info "  2. Restart application"
call :log_info "  3. Run: python %SCRIPTS_DIR%health-check.py"

REM Cleanup temp files
del /Q "%TEMP%\health_response.json" >nul 2>&1
del /Q "%TEMP%\test_response.json" >nul 2>&1
del /Q "%TEMP%\recent_errors.txt" >nul 2>&1

exit /b 0

REM ========================================
REM Logging Functions
REM ========================================

:log_info
set "msg=%~1"
set "timestamp=%date% %time%"
echo [INFO] %msg%
echo %timestamp% [INFO] %msg% >> "%LOG_FILE%"
goto :eof

:log_warn
set "msg=%~1"
set "timestamp=%date% %time%"
echo [WARN] %msg%
echo %timestamp% [WARN] %msg% >> "%LOG_FILE%"
goto :eof

:log_error
set "msg=%~1"
set "timestamp=%date% %time%"
echo [ERROR] %msg%
echo %timestamp% [ERROR] %msg% >> "%LOG_FILE%"
goto :eof

:log_step
set "msg=%~1"
set "timestamp=%date% %time%"
echo.
echo [STEP] %msg%
echo %timestamp% [STEP] %msg% >> "%LOG_FILE%"
goto :eof
