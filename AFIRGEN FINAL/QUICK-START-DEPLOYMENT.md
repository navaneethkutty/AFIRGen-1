# AFIRGen Quick Start - Post Deployment

**Infrastructure Status:** ✅ DEPLOYED  
**EC2 Instance:** i-0bc18e312758fda7c  
**EC2 IP:** 98.86.30.145  
**RDS Endpoint:** afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com:3306

---

## 🚀 Quick Setup (5 Commands)

### 1. Connect to EC2

```bash
ssh -i your-key.pem ubuntu@98.86.30.145
```

### 2. Upload Application Code

From your local machine:

```bash
cd "path/to/your/project"
scp -i your-key.pem -r "AFIRGEN FINAL"/* ubuntu@98.86.30.145:/tmp/afirgen-upload/
```

Or use Git:

```bash
# On EC2
sudo mkdir -p /opt/afirgen
sudo chown ubuntu:ubuntu /opt/afirgen
cd /opt/afirgen
git clone <YOUR_REPO_URL> .
```

### 3. Run Automated Setup

```bash
# On EC2
cd /opt/afirgen
chmod +x scripts/setup-ec2.sh
./scripts/setup-ec2.sh
```

This script will:
- Install all dependencies
- Set up Python environment
- Create systemd service
- Generate secure keys
- Test database connection
- Verify AWS Bedrock access

### 4. Configure Environment

```bash
# Edit environment file
nano /opt/afirgen/.env
```

Update these critical values:

```bash
MYSQL_PASSWORD=<from-terraform-outputs>
FIR_AUTH_KEY=<generated-by-setup-script>
API_KEY=<generated-by-setup-script>
CORS_ORIGINS=http://98.86.30.145:8000
```

### 5. Start Application

```bash
sudo systemctl enable afirgen
sudo systemctl start afirgen
sudo systemctl status afirgen
```

---

## ✅ Verify Deployment

```bash
# Check health endpoint
curl http://localhost:8000/health

# From your local machine
curl http://98.86.30.145:8000/health

# Expected: {"status": "healthy"}
```

---

## 📋 Essential Commands

```bash
# View logs
sudo journalctl -u afirgen -f

# Restart service
sudo systemctl restart afirgen

# Stop service
sudo systemctl stop afirgen

# Check status
sudo systemctl status afirgen
```

---

## 🔧 Get RDS Password

If you don't have the RDS password:

```bash
# From your local machine (in terraform directory)
cd "AFIRGEN FINAL/terraform/free-tier"
terraform output rds_password
```

Or check AWS Secrets Manager:

```bash
aws secretsmanager get-secret-value \
  --secret-id afirgen/rds/password \
  --query SecretString \
  --output text
```

---

## 🗄️ Initialize Database

```bash
# On EC2
cd /opt/afirgen
source venv/bin/activate

# Test connection
mysql -h afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com \
      -u admin -p \
      -e "SELECT VERSION();"

# Create database
mysql -h afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com \
      -u admin -p \
      -e "CREATE DATABASE IF NOT EXISTS fir_db;"

# Run migrations (if available)
cd "main backend"
python migrations/init_db.py
```

---

## 📧 Configure Email Alerts

```bash
# Subscribe to SNS topic
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:<ACCOUNT_ID>:afirgen-prod-alarms \
  --protocol email \
  --notification-endpoint your-email@example.com

# Check your email and confirm subscription
```

---

## 🧪 Test End-to-End

```bash
# Test health
curl http://98.86.30.145:8000/health

# Test API (after authentication is set up)
curl -X POST http://98.86.30.145:8000/api/v1/fir/generate \
  -H "Authorization: Bearer <TOKEN>" \
  -F "audio=@test-audio.mp3"
```

---

## 🐛 Troubleshooting

### Application won't start

```bash
# Check logs
sudo journalctl -u afirgen -n 50 --no-pager

# Check if port is in use
sudo netstat -tulpn | grep 8000

# Verify Python environment
cd /opt/afirgen
source venv/bin/activate
python -c "from api.main import app; print('OK')"
```

### Database connection fails

```bash
# Test connection
mysql -h afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com \
      -u admin -p

# Check security groups
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=afirgen-*"
```

### Can't access from browser

```bash
# Check security group allows port 8000
aws ec2 describe-security-groups \
  --group-ids <SECURITY_GROUP_ID> \
  --query 'SecurityGroups[0].IpPermissions'

# Add rule if needed
aws ec2 authorize-security-group-ingress \
  --group-id <SECURITY_GROUP_ID> \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0
```

---

## 📚 Full Documentation

For detailed setup instructions, see:
- **POST-DEPLOYMENT-SETUP.md** - Complete step-by-step guide
- **PRODUCTION-DEPLOYMENT-README.md** - Production deployment overview
- **PRE-DEPLOYMENT-CHECKLIST.md** - Pre-deployment verification

---

## 🎯 Success Checklist

- [ ] Connected to EC2 via SSH
- [ ] Application code uploaded
- [ ] Setup script completed
- [ ] Environment variables configured
- [ ] Database initialized
- [ ] Application service started
- [ ] Health endpoint returns 200 OK
- [ ] SNS email subscription confirmed
- [ ] CloudWatch alarms active
- [ ] End-to-end test successful

---

## 📞 Need Help?

Check these files:
- `POST-DEPLOYMENT-SETUP.md` - Detailed setup guide
- `BEDROCK-TROUBLESHOOTING.md` - Common issues
- `SECURITY.md` - Security configuration
- `.kiro/specs/bedrock-migration/design.md` - Architecture

---

**Quick Start Created:** March 2, 2026  
**Status:** Ready for deployment
