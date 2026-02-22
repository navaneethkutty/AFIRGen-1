# EC2 Instance Quick Reference

## Instance Details

| Property | Value |
|----------|-------|
| Instance Type | t2.micro |
| vCPU | 1 |
| Memory | 1 GB |
| Storage | 30 GB gp3 (encrypted) |
| Network | Public subnet + Elastic IP |
| Free Tier | 750 hours/month |

## Access

```bash
# SSH to instance
ssh -i your-key.pem ubuntu@<elastic-ip>

# Get Elastic IP from Terraform
terraform output ec2_public_ip
```

## Key Directories

```
/opt/afirgen/              # Main application directory
├── models/                # ML models (downloaded from S3)
├── logs/                  # Application logs
├── .env                   # Environment configuration
├── monitor.sh             # System monitoring
└── health-check.sh        # Service health checks
```

## Quick Commands

### Check Setup Status
```bash
# Verify setup completed
ls -la /opt/afirgen/setup_complete.flag

# View setup log
tail -f /var/log/user-data.log
```

### Monitor System
```bash
# System status
/opt/afirgen/monitor.sh

# Service health
/opt/afirgen/health-check.sh

# Docker containers
docker ps
docker stats --no-stream
```

### View Logs
```bash
# Application logs
tail -f /opt/afirgen/logs/*.log

# User data log
tail -f /var/log/user-data.log

# Docker logs
docker-compose -f docker-compose.free-tier.yml logs -f
```

### Manage Services
```bash
# Start services
cd /opt/afirgen
docker-compose -f docker-compose.free-tier.yml up -d

# Stop services
docker-compose -f docker-compose.free-tier.yml down

# Restart services
docker-compose -f docker-compose.free-tier.yml restart

# View service status
docker-compose -f docker-compose.free-tier.yml ps
```

## Environment Variables

Located in `/opt/afirgen/.env`:

```bash
# Database
MYSQL_HOST=<rds-endpoint>
MYSQL_PORT=3306
MYSQL_USER=admin
MYSQL_PASSWORD=<password>
MYSQL_DB=fir_db

# Services
GGUF_SERVER_URL=http://localhost:8001
ASR_OCR_SERVER_URL=http://localhost:8002

# Environment
ENVIRONMENT=free-tier
AWS_REGION=us-east-1

# Performance
MAX_WORKERS=1
MAX_CONCURRENT_REQUESTS=3

# Memory Limits (MB)
BACKEND_MEMORY_LIMIT=300
GGUF_MEMORY_LIMIT=400
ASR_OCR_MEMORY_LIMIT=300
NGINX_MEMORY_LIMIT=50
```

## CloudWatch

### Metrics (AFIRGen/FreeTier namespace)
- CPU_IDLE
- CPU_IOWAIT
- DISK_USED
- MEM_USED

### Logs (/aws/ec2/afirgen log group)
- {instance-id}/syslog
- {instance-id}/application
- {instance-id}/user-data

## Troubleshooting

### Models Not Downloaded
```bash
cd /opt/afirgen/models
aws s3 sync s3://afirgen-models-<account-id>/ .
touch models_downloaded.flag
```

### CloudWatch Agent Issues
```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json
```

### Docker Issues
```bash
sudo systemctl status docker
sudo systemctl restart docker
sudo journalctl -u docker
```

### High Memory Usage
```bash
# Check container memory
docker stats --no-stream

# Check system memory
free -h

# Restart containers if needed
docker-compose -f docker-compose.free-tier.yml restart
```

## Security

### Ports
- 80 (HTTP): Open to internet
- 443 (HTTPS): Open to internet
- 22 (SSH): Restricted to admin IP

### IAM Permissions
- S3: Read/Write to models, temp, backups buckets
- CloudWatch: Send metrics and logs

### Files
- `.env`: Contains database credentials (chmod 600)
- Models: Cached locally to minimize S3 requests

## Automated Tasks

### Cron Jobs
- **Hourly**: System monitoring → `/opt/afirgen/logs/monitor.log`
- **Every 5 min**: Health checks → `/opt/afirgen/logs/health-check.log`
- **Weekly**: Log cleanup (removes logs >7 days old)

### Log Rotation
- Daily rotation
- 7-day retention
- Compressed archives
- Auto-restart services after rotation

## Cost Optimization

### Free Tier Usage
- EC2: 750 hours/month (one t2.micro 24/7)
- EBS: 30 GB (within free tier)
- Data Transfer: 15 GB/month out
- CloudWatch: 10 metrics, 5 GB logs

### Best Practices
1. Models cached locally (minimize S3 GET requests)
2. Logs rotated daily (7-day retention)
3. CloudWatch metrics at 60-second intervals
4. Memory limits enforced on containers

## Next Steps

1. Wait for user data script to complete (5-10 minutes)
2. Verify setup: `ls /opt/afirgen/setup_complete.flag`
3. Deploy application code
4. Create docker-compose.free-tier.yml
5. Start services
6. Run health checks

## Support

For detailed information, see:
- EC2-SETUP-GUIDE.md
- DEPLOYMENT-GUIDE.md
- README.md
