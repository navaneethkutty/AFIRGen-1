# Task 1.5 Implementation Summary

## Task Description

**Task**: 1.5 Launch EC2 t2.micro instance with user data script

**Requirements**: 2.1, 2.5

**Objectives**:
- Launch t2.micro instance in public subnet
- Attach 30GB gp3 EBS volume
- Configure user data script to install Docker, Docker Compose, CloudWatch agent
- Create and attach IAM role for S3 access
- Allocate and attach Elastic IP

## Implementation

### Files Created

1. **ec2.tf** - Main EC2 configuration
   - EC2 t2.micro instance definition
   - IAM role and policies for S3 and CloudWatch access
   - IAM instance profile
   - Elastic IP allocation
   - Outputs for instance details

2. **user-data.sh** - Automated setup script
   - System updates
   - Docker and Docker Compose installation
   - CloudWatch agent installation and configuration
   - Directory structure creation
   - ML model download from S3
   - Environment configuration
   - Monitoring scripts setup
   - Cron jobs configuration

3. **EC2-SETUP-GUIDE.md** - Comprehensive documentation
   - Instance specifications
   - Components installed
   - Directory structure
   - IAM permissions
   - User data script details
   - Environment variables
   - Monitoring setup
   - Security configuration
   - Deployment steps
   - Troubleshooting guide

4. **EC2-QUICK-REFERENCE.md** - Quick reference guide
   - Instance details table
   - Access commands
   - Key directories
   - Quick commands for monitoring and management
   - Environment variables reference
   - CloudWatch integration
   - Troubleshooting tips

5. **TASK-1.5-IMPLEMENTATION-SUMMARY.md** - This file

### Files Modified

1. **variables.tf** - Added new variables:
   - `ami_id`: Ubuntu 22.04 LTS AMI ID
   - `rds_endpoint`: RDS endpoint (placeholder for now)
   - `db_name`: Database name
   - `db_username`: Database username
   - `db_password`: Database password

2. **terraform.tfvars.example** - Updated with new variables:
   - AMI ID configuration
   - Database configuration
   - Instructions for finding AMI ID

3. **main.tf** - Updated deployment summary output:
   - Added `ec2_instance_id`
   - Added `ec2_public_ip`

4. **README.md** - Enhanced with EC2 information:
   - EC2 architecture section
   - Automated setup details
   - IAM permissions
   - Updated deployment steps
   - EC2 access instructions

## EC2 Instance Configuration

### Instance Specifications

| Property | Value |
|----------|-------|
| Instance Type | t2.micro |
| vCPU | 1 |
| Memory | 1 GB RAM |
| Storage | 30 GB gp3 (encrypted) |
| Network | Public subnet |
| Elastic IP | Yes |
| Monitoring | CloudWatch detailed monitoring |
| Free Tier | 750 hours/month |

### IAM Permissions

**S3 Access**:
- GetObject, PutObject, DeleteObject on models, temp, and backups buckets
- ListBucket on all three buckets

**CloudWatch Access**:
- PutMetricData: Send custom metrics
- CreateLogGroup, CreateLogStream, PutLogEvents: Send logs
- DescribeLogStreams: Query log streams

### User Data Script Features

The user data script (`user-data.sh`) performs comprehensive automated setup:

1. **System Configuration**:
   - Updates all system packages
   - Installs essential utilities (htop, vim, git, jq, etc.)
   - Configures system limits for Docker

2. **Docker Installation**:
   - Installs Docker Engine (latest stable)
   - Installs Docker Compose v2.24.0
   - Enables and starts Docker service

3. **CloudWatch Agent**:
   - Installs CloudWatch agent
   - Configures metrics collection (CPU, Memory, Disk)
   - Configures log collection (syslog, application logs, user data logs)
   - Sets 7-day log retention
   - Starts agent automatically

4. **Application Setup**:
   - Creates directory structure (`/opt/afirgen/`)
   - Downloads ML models from S3 (one-time)
   - Creates environment configuration (`.env`)
   - Sets appropriate permissions

5. **Monitoring**:
   - Creates monitoring script (`monitor.sh`)
   - Creates health check script (`health-check.sh`)
   - Configures cron jobs for automated monitoring
   - Sets up log rotation

6. **Logging**:
   - Configures logrotate for application logs
   - 7-day retention with compression
   - Automatic service restart after rotation

