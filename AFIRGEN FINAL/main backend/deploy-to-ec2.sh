#!/bin/bash
# AFIRGen Backend Deployment Script for EC2 (t3.medium)
# Run this script on your EC2 instance after SSH'ing in

set -e  # Exit on error

echo "============================================================"
echo "AFIRGen Backend Deployment to EC2"
echo "Instance Type: t3.medium (required)"
echo "============================================================"
echo ""

# Check if running on EC2
if [ ! -f /sys/hypervisor/uuid ] || ! grep -q ec2 /sys/hypervisor/uuid 2>/dev/null; then
    echo "⚠ Warning: This doesn't appear to be an EC2 instance"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Variables
DEPLOY_DIR="/opt/afirgen-backend"
REPO_URL="https://github.com/navaneethkutty/AFIRGen-1.git"
BRANCH="main"

echo "Step 1: Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip git mysql-client

echo ""
echo "Step 2: Setting up deployment directory..."
if [ -d "$DEPLOY_DIR" ]; then
    echo "  Directory exists, pulling latest changes..."
    cd "$DEPLOY_DIR"
    git pull origin $BRANCH
else
    echo "  Creating new deployment..."
    sudo mkdir -p "$DEPLOY_DIR"
    sudo chown $USER:$USER "$DEPLOY_DIR"
    git clone -b $BRANCH "$REPO_URL" "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
fi

# Navigate to backend directory
cd "AFIRGEN FINAL/main backend"

echo ""
echo "Step 3: Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3.11 -m venv venv
fi
source venv/bin/activate

echo ""
echo "Step 4: Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Step 5: Configuring environment variables..."
if [ ! -f ".env" ]; then
    echo "  Creating .env file from template..."
    cp .env.example .env
    
    echo ""
    echo "============================================================"
    echo "IMPORTANT: Configure your .env file"
    echo "============================================================"
    echo "Edit the .env file with your production values:"
    echo ""
    echo "  nano .env"
    echo ""
    echo "Required values:"
    echo "  - AWS_REGION=us-east-1"
    echo "  - S3_BUCKET_NAME=afirgen-storage-bucket"
    echo "  - DB_HOST=afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com"
    echo "  - DB_PASSWORD=Prathiush12."
    echo "  - DB_NAME=afirgen"
    echo "  - API_KEY=<your-production-api-key>"
    echo ""
    echo "Note: AWS credentials should use IAM role (already configured on EC2)"
    echo "      Comment out AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
    echo ""
    read -p "Press Enter after you've configured .env..."
else
    echo "  .env file already exists"
fi

echo ""
echo "Step 6: Testing database connectivity..."
python3 << 'PYTHON_SCRIPT'
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        connection_timeout=10
    )
    print("✓ MySQL RDS connection successful!")
    conn.close()
except Exception as e:
    print(f"✗ MySQL connection failed: {e}")
    print("  Check your .env configuration and RDS security group")
    exit(1)
PYTHON_SCRIPT

echo ""
echo "Step 7: Creating logs directory..."
mkdir -p logs

echo ""
echo "Step 8: Installing systemd service..."
sudo cp afirgen.service /etc/systemd/system/
sudo sed -i "s|/opt/afirgen|$DEPLOY_DIR/AFIRGEN FINAL/main backend|g" /etc/systemd/system/afirgen.service
sudo sed -i "s|User=ubuntu|User=$USER|g" /etc/systemd/system/afirgen.service
sudo systemctl daemon-reload

echo ""
echo "Step 9: Starting backend service..."
sudo systemctl enable afirgen
sudo systemctl restart afirgen

echo ""
echo "Step 10: Checking service status..."
sleep 3
sudo systemctl status afirgen --no-pager

echo ""
echo "Step 11: Testing health endpoint..."
sleep 2
curl -s http://localhost:8000/health | python3 -m json.tool || echo "Health check failed"

echo ""
echo "============================================================"
echo "Deployment Complete!"
echo "============================================================"
echo ""
echo "Service Status:"
echo "  sudo systemctl status afirgen"
echo ""
echo "View Logs:"
echo "  sudo journalctl -u afirgen -f"
echo "  tail -f logs/main_backend.log"
echo ""
echo "Test Endpoints:"
echo "  curl http://localhost:8000/health"
echo "  curl http://98.86.30.145:8000/health"
echo ""
echo "Manage Service:"
echo "  sudo systemctl start afirgen"
echo "  sudo systemctl stop afirgen"
echo "  sudo systemctl restart afirgen"
echo ""
echo "Next Steps:"
echo "  1. Test the /health endpoint from external"
echo "  2. Configure frontend to use http://98.86.30.145:8000"
echo "  3. Test FIR generation end-to-end"
echo ""
