# EC2 Deployment Guide

This guide walks you through deploying the AFIRGen backend to EC2 (98.86.30.145) after successful local testing.

## Prerequisites

Before deploying to EC2:
- ✓ All local tests passed (Task 16 complete)
- ✓ All changes committed to git
- ✓ SSH access to EC2 instance (98.86.30.145)
- ✓ EC2 security group allows inbound traffic on port 8000
- ✓ AWS credentials configured on EC2 instance

## Task 17.1: Commit and Push Changes to Git

### 1. Check Git Status

```bash
cd "AFIRGEN FINAL/main backend"
git status
```

### 2. Add All Changes

```bash
git add .
```

### 3. Commit Changes

```bash
git commit -m "Backend cleanup for AWS deployment - Tasks 1-15 complete"
```

### 4. Push to Remote Repository

```bash
git push origin main
```

### 5. Verify All Files Are Committed

Ensure these critical files are in the repository:
- `agentv5.py` (main application)
- `requirements.txt` (dependencies)
- `.env.example` (environment template)
- `README.md` (documentation)
- `ipc_sections.json` (IPC sections data)
- `afirgen.service` (systemd service file)
- All test files

**Note:** Do NOT commit `.env` file with actual credentials!

## Task 17.2: Deploy to EC2 via Git Clone

### 1. SSH into EC2 Instance

```bash
ssh -i your-key.pem ubuntu@98.86.30.145
```

Or if using password authentication:
```bash
ssh ubuntu@98.86.30.145
```

### 2. Navigate to Deployment Directory

```bash
cd /opt/afirgen
```

Or create a new directory:
```bash
sudo mkdir -p /opt/afirgen
sudo chown ubuntu:ubuntu /opt/afirgen
cd /opt/afirgen
```

### 3. Clone or Pull Latest Code

If first deployment:
```bash
git clone https://github.com/your-username/afirgen-backend.git .
```

If updating existing deployment:
```bash
git pull origin main
```

### 4. Create Virtual Environment

```bash
python3 -m venv venv
```

### 5. Activate Virtual Environment

```bash
source venv/bin/activate
```

### 6. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Task 17.3: Configure EC2 Environment

### 1. Create .env File

```bash
nano .env
```

Add the following configuration:

```env
# AWS Configuration
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-production-s3-bucket
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Database Configuration
DB_HOST=afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com
DB_PORT=3306
DB_USER=admin
DB_PASSWORD=Prathiush12.
DB_NAME=afirgen

# API Configuration
API_KEY=your-production-api-key

# Optional Configuration
RATE_LIMIT_PER_MINUTE=100
REQUEST_TIMEOUT=60
MAX_FILE_SIZE_MB=10
```

Save and exit (Ctrl+X, Y, Enter).

### 2. Verify Environment Variables

```bash
cat .env
```

Ensure all required variables are set correctly.

### 3. Set Proper File Permissions

```bash
chmod 600 .env  # Restrict access to .env file
chmod +x venv/bin/activate
```

### 4. Create Logs Directory

```bash
mkdir -p logs
```

## Task 17.4: Initialize EC2 Database

### 1. Test Database Connection

```bash
python3 -c "
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    print('✓ MySQL RDS connection successful!')
    conn.close()
except Exception as e:
    print(f'✗ MySQL RDS connection failed: {e}')
"
```

### 2. Initialize Database Tables

Start the backend once to create tables:

```bash
python3 -c "
from agentv5 import app
import uvicorn
import signal
import sys

def signal_handler(sig, frame):
    print('Stopping...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

print('Starting backend to initialize database...')
uvicorn.run(app, host='0.0.0.0', port=8000)
"
```

Wait for startup messages, then press Ctrl+C to stop.

### 3. Verify Tables Created

Connect to MySQL and verify:

```bash
mysql -h afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com \
      -u admin -p afirgen
```

Run these queries:
```sql
SHOW TABLES;
DESCRIBE fir_records;
DESCRIBE ipc_sections;
SELECT COUNT(*) FROM ipc_sections;
```

### 4. Verify SQLite Database

```bash
ls -la sessions.db
sqlite3 sessions.db "SELECT name FROM sqlite_master WHERE type='table';"
```

### 5. Verify IPC Sections Loaded

```bash
mysql -h afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com \
      -u admin -p afirgen \
      -e "SELECT COUNT(*) as total_sections FROM ipc_sections;"
```

Should show the number of IPC sections loaded from `ipc_sections.json`.

## Task 17.5: Start Backend Service on EC2

### Option A: Run with Uvicorn (Development/Testing)

```bash
# Activate virtual environment
source venv/bin/activate

# Start backend
uvicorn agentv5:app --host 0.0.0.0 --port 8000
```

Keep this terminal open. The backend will run in the foreground.

### Option B: Run with Systemd (Production)

#### 1. Copy Systemd Service File

```bash
sudo cp afirgen.service /etc/systemd/system/
```

#### 2. Edit Service File (if needed)

```bash
sudo nano /etc/systemd/system/afirgen.service
```

Ensure paths are correct:
```ini
[Unit]
Description=AFIRGen Backend Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/afirgen
Environment="PATH=/opt/afirgen/venv/bin"
EnvironmentFile=/opt/afirgen/.env
ExecStart=/opt/afirgen/venv/bin/uvicorn agentv5:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 3. Reload Systemd

```bash
sudo systemctl daemon-reload
```

#### 4. Enable Service (Start on Boot)

```bash
sudo systemctl enable afirgen
```

#### 5. Start Service

```bash
sudo systemctl start afirgen
```

#### 6. Check Service Status

```bash
sudo systemctl status afirgen
```

Should show "active (running)".

#### 7. View Service Logs

```bash
sudo journalctl -u afirgen -f
```

Press Ctrl+C to stop viewing logs.

### Verify Health Check

From EC2 instance:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "aws_bedrock": "ok"
  },
  "timestamp": "2024-03-04T12:00:00Z"
}
```

