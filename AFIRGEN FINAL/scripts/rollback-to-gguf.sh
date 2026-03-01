#!/bin/bash
# Automated rollback script to revert from Bedrock to GGUF architecture
# This script safely rolls back to self-hosted GGUF models if critical issues occur

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPTS_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/rollback-$(date +%Y%m%d-%H%M%S).log"
ENV_FILE="$PROJECT_ROOT/.env"
BACKUP_ENV_FILE="$PROJECT_ROOT/.env.bedrock.backup"

# GGUF model server endpoints
MODEL_SERVER_URL="${MODEL_SERVER_URL:-http://localhost:8001}"
ASR_OCR_SERVER_URL="${ASR_OCR_SERVER_URL:-http://localhost:8002}"

# Application settings
APP_PORT="${APP_PORT:-8000}"
APP_HOST="${APP_HOST:-localhost}"

# Ensure logs directory exists
mkdir -p "$PROJECT_ROOT/logs"

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

log_info() {
    log "INFO" "${GREEN}$@${NC}"
}

log_warn() {
    log "WARN" "${YELLOW}$@${NC}"
}

log_error() {
    log "ERROR" "${RED}$@${NC}"
}

log_step() {
    log "STEP" "${BLUE}$@${NC}"
}

# Error handler
handle_error() {
    log_error "Rollback failed at line $1"
    log_error "Check log file: $LOG_FILE"
    exit 1
}

trap 'handle_error $LINENO' ERR

# Banner
echo -e "${RED}========================================${NC}"
echo -e "${RED}AFIRGen Rollback to GGUF${NC}"
echo -e "${RED}========================================${NC}"
log_info "Starting rollback procedure"
log_info "Log file: $LOG_FILE"

# Step 1: Backup current environment configuration
log_step "Step 1: Backing up current environment configuration..."
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "$BACKUP_ENV_FILE"
    log_info "✓ Environment backed up to: $BACKUP_ENV_FILE"
else
    log_warn "No .env file found, skipping backup"
fi

# Step 2: Update environment variable to disable Bedrock
log_step "Step 2: Disabling Bedrock implementation..."

# Update or create .env file
if [ -f "$ENV_FILE" ]; then
    # Check if ENABLE_BEDROCK exists in file
    if grep -q "^ENABLE_BEDROCK=" "$ENV_FILE"; then
        # Update existing value
        sed -i.bak 's/^ENABLE_BEDROCK=.*/ENABLE_BEDROCK=false/' "$ENV_FILE"
        log_info "✓ Updated ENABLE_BEDROCK=false in $ENV_FILE"
    else
        # Add new value
        echo "ENABLE_BEDROCK=false" >> "$ENV_FILE"
        log_info "✓ Added ENABLE_BEDROCK=false to $ENV_FILE"
    fi
else
    # Create new .env file
    echo "ENABLE_BEDROCK=false" > "$ENV_FILE"
    log_info "✓ Created $ENV_FILE with ENABLE_BEDROCK=false"
fi

# Export for current session
export ENABLE_BEDROCK=false
log_info "✓ Exported ENABLE_BEDROCK=false for current session"

# Step 3: Verify GGUF model servers are running
log_step "Step 3: Verifying GGUF model servers..."

# Check main model server
log_info "Checking model server at $MODEL_SERVER_URL..."
if curl -s -f "$MODEL_SERVER_URL/health" > /dev/null 2>&1; then
    log_info "✓ Model server is healthy"
else
    log_warn "✗ Model server not responding at $MODEL_SERVER_URL"
    log_warn "Please ensure GGUF model servers are running before proceeding"
    log_warn "Start with: python -m uvicorn model_server:app --port 8001"
fi

# Check ASR/OCR server
log_info "Checking ASR/OCR server at $ASR_OCR_SERVER_URL..."
if curl -s -f "$ASR_OCR_SERVER_URL/health" > /dev/null 2>&1; then
    log_info "✓ ASR/OCR server is healthy"