### Directory Structure

```
/opt/afirgen/
├── models/                    # ML models (downloaded from S3)
│   └── models_downloaded.flag # Indicates models are cached
├── logs/                      # Application logs
│   ├── monitor.log           # System monitoring logs
│   └── health-check.log      # Health check logs
├── temp_asr_ocr/             # Temporary ASR/OCR files
├── chroma_kb/                # ChromaDB vector database
├── kb/                       # Knowledge base files
├── .env                      # Environment configuration (chmod 600)
├── monitor.sh                # System monitoring script
├── health-check.sh           # Service health check script
└── setup_complete.flag       # Setup completion indicator
```

### Environment Configuration

The `.env` file contains:
- Database connection details (RDS endpoint, credentials)
- Service URLs (GGUF server, ASR/OCR server)
- Environment settings (free-tier mode)
- Performance settings (max workers, concurrent requests)
- S3 bucket names
- Model configuration (quantization, paths)
- Memory limits for each container

### CloudWatch Integration

**Metrics** (AFIRGen/FreeTier namespace):
- CPU_IDLE: CPU idle percentage
- CPU_IOWAIT: CPU I/O wait percentage
- DISK_USED: Disk usage percentage
- MEM_USED: Memory usage percentage

**Logs** (/aws/ec2/afirgen log group):
- {instance-id}/syslog: System logs
- {instance-id}/application: Application logs
- {instance-id}/user-data: User data script output

All logs have 7-day retention to stay within Free Tier limits (5GB/month).

### Automated Tasks

**Cron Jobs**:
- **Hourly**: System monitoring → `/opt/afirgen/logs/monitor.log`
- **Every 5 minutes**: Health checks → `/opt/afirgen/logs/health-check.log`
- **Weekly**: Log cleanup (removes logs older than 7 days)

**Log Rotation**:
- Daily rotation of application logs
- 7-day retention with compression
- Automatic service restart after rotation

## Security

### Network Security
- Instance in public subnet with Elastic IP
- Security group allows:
  - HTTP (80) from anywhere
  - HTTPS (443) from anywhere
  - SSH (22) from admin IP only
- All outbound traffic allowed

### Data Security
- EBS volume encrypted at rest
- IAM role for S3 access (no hardcoded credentials)
- Database credentials in .env file (chmod 600)
- S3 buckets have encryption enabled (SSE-S3)

### System Security
- Automatic security updates enabled
- Minimal attack surface (only necessary services)
- SSH access restricted to specific IP
- Docker containers run with memory limits

## Cost Optimization

### Free Tier Compliance

- **EC2 Hours**: 750 hours/month (one t2.micro instance 24/7) ✅
- **EBS Storage**: 30 GB (within 30 GB free tier) ✅
- **Data Transfer**: Minimized by caching models locally ✅
- **CloudWatch**: 10 metrics, 5 GB logs (configured within limits) ✅

### Best Practices Implemented

1. **Model Caching**: Models downloaded once from S3, cached locally
2. **Log Rotation**: 7-day retention, automatic cleanup
3. **Monitoring Efficiency**: 60-second intervals, minimal metrics
4. **S3 Optimization**: Minimize GET requests by caching

## Deployment Process

### Prerequisites

1. AWS account (free tier eligible)
2. Terraform >= 1.0 installed
3. AWS CLI configured
4. SSH key pair created in AWS

### Steps

1. **Configure Variables**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

2. **Deploy Infrastructure**:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

3. **Wait for Setup** (5-10 minutes):
   ```bash
   # SSH to instance
   ssh -i your-key.pem ubuntu@$(terraform output -raw ec2_public_ip)
   
   # Monitor setup progress
   tail -f /var/log/user-data.log
   
   # Verify completion
   ls -la /opt/afirgen/setup_complete.flag
   ```

4. **Verify Installation**:
   ```bash
   # Check Docker
   docker --version
   docker-compose --version
   
   # Check CloudWatch agent
   sudo systemctl status amazon-cloudwatch-agent
   
   # Check models downloaded
   ls -lh /opt/afirgen/models/
   
   # Run monitoring script
   /opt/afirgen/monitor.sh
   ```

## Testing

### Manual Testing

1. **SSH Access**:
   ```bash
   ssh -i your-key.pem ubuntu@<elastic-ip>
   ```

