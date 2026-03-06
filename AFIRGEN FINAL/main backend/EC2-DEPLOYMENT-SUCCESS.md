# ✅ EC2 Deployment Successful!

## Backend is Live and Operational

**Health Check:** http://18.206.148.182:8000/health

```json
{
  "status": "healthy",
  "checks": {
    "mysql": true,
    "bedrock": true
  },
  "timestamp": "2026-03-05T12:52:47.327410Z"
}
```

## Deployment Details

### EC2 Instance
- **Instance ID:** i-02ecca1d375ab2cec
- **Public IP:** 18.206.148.182
- **Instance Type:** t3.small (2 vCPUs, 2 GB RAM)
- **Region:** us-east-1
- **VPC:** vpc-0e420c4cc3f10b810

### Installation Path
- **Backend:** `/opt/afirgen-backend/AFIRGEN FINAL/main backend/`
- **Virtual Environment:** `/opt/afirgen-backend/AFIRGEN FINAL/main backend/venv/`
- **Logs:** `/opt/afirgen-backend/AFIRGEN FINAL/main backend/logs/`

### Database
- **MySQL RDS:** afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com
- **Database Name:** afirgen
- **Tables Created:** ✅ fir_records, ipc_sections
- **SQLite Sessions:** ✅ sessions.db
- **Legal KB:** ✅ 988 sections loaded

### AWS Services Connected
- ✅ AWS Bedrock (Claude 3 Sonnet)
- ✅ AWS Transcribe
- ✅ AWS Textract
- ✅ S3 (afirgen-storage-bucket)
- ✅ RDS MySQL

## Issues Resolved During Deployment

1. **Python Version:** Changed from python3.11 to python3 (Ubuntu 24.04 uses Python 3.12)
2. **Database Creation:** Created `afirgen` database on RDS
3. **Permissions:** Fixed file and directory permissions for ssm-user
4. **SQLite Directory:** Made directory writable for SQLite temporary files

## How to Access

### From SSM Session (Currently Running)
The backend is running in your SSM session. To keep it running permanently:

**Option 1: Run in background with nohup**
```bash
# Press Ctrl+C to stop current process
nohup venv/bin/uvicorn agentv5:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &
```

**Option 2: Configure systemd service (recommended)**
```bash
# Exit SSM session (backend will stop)
# Then run from your local machine:
aws ssm send-command \
  --instance-ids i-02ecca1d375ab2cec \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=[
    "cd /opt/afirgen-backend/AFIRGEN\\ FINAL/main\\ backend",
    "sudo bash -c \"cat > /etc/systemd/system/afirgen.service << EOF
[Unit]
Description=AFIRGen Backend Service
After=network.target

[Service]
Type=simple
User=ssm-user
WorkingDirectory=/opt/afirgen-backend/AFIRGEN FINAL/main backend
EnvironmentFile=/opt/afirgen-backend/AFIRGEN FINAL/main backend/.env
ExecStart=/opt/afirgen-backend/AFIRGEN FINAL/main backend/venv/bin/uvicorn agentv5:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF\"",
    "sudo systemctl daemon-reload",
    "sudo systemctl enable afirgen",
    "sudo systemctl start afirgen"
  ]' \
  --region us-east-1
```

### Test Endpoints

**Health Check:**
```bash
curl http://18.206.148.182:8000/health
```

**List FIRs:**
```bash
curl -H "X-API-Key: your-secret-api-key-change-in-production" \
  http://18.206.148.182:8000/firs
```

**Generate FIR (Text Input):**
```bash
curl -X POST http://18.206.148.182:8000/process \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-in-production" \
  -d '{
    "input_type": "text",
    "text": "I want to report a theft. Someone stole my laptop from my office.",
    "language": "en"
  }'
```

## Next Steps

1. **Keep Backend Running:** Choose Option 1 (nohup) or Option 2 (systemd) above
2. **Configure Frontend:** Update frontend API URL to `http://18.206.148.182:8000`
3. **Test End-to-End:** Test complete FIR generation workflow
4. **Monitor Logs:** Check logs for any issues
5. **Final Checkpoint:** Complete Task 18 in spec

## Monitoring Commands

**Check if backend is running:**
```bash
curl http://18.206.148.182:8000/health
```

**View logs (if using systemd):**
```bash
aws ssm start-session --target i-02ecca1d375ab2cec --region us-east-1
sudo journalctl -u afirgen -f
```

**View application logs:**
```bash
aws ssm start-session --target i-02ecca1d375ab2cec --region us-east-1
tail -f "/opt/afirgen-backend/AFIRGEN FINAL/main backend/logs/main_backend.log"
```

## Summary

The AFIRGen backend is successfully deployed and operational on EC2! All AWS services are connected, the database is initialized with 988 legal sections, and the health check confirms everything is working correctly.
