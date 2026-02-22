# EC2 Instance Setup Guide

## Overview

This guide documents the EC2 t2.micro instance configuration for the AFIRGen Free Tier deployment. The instance is configured with automated setup via user data script and includes all necessary components for running the AFIRGen system.

## Instance Specifications

- **Instance Type**: t2.micro (Free Tier eligible)
- **vCPU**: 1
- **Memory**: 1 GB RAM
- **Storage**: 30 GB gp3 EBS volume (encrypted)
- **Network**: Public subnet with Elastic IP
- **Monitoring**: CloudWatch detailed monitoring enabled

## Components Installed

### 1. Docker and Docker Compose

- **Docker Engine**: Latest stable version
- **Docker Compose**: v2.24.0
- **Purpose**: Container orchestration for all AFIRGen services

### 2. CloudWatch Agent

- **Metrics Collection**: CPU, Memory, Disk usage
- **Log Collection**: System logs, application logs, user data logs
- **Namespace**: AFIRGen/FreeTier
- **Collection Interval**: 60 seconds

### 3. AWS CLI

- **Purpose**: S3 access for model downloads and backups
- **Configuration**: Uses IAM instance profile for authentication

### 4. System Utilities

- htop, iotop: System monitoring
- vim, git: Development tools
- jq: JSON processing
- net-tools: Network diagnostics

## Directory Structure

```
/opt/afirgen/
├── models/              # ML models downloaded from S3
│   └── models_downloaded.flag
├── logs/                # Application logs
│   ├── monitor.log
│   └── health-check.log
├── temp_asr_ocr/        # Temporary ASR/OCR files
├── chroma_kb/           # ChromaDB vector database
├── kb/                  # Knowledge base files
├── .env                 # Environment configuration
├── monitor.sh           # System monitoring script
├── health-check.sh      # Service health check script
└── setup_complete.flag  # Setup completion indicator
```

## IAM Permissions

The EC2 instance has an IAM role with the following permissions:

### S3 Access
- GetObject, PutObject, DeleteObject on:
  - Models bucket
  - Temp bucket
  - Backups bucket
- ListBucket on all three buckets

### CloudWatch Access
- PutMetricData: Send custom metrics
- CreateLogGroup, CreateLogStream, PutLogEvents: Send logs
- DescribeLogStreams: Query log streams

## User Data Script

The user data script (`user-data.sh`) performs the following tasks on first boot:

1. **System Update**: Updates all packages
2. **Docker Installation**: Installs Docker and Docker Compose
3. **CloudWatch Agent**: Installs and configures CloudWatch agent
4. **Directory Setup**: Creates application directory structure
5. **Model Download**: Downloads ML models from S3 (one-time)
6. **Environment Config**: Creates .env file with database and service URLs
7. **Log Rotation**: Configures logrotate for application logs
8. **Monitoring Scripts**: Creates monitoring and health check scripts
9. **Cron Jobs**: Sets up automated monitoring and cleanup

## Environment Variables

The `.env` file created by user data contains:

```bash
# Database Configuration
MYSQL_HOST=<rds-endpoint>
MYSQL_PORT=3306
MYSQL_USER=<username>
MYSQL_PASSWORD=<password>
MYSQL_DB=fir_db

# Service URLs
GGUF_SERVER_URL=http://localhost:8001
ASR_OCR_SERVER_URL=http://localhost:8002

# Environment
ENVIRONMENT=free-tier
AWS_REGION=us-east-1

# Performance Settings
MAX_WORKERS=1
MAX_CONCURRENT_REQUESTS=3

# S3 Buckets
S3_MODELS_BUCKET=<models-bucket>
S3_TEMP_BUCKET=<temp-bucket>
S3_BACKUPS_BUCKET=<backups-bucket>

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
```

## Monitoring

### System Monitoring Script

Run `/opt/afirgen/monitor.sh` to view:
- Memory usage
- Disk usage
- Docker container status
- Container memory usage
- Recent application logs

### Health Check Script

Run `/opt/afirgen/health-check.sh` to check:
- Main Backend health (port 8000)
- GGUF Server health (port 8001)
- ASR/OCR Server health (port 8002)

### Automated Monitoring

Cron jobs run automatically:
- **Hourly**: System monitoring (logged to monitor.log)
- **Every 5 minutes**: Health checks (logged to health-check.log)
- **Weekly**: Old log cleanup (removes logs older than 7 days)