2. **User Data Completion**:
   ```bash
   cat /var/log/user-data.log
   ls /opt/afirgen/setup_complete.flag
   ```

3. **Docker Installation**:
   ```bash
   docker --version
   docker-compose --version
   sudo systemctl status docker
   ```

4. **CloudWatch Agent**:
   ```bash
   sudo systemctl status amazon-cloudwatch-agent
   ```

5. **Models Downloaded**:
   ```bash
   ls -lh /opt/afirgen/models/
   cat /opt/afirgen/models/models_downloaded.flag
   ```

6. **Environment Configuration**:
   ```bash
   cat /opt/afirgen/.env
   ```

7. **Monitoring Scripts**:
   ```bash
   /opt/afirgen/monitor.sh
   /opt/afirgen/health-check.sh
   ```

### CloudWatch Verification

1. **Metrics**: Check AFIRGen/FreeTier namespace in CloudWatch console
2. **Logs**: Check /aws/ec2/afirgen log group
3. **Alarms**: Will be configured in later tasks

## Troubleshooting

### Common Issues

1. **User Data Script Failed**:
   - Check `/var/log/user-data.log` for errors
   - Verify IAM permissions for S3 access
   - Check network connectivity

2. **Models Not Downloaded**:
   - Manually run: `aws s3 sync s3://afirgen-models-<account-id>/ /opt/afirgen/models/`
   - Verify S3 bucket exists and has models
   - Check IAM permissions

3. **CloudWatch Agent Not Running**:
   - Restart: `sudo systemctl restart amazon-cloudwatch-agent`
   - Check config: `/opt/aws/amazon-cloudwatch-agent/etc/config.json`
   - Verify IAM permissions

4. **Docker Not Starting**:
   - Check status: `sudo systemctl status docker`
   - View logs: `sudo journalctl -u docker`
   - Restart: `sudo systemctl restart docker`

## Next Steps

After EC2 instance is running:

1. **Task 1.6**: Create RDS db.t3.micro MySQL instance
2. **Task 1.7**: Write property test for storage compliance
3. **Phase 2**: Deploy application services
4. **Phase 3**: Configure monitoring and optimization

## Requirements Satisfied

✅ **Requirement 2.1**: Deploy all backend services on one t2.micro EC2 instance
✅ **Requirement 2.5**: Provide 30GB of EBS storage for the EC2 instance

## Documentation

- **Detailed Guide**: [EC2-SETUP-GUIDE.md](./EC2-SETUP-GUIDE.md)
- **Quick Reference**: [EC2-QUICK-REFERENCE.md](./EC2-QUICK-REFERENCE.md)
- **Main README**: [README.md](./README.md)
- **Deployment Guide**: [DEPLOYMENT-GUIDE.md](./DEPLOYMENT-GUIDE.md)

## Terraform Resources Created

1. `aws_iam_role.ec2` - IAM role for EC2 instance
2. `aws_iam_role_policy.ec2_s3` - S3 access policy
3. `aws_iam_role_policy.ec2_cloudwatch` - CloudWatch access policy
4. `aws_iam_instance_profile.ec2` - Instance profile
5. `aws_instance.main` - EC2 t2.micro instance
6. `aws_eip.main` - Elastic IP

## Outputs Added

- `ec2_instance_id`: EC2 instance identifier
- `ec2_instance_type`: Instance type (t2.micro)
- `ec2_private_ip`: Private IP address
- `ec2_public_ip`: Public IP address (Elastic IP)
- `ec2_elastic_ip`: Elastic IP address
- `ec2_iam_role`: IAM role name
- `ec2_configuration`: Configuration summary

## Conclusion

Task 1.5 has been successfully implemented with:

✅ EC2 t2.micro instance configured
✅ 30GB gp3 EBS volume attached (encrypted)
✅ User data script for automated setup
✅ Docker and Docker Compose installed
✅ CloudWatch agent configured
✅ IAM role with S3 and CloudWatch permissions
✅ Elastic IP allocated and attached
✅ Comprehensive documentation created
✅ Monitoring and health check scripts
✅ Automated tasks via cron jobs
✅ Free Tier compliant configuration

The EC2 instance is ready to host the AFIRGen application services once the RDS database is created and the application code is deployed.