## Task 17.6: Test EC2 Deployment

### 1. Test Health Check from External

From your local machine:
```bash
curl http://98.86.30.145:8000/health
```

### 2. Test FIR Generation from External

```bash
curl -X POST http://98.86.30.145:8000/process \
  -H "X-API-Key: your-production-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "input_type": "text",
    "text": "I want to report a theft. Someone stole my laptop.",
    "language": "en-IN"
  }'
```

### 3. Verify AWS Services Accessible

Check logs for AWS service calls:
```bash
tail -f logs/main_backend.log
```

Or with systemd:
```bash
sudo journalctl -u afirgen -f
```

Look for:
- Bedrock API calls
- S3 uploads
- Database operations

### 4. Test All Endpoints

Use the test script from local testing, but change the API_BASE:
```python
API_BASE = "http://98.86.30.145:8000"
```

## Task 17.7: Configure Frontend for EC2

### 1. Switch Frontend to EC2 Configuration

On your local machine:
```bash
cd "AFIRGEN FINAL/frontend"
./deploy-to-ec2.sh
```

Or manually edit `js/config.js`:
```javascript
window.ENV = {
  API_BASE_URL: 'http://98.86.30.145:8000',
  API_KEY: 'your-production-api-key',
  ENVIRONMENT: 'production',
  ENABLE_DEBUG: false
};
```

### 2. Test Frontend with EC2 Backend

Open `index.html` in your browser and test:
- Text input FIR generation
- File uploads
- Session polling
- FIR retrieval
- PDF generation

### 3. Use Connectivity Test Page

Open `test-backend-connectivity.html`:
- Click "Use EC2 (98.86.30.145)"
- Click "Test /health Endpoint"
- Click "Test All Endpoints"

### 4. Verify End-to-End Workflow

Complete a full FIR generation workflow:
1. Submit complaint text
2. Wait for processing
3. View generated FIR
4. Generate PDF
5. Download PDF

## Task 17.8: Monitor EC2 Deployment

### 1. Monitor Application Logs

```bash
tail -f logs/main_backend.log
```

Or with systemd:
```bash
sudo journalctl -u afirgen -f
```

### 2. Monitor System Resources

```bash
# CPU and memory usage
top

# Disk usage
df -h

# Network connections
netstat -tulpn | grep 8000
```

### 3. Check for Errors

```bash
# Check for errors in logs
grep -i error logs/main_backend.log

# Check for failed requests
grep -i "status_code=500" logs/main_backend.log
```

### 4. Monitor FIR Generation Success Rate

```bash
# Count successful FIR generations
grep -c "FIR generation completed" logs/main_backend.log

# Count failed FIR generations
grep -c "FIR generation failed" logs/main_backend.log
```

### 5. Set Up Log Rotation (Optional)

Create logrotate configuration:
```bash
sudo nano /etc/logrotate.d/afirgen
```

Add:
```
/opt/afirgen/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ubuntu ubuntu
}
```

## Troubleshooting

### Issue: Service Won't Start

**Check logs:**
```bash
sudo journalctl -u afirgen -n 50
```

**Common causes:**
- Missing dependencies: `pip install -r requirements.txt`
- Wrong Python path in service file
- Missing .env file
- Database connection issues

### Issue: Health Check Returns "unhealthy"

**Check:**
- Database connection
- AWS credentials
- Bedrock access
- Logs for specific errors

### Issue: Port 8000 Not Accessible Externally

**Check EC2 security group:**
- Inbound rule for port 8000
- Source: 0.0.0.0/0 (or your IP)
- Protocol: TCP

**Check firewall:**
```bash
sudo ufw status
sudo ufw allow 8000/tcp
```

### Issue: High Memory Usage

**Check memory:**
```bash
free -h
```

**Restart service:**
```bash
sudo systemctl restart afirgen
```

**Consider upgrading EC2 instance type if needed.**

### Issue: Database Connection Timeout

**Check RDS security group:**
- Inbound rule for port 3306
- Source: EC2 security group or EC2 IP

**Test connection:**
```bash
telnet afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com 3306
```

## Rollback Procedure

If deployment fails:

### 1. Stop Service

```bash
sudo systemctl stop afirgen
```

### 2. Revert to Previous Version

```bash
git log  # Find previous commit
git checkout <previous-commit-hash>
```

### 3. Reinstall Dependencies

```bash
pip install -r requirements.txt
```

### 4. Restart Service

```bash
sudo systemctl start afirgen
```

## Post-Deployment Checklist

- [ ] Backend service running on EC2
- [ ] Health check responds correctly
- [ ] All AWS services accessible
- [ ] Database connection working
- [ ] FIR generation workflow works
- [ ] PDF generation works
- [ ] Frontend connected to EC2 backend
- [ ] End-to-end workflow tested
- [ ] Logs are being written
- [ ] No errors in logs
- [ ] Service starts on boot (systemd enabled)

## Next Steps

After successful EC2 deployment:
1. Complete Task 18 (Final checkpoint)
2. Monitor production usage
3. Set up automated backups
4. Configure CloudWatch monitoring (optional)
5. Set up SSL/TLS with domain name (optional)

## Additional Resources

- Backend README: `README.md`
- Local Testing Guide: `LOCAL-TESTING-GUIDE.md`
- Frontend Configuration: `../frontend/FRONTEND-CONFIGURATION-GUIDE.md`
- AWS EC2 Documentation: https://docs.aws.amazon.com/ec2/
