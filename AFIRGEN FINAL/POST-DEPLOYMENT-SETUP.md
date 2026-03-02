# AFIRGen Post-Deployment Setup Guide

**Infrastructure Deployed:** ✅  
**EC2 Instance:** i-0bc18e312758fda7c  
**EC2 IP:** 98.86.30.145  
**RDS Endpoint:** afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com:3306

---

## Quick Start

Follow these steps in order to complete your deployment:

### Step 1: Connect to EC2 Instance

```bash
# Replace 'your-key.pem' with your actual SSH key file
ssh -i your-key.pem ubuntu@98.86.30.145
```

If you don't have the SSH key, retrieve it from AWS:
```bash
# List your key pairs
aws ec2 describe-key-pairs

# If you need to create a new key pair
aws ec2 create-key-pair --key-name afirgen-key --query 'KeyMaterial' --output text > afirgen-key.pem
chmod 400 afirgen-key.pem
```

---

### Step 2: Install System Dependencies

Once connected to EC2, run:

```bash
# Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.11 and pip
sudo apt-get install -y python3.11 python3.11-venv python3-pip

# Install Git
sudo apt-get install -y git

# Install MySQL client
sudo apt-get install -y mysql-client

# Install other dependencies
sudo apt-get install -y build-essential libssl-dev libffi-dev python3-dev
```

---

### Step 3: Clone Application Code

```bash
# Create application directory
sudo mkdir -p /opt/afirgen
sudo chown ubuntu:ubuntu /opt/afirgen
cd /opt/afirgen

# Clone your repository (replace with your actual repo URL)
git clone <YOUR_REPO_URL> .

# Or upload code from local machine
# From your local machine, run:
# scp -i your-key.pem -r "AFIRGEN FINAL"/* ubuntu@98.86.30.145:/opt/afirgen/
```

---

### Step 4: Set Up Python Environment

```bash
cd /opt/afirgen

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install main backend dependencies
pip install --upgrade pip
pip install -r "main backend/requirements.txt"

# Install additional dependencies if needed
pip install boto3 pymysql cryptography
```

---

### Step 5: Configure Environment Variables

```bash
# Copy environment template
cp .env.bedrock /opt/afirgen/.env

# Edit environment file with your actual values
nano /opt/afirgen/.env
```

Update these critical values in `.env`:

```bash
# MySQL Database Configuration
MYSQL_HOST=afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com
MYSQL_PORT=3306
MYSQL_USER=admin
MYSQL_PASSWORD=<YOUR_RDS_PASSWORD>  # Set during Terraform deployment
MYSQL_DB=fir_db

# Application Configuration
PORT=8000
FIR_AUTH_KEY=<GENERATE_SECURE_KEY>
API_KEY=<GENERATE_SECURE_API_KEY_MIN_32_CHARS>

# AWS Configuration
AWS_REGION=us-east-1
USE_AWS_SECRETS=false  # Set to true if using Secrets Manager

# CORS Configuration (update with your domain)
CORS_ORIGINS=http://98.86.30.145:8000,http://localhost:8000

# Security
ENFORCE_HTTPS=false  # Set to true once SSL is configured
SESSION_TIMEOUT=3600
```

Generate secure keys:
```bash
# Generate FIR_AUTH_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate API_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

### Step 6: Initialize Database

```bash
# Test database connection
mysql -h afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com \
      -u admin -p \
      -e "SELECT VERSION();"

# Create database if it doesn't exist
mysql -h afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com \
      -u admin -p \
      -e "CREATE DATABASE IF NOT EXISTS fir_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Run database migrations
cd /opt/afirgen/"main backend"
source /opt/afirgen/venv/bin/activate

# If you have migration scripts
python migrations/init_db.py

# Or manually create tables (check your schema files)
mysql -h afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com \
      -u admin -p fir_db < migrations/schema.sql
```

---

### Step 7: Set Up Vector Database (Aurora pgvector)

If using Aurora PostgreSQL with pgvector:

```bash
# Install PostgreSQL client
sudo apt-get install -y postgresql-client

# Connect to Aurora (get endpoint from Terraform outputs)
# psql -h <AURORA_ENDPOINT> -U admin -d postgres

# Create vector extension
# CREATE EXTENSION IF NOT EXISTS vector;

# Run vector DB migrations
# python scripts/migrate_vector_db.py
```

---

### Step 8: Configure AWS Bedrock Access

```bash
# Ensure EC2 instance has IAM role with Bedrock permissions
# This should be configured in Terraform

# Test Bedrock access
python3 << EOF
import boto3
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
print("Bedrock client created successfully")
EOF
```

---

### Step 9: Create Systemd Service

Create a systemd service to run the application:

```bash
sudo nano /etc/systemd/system/afirgen.service
```

Add this content:

```ini
[Unit]
Description=AFIRGen FIR Generation Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/afirgen/main backend
Environment="PATH=/opt/afirgen/venv/bin"
EnvironmentFile=/opt/afirgen/.env
ExecStart=/opt/afirgen/venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable afirgen

# Start the service
sudo systemctl start afirgen

# Check status
sudo systemctl status afirgen

# View logs
sudo journalctl -u afirgen -f
```

---

### Step 10: Configure Security Groups

Ensure your EC2 security group allows:

```bash
# Check current security group rules
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=afirgen-*" \
  --query 'SecurityGroups[*].[GroupId,GroupName,IpPermissions]'

# Add rules if needed (should be in Terraform)
# Port 8000 for API
# Port 22 for SSH (your IP only)
# Port 443 for HTTPS (when configured)
```

---

### Step 11: Verify Application Health

```bash
# From EC2 instance
curl http://localhost:8000/health

