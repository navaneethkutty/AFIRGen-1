#!/bin/bash
# AFIRGen EC2 Setup Script
# Run this script on your EC2 instance after deployment

set -e

echo "=========================================="
echo "AFIRGen EC2 Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/opt/afirgen"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="afirgen"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root"
    exit 1
fi

echo "Step 1: Updating system packages..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq
print_status "System packages updated"

echo ""
echo "Step 2: Installing dependencies..."
sudo apt-get install -y -qq \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    mysql-client \
    postgresql-client \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    curl \
    wget \
    unzip
print_status "Dependencies installed"

echo ""
echo "Step 3: Creating application directory..."
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR
print_status "Application directory created: $APP_DIR"

echo ""
echo "Step 4: Setting up Python virtual environment..."
cd $APP_DIR
python3.11 -m venv $VENV_DIR
source $VENV_DIR/bin/activate
pip install --upgrade pip -q
print_status "Virtual environment created"

echo ""
echo "Step 5: Installing AWS CLI..."
if ! command -v aws &> /dev/null; then
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip -q awscliv2.zip
    sudo ./aws/install
    rm -rf aws awscliv2.zip
    print_status "AWS CLI installed"
else
    print_status "AWS CLI already installed"
fi

echo ""
echo "Step 6: Checking for application code..."
if [ ! -f "$APP_DIR/main backend/requirements.txt" ]; then
    print_warning "Application code not found in $APP_DIR"
    echo "Please upload your code using one of these methods:"
    echo ""
    echo "Method 1: SCP from local machine"
    echo "  scp -i your-key.pem -r 'AFIRGEN FINAL'/* ubuntu@$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):/opt/afirgen/"
    echo ""
    echo "Method 2: Git clone"
    echo "  cd $APP_DIR"
    echo "  git clone <YOUR_REPO_URL> ."
    echo ""
    echo "After uploading code, run this script again."
    exit 0
else
    print_status "Application code found"
fi

echo ""
echo "Step 7: Installing Python dependencies..."
if [ -f "$APP_DIR/main backend/requirements.txt" ]; then
    pip install -r "$APP_DIR/main backend/requirements.txt" -q
    print_status "Python dependencies installed"
fi

# Install additional AWS dependencies
pip install boto3 pymysql cryptography -q
print_status "AWS dependencies installed"

echo ""
echo "Step 8: Setting up environment configuration..."
if [ ! -f "$APP_DIR/.env" ]; then
    if [ -f "$APP_DIR/.env.bedrock" ]; then
        cp "$APP_DIR/.env.bedrock" "$APP_DIR/.env"
        print_status "Environment file created from .env.bedrock"
    elif [ -f "$APP_DIR/.env.example" ]; then
        cp "$APP_DIR/.env.example" "$APP_DIR/.env"
        print_status "Environment file created from .env.example"
    else
        print_warning "No environment template found"
        echo "Creating basic .env file..."
        cat > "$APP_DIR/.env" << 'EOF'
# AFIRGen Environment Configuration
MYSQL_HOST=afirgen-free-tier-mysql.ceniwmoioy4y.us-east-1.rds.amazonaws.com
MYSQL_PORT=3306
MYSQL_USER=admin
MYSQL_PASSWORD=CHANGE_ME
MYSQL_DB=fir_db

PORT=8000
FIR_AUTH_KEY=CHANGE_ME
API_KEY=CHANGE_ME

AWS_REGION=us-east-1
USE_AWS_SECRETS=false

CORS_ORIGINS=http://localhost:8000
ENFORCE_HTTPS=false
SESSION_TIMEOUT=3600
EOF
        print_status "Basic .env file created"
    fi
    
    print_warning "IMPORTANT: Edit $APP_DIR/.env with your actual configuration"
    echo "Run: nano $APP_DIR/.env"
else
    print_status "Environment file already exists"
fi

echo ""
echo "Step 9: Generating secure keys..."
FIR_AUTH_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")

echo "Generated keys (save these securely):"
echo "FIR_AUTH_KEY=$FIR_AUTH_KEY"
echo "API_KEY=$API_KEY"
echo ""
echo "Update these in $APP_DIR/.env"

echo ""
echo "Step 10: Creating systemd service..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=AFIRGen FIR Generation Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR/main backend
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_DIR/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
print_status "Systemd service created"

echo ""
echo "Step 11: Testing database connection..."
if [ -f "$APP_DIR/.env" ]; then
    source "$APP_DIR/.env"
    if mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1;" &> /dev/null; then
        print_status "Database connection successful"
        
        # Create database if it doesn't exist
        mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" \
            -e "CREATE DATABASE IF NOT EXISTS $MYSQL_DB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null
        print_status "Database '$MYSQL_DB' ready"
    else
        print_warning "Database connection failed - please check credentials in .env"
    fi
else
    print_warning "Skipping database test - .env file not configured"
fi

echo ""
echo "Step 12: Testing AWS Bedrock access..."
if aws bedrock list-foundation-models --region us-east-1 &> /dev/null; then
    print_status "AWS Bedrock access verified"
else
    print_warning "AWS Bedrock access failed - check IAM role permissions"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure environment variables:"
echo "   nano $APP_DIR/.env"
echo ""
echo "2. Update these values:"
echo "   - MYSQL_PASSWORD (from Terraform outputs)"
echo "   - FIR_AUTH_KEY (generated above)"
echo "   - API_KEY (generated above)"
echo "   - CORS_ORIGINS (your domain)"
echo ""
echo "3. Initialize database:"
echo "   cd $APP_DIR/main backend"
echo "   source $VENV_DIR/bin/activate"
echo "   python migrations/init_db.py"
echo ""
echo "4. Start the application:"
echo "   sudo systemctl enable $SERVICE_NAME"
echo "   sudo systemctl start $SERVICE_NAME"
echo ""
echo "5. Check status:"
echo "   sudo systemctl status $SERVICE_NAME"
echo "   curl http://localhost:8000/health"
echo ""
echo "6. View logs:"
echo "   sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "=========================================="