## CloudWatch Integration

### Metrics

The CloudWatch agent sends these metrics to the `AFIRGen/FreeTier` namespace:
- **CPU_IDLE**: CPU idle percentage
- **CPU_IOWAIT**: CPU I/O wait percentage
- **DISK_USED**: Disk usage percentage
- **MEM_USED**: Memory usage percentage

### Logs

Logs are sent to the `/aws/ec2/afirgen` log group:
- **{instance-id}/syslog**: System logs
- **{instance-id}/application**: Application logs
- **{instance-id}/user-data**: User data script output

All logs have 7-day retention to stay within Free Tier limits.

## Security

### Network Security
- Instance in public subnet with Elastic IP
- Security group allows:
  - HTTP (80) from anywhere
  - HTTPS (443) from anywhere
  - SSH (22) from admin IP only

### Data Security
- EBS volume encrypted at rest
- IAM role for S3 access (no hardcoded credentials)
- Database credentials in .env file (restricted permissions)

### System Security
- Automatic security updates enabled
- Minimal attack surface (only necessary services)
- SSH access restricted to specific IP

## Deployment Steps

### 1. Configure Variables

Edit `terraform.tfvars`:
```hcl
admin_ip = "YOUR_IP/32"
ami_id = "ami-XXXXXXXXX"  # Ubuntu 22.04 LTS
db_username = "admin"
db_password = "STRONG_PASSWORD"
```

### 2. Deploy Infrastructure

```bash
cd terraform/free-tier
terraform init
terraform plan
terraform apply
```

### 3. Wait for Setup

The user data script takes 5-10 minutes to complete. Monitor progress:

```bash
# SSH to instance
ssh -i your-key.pem ubuntu@<elastic-ip>

# Check user data log
tail -f /var/log/user-data.log

# Verify setup complete
ls -la /opt/afirgen/setup_complete.flag
```

### 4. Deploy Application

```bash
# Copy application code
scp -r ./AFIRGEN\ FINAL/* ubuntu@<elastic-ip>:/opt/afirgen/

# Copy docker-compose configuration
scp docker-compose.free-tier.yml ubuntu@<elastic-ip>:/opt/afirgen/

# Start services
ssh ubuntu@<elastic-ip>
cd /opt/afirgen
docker-compose -f docker-compose.free-tier.yml up -d
```

### 5. Verify Deployment

```bash
# Check container status
docker ps

# Run health checks
/opt/afirgen/health-check.sh

# Check system resources
/opt/afirgen/monitor.sh

# View logs
tail -f /opt/afirgen/logs/*.log
```

## Troubleshooting

### User Data Script Failed

Check the log:
```bash
cat /var/log/user-data.log
```

Common issues:
- Network connectivity problems
- S3 bucket permissions
- Invalid AMI ID

### Models Not Downloaded

Manually download:
```bash
cd /opt/afirgen/models
aws s3 sync s3://afirgen-models-<account-id>/ .
touch models_downloaded.flag
```

### CloudWatch Agent Not Running

Restart the agent:
```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json
```

### Docker Not Starting

Check Docker status:
```bash
sudo systemctl status docker
sudo journalctl -u docker
```

Restart Docker:
```bash
sudo systemctl restart docker
```

## Cost Optimization

### Free Tier Compliance

- **EC2 Hours**: 750 hours/month (one t2.micro instance 24/7)
- **EBS Storage**: 30 GB (within 30 GB free tier)
- **Data Transfer**: Minimize by caching models locally
- **CloudWatch**: 10 metrics, 5 GB logs (configured within limits)

### Best Practices

1. **Model Caching**: Models downloaded once, cached locally
2. **Log Rotation**: 7-day retention, automatic cleanup
3. **Monitoring Efficiency**: 60-second intervals, minimal metrics
4. **S3 Optimization**: Minimize GET requests by caching

## Next Steps

After EC2 instance is running:

1. **Task 1.6**: Create RDS instance
2. **Task 1.7**: Write property test for storage compliance
3. **Phase 2**: Deploy application services
4. **Phase 3**: Configure monitoring and optimization

## References

- Requirements: 2.1, 2.5
- Design Document: Section 2 (Backend Deployment)
- Terraform Configuration: `ec2.tf`, `user-data.sh`
- Security Groups: `security-groups.tf`
- IAM Roles: Defined in `ec2.tf`
