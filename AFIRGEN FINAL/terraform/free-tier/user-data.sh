#!/bin/bash
# AFIRGen Free Tier EC2 User Data Script
# This script runs on first boot to configure the EC2 instance
# Requirements: 2.1, 2.5

set -e  # Exit on error
set -x  # Print commands for debugging

# Log all output to file
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=========================================="
echo "AFIRGen Free Tier EC2 Setup Starting"
echo "=========================================="
echo "Timestamp: $(date)"

# ============================================================================
# System Update
# ============================================================================
echo "Updating system packages..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

# ============================================================================
# Install Docker and Docker Compose
# ============================================================================
echo "Installing Docker..."
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io

# Install Docker Compose
echo "Installing Docker Compose..."
DOCKER_COMPOSE_VERSION="2.24.0"
curl -L "https://github.com/docker/compose/releases/download/v$${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Enable and start Docker service
systemctl enable docker
systemctl start docker

# Verify Docker installation
docker --version
docker-compose --version

# ============================================================================
# Install CloudWatch Agent
# ============================================================================
echo "Installing CloudWatch agent..."
wget -q https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i amazon-cloudwatch-agent.deb
rm amazon-cloudwatch-agent.deb

# Configure CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/config.json <<'EOF'
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "root"
  },
  "metrics": {
    "namespace": "AFIRGen/FreeTier",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {
            "name": "cpu_usage_idle",
            "rename": "CPU_IDLE",
            "unit": "Percent"
          },
          {
            "name": "cpu_usage_iowait",
            "rename": "CPU_IOWAIT",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60,
        "totalcpu": false
      },
      "disk": {
        "measurement": [
          {
            "name": "used_percent",
            "rename": "DISK_USED",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60,
        "resources": [
          "/"
        ]
      },
      "mem": {
        "measurement": [
          {
            "name": "mem_used_percent",
            "rename": "MEM_USED",
            "unit": "Percent"
          }
        ],
        "metrics_collection_interval": 60
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/syslog",
            "log_group_name": "/aws/ec2/afirgen",
            "log_stream_name": "{instance_id}/syslog",
            "retention_in_days": 7
          },
          {
            "file_path": "/opt/afirgen/logs/*.log",
            "log_group_name": "/aws/ec2/afirgen",
            "log_stream_name": "{instance_id}/application",
            "retention_in_days": 7
          },
          {
            "file_path": "/var/log/user-data.log",
            "log_group_name": "/aws/ec2/afirgen",
            "log_stream_name": "{instance_id}/user-data",
            "retention_in_days": 7
          }
        ]
      }
    }
  }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json

echo "CloudWatch agent started successfully"

# ============================================================================
# Install AWS CLI (if not already installed)
# ============================================================================
if ! command -v aws &> /dev/null; then
    echo "Installing AWS CLI..."
    apt-get install -y awscli
fi

# Verify AWS CLI
aws --version

# ============================================================================
# Create Application Directory Structure
# ============================================================================
echo "Creating application directory structure..."
mkdir -p /opt/afirgen
mkdir -p /opt/afirgen/models
mkdir -p /opt/afirgen/logs
mkdir -p /opt/afirgen/temp_asr_ocr
mkdir -p /opt/afirgen/chroma_kb
mkdir -p /opt/afirgen/kb

# Set permissions
chown -R ubuntu:ubuntu /opt/afirgen

# ============================================================================
# Download Models from S3
# ============================================================================
echo "Downloading ML models from S3..."
echo "Models bucket: ${models_bucket}"

# Download models to local disk (one-time setup)
# This reduces S3 GET requests and improves model loading performance
cd /opt/afirgen/models

# Check if models already exist (in case of instance restart)
if [ ! -f "models_downloaded.flag" ]; then
    echo "Downloading models for the first time..."
    aws s3 sync s3://${models_bucket}/ . --region ${aws_region}
    
    # Create flag file to indicate models have been downloaded
    touch models_downloaded.flag
    echo "Models downloaded successfully"
else
    echo "Models already downloaded, skipping..."
fi

# Verify model files exist
echo "Verifying model files..."
ls -lh /opt/afirgen/models/

# ============================================================================
# Create Environment Configuration
# ============================================================================
echo "Creating environment configuration..."
cat > /opt/afirgen/.env <<EOF
# Database Configuration
MYSQL_HOST=${rds_endpoint}
MYSQL_PORT=3306
MYSQL_USER=${db_username}
MYSQL_PASSWORD=${db_password}
MYSQL_DB=${db_name}

# Service URLs
GGUF_SERVER_URL=http://localhost:8001
ASR_OCR_SERVER_URL=http://localhost:8002

# Environment
ENVIRONMENT=free-tier
AWS_REGION=${aws_region}

# Performance Settings (Free Tier Optimized)
MAX_WORKERS=1
MAX_CONCURRENT_REQUESTS=3

# S3 Buckets
S3_MODELS_BUCKET=${models_bucket}
S3_TEMP_BUCKET=${temp_bucket}
S3_BACKUPS_BUCKET=${backups_bucket}