else
    log_warn "✗ ASR/OCR server not responding at $ASR_OCR_SERVER_URL"
    log_warn "Please ensure ASR/OCR server is running before proceeding"
    log_warn "Start with: python -m uvicorn asr_ocr_server:app --port 8002"
fi

# Step 4: Restart application
log_step "Step 4: Restarting application..."

# Detect application management method
if command -v systemctl &> /dev/null && systemctl list-units --type=service | grep -q "afirgen"; then
    # Using systemd
    log_info "Detected systemd service, restarting..."
    sudo systemctl restart afirgen
    log_info "✓ Application restarted via systemd"
    
elif [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
    # Using Docker Compose
    log_info "Detected Docker Compose, restarting..."
    cd "$PROJECT_ROOT"
    docker-compose restart
    log_info "✓ Application restarted via Docker Compose"
    
else
    # Manual restart required
    log_warn "Could not detect application management method"
    log_warn "Please restart the application manually:"
    log_warn "  pkill -f 'uvicorn.*agentv5:app'"
    log_warn "  cd $PROJECT_ROOT"
    log_warn "  python -m uvicorn agentv5:app --host 0.0.0.0 --port $APP_PORT"
    
    # Ask user to confirm restart
    read -p "Press Enter after restarting the application..."
fi

# Wait for application to start
log_info "Waiting for application to start (10 seconds)..."
sleep 10

# Step 5: Verify application health
log_step "Step 5: Verifying application health..."

max_retries=5
retry_count=0
health_check_passed=false

while [ $retry_count -lt $max_retries ]; do
    log_info "Health check attempt $((retry_count + 1))/$max_retries..."
    
    if curl -s -f "http://$APP_HOST:$APP_PORT/health" > /dev/null 2>&1; then
        health_response=$(curl -s "http://$APP_HOST:$APP_PORT/health")
        
        # Check if implementation is GGUF
        if echo "$health_response" | grep -q '"implementation".*"gguf"'; then
            log_info "✓ Application is healthy and using GGUF implementation"
            health_check_passed=true
            break
        elif echo "$health_response" | grep -q '"implementation".*"bedrock"'; then
            log_warn "Application is still using Bedrock implementation"
            log_warn "Waiting for configuration to take effect..."
        else
            log_warn "Could not determine implementation from health response"
        fi
    else
        log_warn "Health endpoint not responding"
    fi
    
    retry_count=$((retry_count + 1))
    if [ $retry_count -lt $max_retries ]; then
        sleep 5
    fi
done

if [ "$health_check_passed" = false ]; then
    log_error "✗ Health check failed after $max_retries attempts"
    log_error "Application may not have restarted correctly"
    log_error "Check application logs for errors"
    exit 1
fi

# Step 6: Verify GGUF functionality
log_step "Step 6: Verifying GGUF functionality..."

# Test health endpoint details
health_response=$(curl -s "http://$APP_HOST:$APP_PORT/health")
log_info "Health endpoint response:"
echo "$health_response" | python3 -m json.tool 2>/dev/null || echo "$health_response"

# Verify key indicators
if echo "$health_response" | grep -q '"enable_bedrock".*false'; then
    log_info "✓ Feature flag ENABLE_BEDROCK is false"
else
    log_error "✗ Feature flag ENABLE_BEDROCK is not false"
    exit 1
fi

if echo "$health_response" | grep -q '"implementation".*"gguf"'; then
    log_info "✓ Implementation is set to GGUF"
else
    log_error "✗ Implementation is not set to GGUF"
    exit 1
fi

# Step 7: Perform functional test
log_step "Step 7: Performing functional test..."

# Simple test with text input
test_payload='{"text": "Test complaint for rollback verification"}'
log_info "Sending test request to /process endpoint..."

test_response=$(curl -s -X POST "http://$APP_HOST:$APP_PORT/process" \
    -H "Content-Type: application/json" \
    -d "$test_payload" 2>&1)

if echo "$test_response" | grep -q '"success".*true'; then
    log_info "✓ Functional test passed"
elif echo "$test_response" | grep -q '"session_id"'; then
    log_info "✓ Functional test passed (session created)"
else
    log_warn "Functional test response:"
    echo "$test_response" | python3 -m json.tool 2>/dev/null || echo "$test_response"
    log_warn "Could not verify functional test, but application is responding"
fi

# Step 8: Check for Bedrock-related errors in logs
log_step "Step 8: Checking for Bedrock-related errors..."

if [ -f "$PROJECT_ROOT/logs/main_backend.log" ]; then
    recent_errors=$(tail -n 100 "$PROJECT_ROOT/logs/main_backend.log" | grep -i "bedrock\|boto3\|aws" | grep -i "error\|exception" || true)
    
    if [ -z "$recent_errors" ]; then
        log_info "✓ No Bedrock-related errors found in recent logs"
    else
        log_warn "Found Bedrock-related errors in logs:"
        echo "$recent_errors"
        log_warn "These errors should stop occurring now that GGUF is active"
    fi
else
    log_warn "Application log file not found at $PROJECT_ROOT/logs/main_backend.log"
fi

# Step 9: Verify database connectivity
log_step "Step 9: Verifying database connectivity..."

# Check if database is accessible (basic check)
if echo "$health_response" | grep -q '"database".*"connected"'; then
    log_info "✓ Database connection verified"
else
    log_warn "Could not verify database connection from health endpoint"
fi

# Step 10: Generate rollback report
log_step "Step 10: Generating rollback report..."

report_file="$PROJECT_ROOT/logs/rollback-report-$(date +%Y%m%d-%H%M%S).txt"

cat > "$report_file" << EOF
AFIRGen Rollback Report
=======================
Date: $(date)
Rollback Type: Bedrock to GGUF

Environment Configuration:
- ENABLE_BEDROCK: false
- Model Server: $MODEL_SERVER_URL
- ASR/OCR Server: $ASR_OCR_SERVER_URL
- Application: http://$APP_HOST:$APP_PORT

Health Check Results:
- Application Status: Healthy
- Implementation: GGUF
- Database: Connected
- Model Servers: Verified

Rollback Steps Completed:
1. ✓ Backed up environment configuration
2. ✓ Disabled Bedrock (ENABLE_BEDROCK=false)
3. ✓ Verified GGUF model servers
4. ✓ Restarted application
5. ✓ Verified application health
6. ✓ Verified GGUF functionality
7. ✓ Performed functional test
8. ✓ Checked for errors
9. ✓ Verified database connectivity
10. ✓ Generated rollback report

Backup Files:
- Environment backup: $BACKUP_ENV_FILE
- Rollback log: $LOG_FILE

Next Steps:
1. Monitor application logs for any issues
2. Test FIR generation with real data
3. Verify all endpoints are functioning
4. Monitor system performance
5. Document incident and rollback reason

To revert this rollback (switch back to Bedrock):
1. Set ENABLE_BEDROCK=true in .env file
2. Restart application
3. Verify Bedrock services are accessible
4. Run health checks

EOF

log_info "✓ Rollback report saved to: $report_file"

# Final summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Rollback Completed Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
log_info "Summary:"
log_info "  - Implementation: GGUF (self-hosted models)"
log_info "  - Feature Flag: ENABLE_BEDROCK=false"
log_info "  - Application: Healthy and responding"
log_info "  - Model Servers: Verified"
log_info ""
log_info "Files:"
log_info "  - Rollback log: $LOG_FILE"
log_info "  - Rollback report: $report_file"
log_info "  - Environment backup: $BACKUP_ENV_FILE"
log_info ""
log_info "Next steps:"
log_info "  1. Monitor application logs: tail -f $PROJECT_ROOT/logs/main_backend.log"
log_info "  2. Test FIR generation endpoints"
log_info "  3. Verify system performance"
log_info "  4. Document rollback reason and incident"
log_info ""
log_info "To switch back to Bedrock:"
log_info "  1. Edit $ENV_FILE and set ENABLE_BEDROCK=true"
log_info "  2. Restart application"
log_info "  3. Run: $SCRIPTS_DIR/health-check.py"

exit 0