# From your local machine
curl http://98.86.30.145:8000/health

# Expected response:
# {"status": "healthy", "timestamp": "..."}
```

---

### Step 12: Configure SNS Email Notifications

```bash
# List SNS topics
aws sns list-topics

# Subscribe your email to the alarm topic
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:<ACCOUNT_ID>:afirgen-prod-alarms \
  --protocol email \
  --notification-endpoint your-email@example.com

# Check your email and confirm the subscription
```

---

### Step 13: Test End-to-End FIR Generation

```bash
# Test API authentication
curl -X POST http://98.86.30.145:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'

# Upload test audio file
curl -X POST http://98.86.30.145:8000/api/v1/fir/generate \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -F "audio=@test-audio.mp3" \
  -F "incident_type=theft"

# Check FIR status
curl http://98.86.30.145:8000/api/v1/fir/<FIR_ID> \
  -H "Authorization: Bearer <YOUR_TOKEN>"
```

---

### Step 14: Set Up Monitoring

```bash
# Verify CloudWatch agent (if installed)
sudo systemctl status amazon-cloudwatch-agent

# Check CloudWatch alarms
aws cloudwatch describe-alarms --alarm-name-prefix "afirgen-prod"

# View CloudWatch dashboard
# Navigate to: https://console.aws.amazon.com/cloudwatch/
# Select: Dashboards > AFIRGen-Production
```

---

### Step 15: Configure Backups

```bash
# Set up automated database backups
cd /opt/afirgen
cp backup_scheduler.sh /opt/afirgen/
chmod +x /opt/afirgen/backup_scheduler.sh

# Add to crontab for daily backups at 2 AM
crontab -e

# Add this line:
# 0 2 * * * /opt/afirgen/backup_scheduler.sh >> /var/log/afirgen-backup.log 2>&1
```

---

## Verification Checklist

After completing all steps, verify:

- [ ] EC2 instance is running and accessible via SSH
- [ ] Application is running (systemd service active)
- [ ] Health endpoint returns 200 OK
- [ ] Database connection is working
- [ ] Vector database is initialized
- [ ] AWS Bedrock access is configured
- [ ] CloudWatch alarms are active
- [ ] SNS email subscription is confirmed
- [ ] Security groups are properly configured
- [ ] Environment variables are set correctly
- [ ] Backups are scheduled
- [ ] End-to-end FIR generation works

---

## Troubleshooting

### Application Won't Start

```bash
# Check logs
sudo journalctl -u afirgen -n 100 --no-pager

# Check if port is in use
sudo netstat -tulpn | grep 8000

# Verify environment file
cat /opt/afirgen/.env

# Test Python imports
cd /opt/afirgen/"main backend"
source /opt/afirgen/venv/bin/activate
python -c "from api.main import app; print('OK')"
```

### Database Connection Issues

```bash
# Test connection
mysql -h afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com \
      -u admin -p \
      -e "SELECT 1;"

# Check security group rules
aws ec2 describe-security-groups --group-ids <RDS_SECURITY_GROUP_ID>

# Verify RDS is running
aws rds describe-db-instances --db-instance-identifier afirgen-free-tier-mysql
```

### Bedrock Access Issues

```bash
# Check IAM role attached to EC2
aws ec2 describe-instances --instance-ids i-0bc18e312758fda7c \
  --query 'Reservations[0].Instances[0].IamInstanceProfile'

# Verify IAM role has Bedrock permissions
aws iam get-role-policy --role-name <ROLE_NAME> --policy-name BedrockAccess

# Test Bedrock API
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-v2 \
  --body '{"prompt":"Hello","max_tokens_to_sample":100}' \
  --region us-east-1 \
  output.txt
```

### High Memory/CPU Usage

```bash
# Check resource usage
top
htop

# Check application logs for errors
sudo journalctl -u afirgen -f

# Restart application
sudo systemctl restart afirgen
```

---

## Next Steps

Once everything is verified:

1. **Set up SSL/TLS** - Configure Let's Encrypt or AWS Certificate Manager
2. **Configure Domain** - Point your domain to the EC2 IP
3. **Enable HTTPS** - Update CORS_ORIGINS and ENFORCE_HTTPS=true
4. **Load Testing** - Run performance tests to verify capacity
5. **Documentation** - Update API documentation with production URLs
6. **Monitoring** - Set up custom CloudWatch dashboards
7. **Backup Testing** - Verify backup and restore procedures
8. **Disaster Recovery** - Test rollback procedures

---

## Useful Commands

```bash
# Restart application
sudo systemctl restart afirgen

# View real-time logs
sudo journalctl -u afirgen -f

# Check application status
sudo systemctl status afirgen

# Stop application
sudo systemctl stop afirgen

# Check disk space
df -h

# Check memory usage
free -h

# Check network connections
sudo netstat -tulpn

# Update application code
cd /opt/afirgen
git pull
sudo systemctl restart afirgen
```

---

## Support Resources

- **Architecture Documentation:** `.kiro/specs/bedrock-migration/design.md`
- **API Documentation:** `openapi.yaml`
- **Troubleshooting Guide:** `BEDROCK-TROUBLESHOOTING.md`
- **Production Deployment:** `PRODUCTION-DEPLOYMENT-README.md`
- **Security Guide:** `SECURITY.md`

---

**Deployment Date:** March 2, 2026  
**Last Updated:** March 2, 2026  
**Status:** Infrastructure deployed, application setup in progress