# Model Configuration
MODEL_DIR=/opt/afirgen/models
MODEL_QUANTIZATION=Q4_K_M
WHISPER_MODEL=base
MAX_CONTEXT_LENGTH=2048

# Memory Limits (MB)
BACKEND_MEMORY_LIMIT=300
GGUF_MEMORY_LIMIT=400
ASR_OCR_MEMORY_LIMIT=300
NGINX_MEMORY_LIMIT=50
EOF

chown ubuntu:ubuntu /opt/afirgen/.env
chmod 600 /opt/afirgen/.env

echo "Environment configuration created"

# ============================================================================
# Set Up Log Rotation
# ============================================================================
echo "Configuring log rotation..."
cat > /etc/logrotate.d/afirgen <<EOF
/opt/afirgen/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ubuntu ubuntu
    sharedscripts
    postrotate
        docker-compose -f /opt/afirgen/docker-compose.free-tier.yml restart > /dev/null 2>&1 || true
    endscript
}
EOF

echo "Log rotation configured"

# ============================================================================
# Install Additional Utilities
# ============================================================================
echo "Installing additional utilities..."
apt-get install -y \
    htop \
    iotop \
    net-tools \
    vim \
    git \
    jq \
    unzip

# ============================================================================
# Configure System Limits for Docker
# ============================================================================
echo "Configuring system limits..."
cat >> /etc/sysctl.conf <<EOF

# AFIRGen Docker optimizations
vm.max_map_count=262144
fs.file-max=65536
EOF

sysctl -p

# ============================================================================
# Create Monitoring Script
# ============================================================================
echo "Creating monitoring script..."
cat > /opt/afirgen/monitor.sh <<'MONITOR_EOF'
#!/bin/bash
# Simple monitoring script for AFIRGen free tier deployment

echo "=========================================="
echo "AFIRGen System Status"
echo "=========================================="
echo "Timestamp: $(date)"
echo ""

echo "Memory Usage:"
free -h
echo ""

echo "Disk Usage:"
df -h /
echo ""

echo "Docker Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "Docker Container Memory Usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}"
echo ""

echo "Recent Application Logs (last 10 lines):"
tail -n 10 /opt/afirgen/logs/*.log 2>/dev/null || echo "No logs found"
MONITOR_EOF

chmod +x /opt/afirgen/monitor.sh
chown ubuntu:ubuntu /opt/afirgen/monitor.sh

# ============================================================================
# Create Health Check Script
# ============================================================================
echo "Creating health check script..."
cat > /opt/afirgen/health-check.sh <<'HEALTH_EOF'
#!/bin/bash
# Health check script for AFIRGen services

check_service() {
    local service_name=$1
    local service_url=$2
    
    if curl -sf "$service_url" > /dev/null 2>&1; then
        echo "✓ $service_name is healthy"
        return 0
    else
        echo "✗ $service_name is unhealthy"
        return 1
    fi
}

echo "Checking AFIRGen services..."
check_service "Main Backend" "http://localhost:8000/health"
check_service "GGUF Server" "http://localhost:8001/health"
check_service "ASR/OCR Server" "http://localhost:8002/health"
HEALTH_EOF

chmod +x /opt/afirgen/health-check.sh
chown ubuntu:ubuntu /opt/afirgen/health-check.sh

# ============================================================================
# Setup Cron Jobs
# ============================================================================
echo "Setting up cron jobs..."
cat > /tmp/afirgen-cron <<EOF
# Run monitoring script every hour
0 * * * * /opt/afirgen/monitor.sh >> /opt/afirgen/logs/monitor.log 2>&1

# Run health check every 5 minutes
*/5 * * * * /opt/afirgen/health-check.sh >> /opt/afirgen/logs/health-check.log 2>&1

# Clean up old logs weekly
0 0 * * 0 find /opt/afirgen/logs -name "*.log" -mtime +7 -delete
EOF

crontab -u ubuntu /tmp/afirgen-cron
rm /tmp/afirgen-cron

echo "Cron jobs configured"

# ============================================================================
# Final Setup
# ============================================================================
echo "Finalizing setup..."

# Create a flag file to indicate setup is complete
touch /opt/afirgen/setup_complete.flag

# Print summary
echo ""
echo "=========================================="
echo "AFIRGen Free Tier EC2 Setup Complete!"
echo "=========================================="
echo "Instance ID: $(ec2-metadata --instance-id | cut -d ' ' -f 2)"
echo "Private IP: $(ec2-metadata --local-ipv4 | cut -d ' ' -f 2)"
echo "Public IP: $(ec2-metadata --public-ipv4 | cut -d ' ' -f 2)"
echo ""
echo "Next steps:"
echo "1. Deploy application code to /opt/afirgen"
echo "2. Create docker-compose.free-tier.yml"
echo "3. Start services: docker-compose -f docker-compose.free-tier.yml up -d"
echo ""
echo "Monitoring:"
echo "- Run: /opt/afirgen/monitor.sh"
echo "- Run: /opt/afirgen/health-check.sh"
echo "- Logs: /opt/afirgen/logs/"
echo ""
echo "CloudWatch:"
echo "- Metrics: AFIRGen/FreeTier namespace"
echo "- Logs: /aws/ec2/afirgen log group"
echo "=========================================="
