# EC2 Deployment Steps (t3.medium)

## Prerequisites

- EC2 instance: **t3.medium** (NOT t2.small or t3.small)
- Instance IP: `98.86.30.145`
- SSH key file for EC2 access
- IAM role attached to EC2 with permissions for:
  - AWS Bedrock (invoke model)
  - AWS Transcribe
  - AWS Textract
  - S3 (read/write/delete)
  - RDS MySQL (via security group)

## Quick Deployment

### Step 1: SSH into EC2

```bash
ssh -i path/to/your-key.pem ubuntu@98.86.30.145
```

### Step 2: Download and Run Deployment Script

```bash
# Download the deployment script
curl -o deploy.sh https://raw.githubusercontent.com/navaneethkutty/AFIRGen-1/main/AFIRGEN%20FINAL/main%20backend/deploy-to-ec2.sh

# Make it executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

The script will:
1. Install system dependencies (Python 3.11, git, mysql-client)
2. Clone/update the repository
3. Set up Python virtual environment
4. Install Python dependencies
5. Create .env file from template
6. Test database connectivity
7. Install systemd service
8. Start the backend
9. Test health endpoint

### Step 3: Configure .env File

When prompted, edit the `.env` file:

```bash
nano /opt/afirgen-backend/AFIRGEN\ FINAL/main\ backend/.env
```

**Important Configuration:**

```env
# AWS Configuration (use IAM role, comment out credentials)
AWS_REGION=us-east-1
S3_BUCKET_NAME=afirgen-storage-bucket
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Database Configuration
DB_HOST=afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com
DB_PORT=3306
DB_USER=admin
DB_PASSWORD=Prathiush12.
DB_NAME=afirgen

# API Configuration
API_KEY=your-production-api-key-here

# Comment out these lines (EC2 uses IAM role):
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
```

Save with `Ctrl+O`, `Enter`, then exit with `Ctrl+X`.

### Step 4: Verify Deployment

```bash
# Check service status
sudo systemctl status afirgen

# View logs
sudo journalctl -u afirgen -f

# Test health endpoint (local)
curl http://localhost:8000/health

# Test health endpoint (external)
curl http://98.86.30.145:8000/health
```

## Manual Deployment (Alternative)

If you prefer manual steps:

### 1. SSH into EC2

```bash
ssh -i path/to/your-key.pem ubuntu@98.86.30.145
```

### 2. Install Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip git mysql-client
```

### 3. Clone Repository

```bash
sudo mkdir -p /opt/afirgen-backend
sudo chown $USER:$USER /opt/afirgen-backend
cd /opt/afirgen-backend
git clone https://github.com/navaneethkutty/AFIRGen-1.git .
cd "AFIRGEN FINAL/main backend"
```

### 4. Set Up Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Environment

```bash
cp .env.example .env
nano .env
# Edit with your production values
```

### 6. Test Database Connection

```bash
python3 << 'EOF'
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT', 3306)),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME')
)
print("✓ MySQL connection successful!")
conn.close()
EOF
```

### 7. Install Systemd Service

```bash
sudo cp afirgen.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable afirgen
sudo systemctl start afirgen
```

### 8. Verify

```bash
sudo systemctl status afirgen
curl http://localhost:8000/health
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u afirgen -n 50

# Check application logs
tail -f /opt/afirgen-backend/AFIRGEN\ FINAL/main\ backend/logs/main_backend.log

# Test manually
cd /opt/afirgen-backend/AFIRGEN\ FINAL/main\ backend
source venv/bin/activate
python -c "from agentv5 import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)"
```

### Database Connection Failed

```bash
# Test from EC2
mysql -h afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com -u admin -p

# Check security group allows EC2 instance
# RDS security group should allow inbound from EC2 security group
```

### Port 8000 Not Accessible Externally

```bash
# Check EC2 security group allows inbound port 8000
# Add rule: Type=Custom TCP, Port=8000, Source=0.0.0.0/0 (or your IP)
```

### IAM Role Issues

```bash
# Verify IAM role is attached to EC2
aws sts get-caller-identity

# Should show the IAM role, not "Unable to locate credentials"
```

## Service Management

```bash
# Start service
sudo systemctl start afirgen

# Stop service
sudo systemctl stop afirgen

# Restart service
sudo systemctl restart afirgen

# View status
sudo systemctl status afirgen

# View logs (follow)
sudo journalctl -u afirgen -f

# View logs (last 100 lines)
sudo journalctl -u afirgen -n 100
```

## Updating Code

```bash
cd /opt/afirgen-backend
git pull origin main
cd "AFIRGEN FINAL/main backend"
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart afirgen
```

## Performance Monitoring

```bash
# Check CPU/Memory usage
htop

# Check disk usage
df -h

# Check backend process
ps aux | grep uvicorn

# Check network connections
netstat -tulpn | grep 8000
```

## Next Steps After Deployment

1. **Test Health Endpoint:**
   ```bash
   curl http://98.86.30.145:8000/health
   ```

2. **Test FIR Generation:**
   ```bash
   curl -X POST http://98.86.30.145:8000/process \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"input_type":"text","text":"Test complaint","language":"en-IN"}'
   ```

3. **Configure Frontend:**
   - Update frontend API base URL to `http://98.86.30.145:8000`
   - Test end-to-end workflow

4. **Monitor Logs:**
   ```bash
   sudo journalctl -u afirgen -f
   ```

## Security Checklist

- [ ] EC2 security group allows only necessary ports (22, 8000)
- [ ] RDS security group allows only EC2 security group
- [ ] IAM role has minimal required permissions
- [ ] API key is strong and unique
- [ ] .env file has correct permissions (600)
- [ ] AWS credentials NOT in .env (use IAM role)
- [ ] Logs directory has correct permissions

## Instance Type Verification

Verify you're using t3.medium:

```bash
# Check instance type
curl -s http://169.254.169.254/latest/meta-data/instance-type

# Should output: t3.medium
```

If it shows t2.small or t3.small, you need to:
1. Stop the instance
2. Change instance type to t3.medium
3. Start the instance
4. Redeploy

t3.medium provides:
- 2 vCPUs
- 4 GB RAM
- Better network performance
- Required for AWS Bedrock workloads
