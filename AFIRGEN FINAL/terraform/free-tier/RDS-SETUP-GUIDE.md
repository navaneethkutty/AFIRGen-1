# RDS MySQL Setup Guide - AFIRGen Free Tier

## Overview

This guide covers the RDS db.t3.micro MySQL instance configuration for the AFIRGen Free Tier deployment. The RDS instance stores all FIR records and application data with optimized settings for Free Tier constraints.

## Configuration Summary

### Instance Specifications
- **Instance Class**: db.t3.micro (2 vCPU, 1GB RAM)
- **Engine**: MySQL 8.0.35
- **Storage**: 20GB gp2 (Free Tier limit)
- **Encryption**: Enabled (at rest)
- **Multi-AZ**: Disabled (not available in Free Tier)
- **Public Access**: Disabled (private subnets only)

### Network Configuration
- **Subnets**: Private subnets in us-east-1a and us-east-1b
- **Security Group**: Allows MySQL (port 3306) from EC2 security group only
- **Subnet Group**: afirgen-free-tier-db-subnet-group

### Backup Configuration
- **Retention Period**: 7 days (Free Tier maximum)
- **Backup Window**: 03:00-04:00 UTC (low-traffic period)
- **Maintenance Window**: Sunday 04:00-05:00 UTC (after backup)
- **Automated Backups**: Enabled

### Performance Parameters
Optimized for db.t3.micro (1GB RAM):
- `max_connections`: 50 (reduced from default 150)
- `innodb_buffer_pool_size`: 512MB (50% of available RAM)
- `slow_query_log`: Enabled (threshold: 2 seconds)
- `general_log`: Disabled (to save storage)

## Requirements Validation

### Requirement 5.1: Database Storage Management
✅ Single RDS db.t3.micro MySQL instance with 20GB storage

### Requirement 9.3: Security Within Free Tier
✅ RDS instance in private subnet with no public access
✅ Encryption at rest enabled using AWS-managed keys

### Requirement 15.1: Backup and Recovery
✅ RDS automated backups with 7-day retention

### Requirement 15.2: Backup and Recovery
✅ Backups scheduled during low-traffic windows (3:00-4:00 AM UTC)

## Deployment

### Prerequisites
1. VPC and subnets created (vpc.tf)
2. Security groups configured (security-groups.tf)
3. Database credentials set in terraform.tfvars

### Terraform Variables Required

```hcl
# terraform.tfvars
db_name     = "fir_db"
db_username = "admin"
db_password = "YourSecurePassword123!"  # Change this!
```

### Deploy RDS Instance

```bash
# Initialize Terraform (if not already done)
terraform init

# Plan the deployment
terraform plan

# Apply the configuration
terraform apply

# Get the RDS endpoint
terraform output rds_endpoint
```

### Verify Deployment

```bash
# Check RDS instance status
aws rds describe-db-instances \
  --db-instance-identifier afirgen-free-tier-mysql \
  --query 'DBInstances[0].[DBInstanceStatus,Endpoint.Address,AllocatedStorage]' \
  --output table

# Test connection from EC2 instance
mysql -h <rds-endpoint> -u admin -p fir_db
```

## CloudWatch Monitoring

### Alarms Created

1. **Storage Space Alarm**
   - Metric: FreeStorageSpace
   - Threshold: 2GB remaining (18GB used = 90% capacity)
   - Evaluation: 1 period of 5 minutes
   - Action: Alert when storage exceeds 90%

2. **CPU Utilization Alarm**
   - Metric: CPUUtilization
   - Threshold: 90%
   - Evaluation: 2 consecutive periods of 5 minutes
   - Action: Alert on sustained high CPU

3. **Database Connections Alarm**
   - Metric: DatabaseConnections
   - Threshold: 40 connections (80% of max 50)
   - Evaluation: 2 consecutive periods of 5 minutes
   - Action: Alert when approaching connection limit

### Monitoring Queries

```bash
# Check current storage usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value=afirgen-free-tier-mysql \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# Check current connections
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=afirgen-free-tier-mysql \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

## Database Management

### Connection from EC2

The EC2 instance automatically receives the RDS endpoint via user-data script:

```bash
# Environment variables set in /opt/afirgen/.env
MYSQL_HOST=<rds-endpoint>
MYSQL_PORT=3306
MYSQL_USER=admin
MYSQL_PASSWORD=<password>
MYSQL_DB=fir_db
```

### Manual Connection

```bash
# SSH to EC2 instance
ssh -i your-key.pem ubuntu@<ec2-public-ip>

# Install MySQL client (if not already installed)
sudo apt-get install -y mysql-client

# Connect to RDS
mysql -h $(grep MYSQL_HOST /opt/afirgen/.env | cut -d= -f2) \
      -u $(grep MYSQL_USER /opt/afirgen/.env | cut -d= -f2) \
      -p$(grep MYSQL_PASSWORD /opt/afirgen/.env | cut -d= -f2) \
      $(grep MYSQL_DB /opt/afirgen/.env | cut -d= -f2)
```

### Storage Cleanup

When storage exceeds 18GB (90% of 20GB limit), run cleanup:

```sql
-- Delete old validation history (>90 days)
DELETE FROM validation_history 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);

-- Delete archived FIR records (>180 days)
DELETE FROM fir_records 
WHERE status = 'archived' 
AND completed_at < DATE_SUB(NOW(), INTERVAL 180 DAY);

-- Check storage usage
SELECT 
    table_schema AS 'Database',
    SUM(data_length + index_length) / 1024 / 1024 / 1024 AS 'Size (GB)'
FROM information_schema.tables
WHERE table_schema = 'fir_db'
GROUP BY table_schema;
```

### Automated Cleanup Script

Create a cron job on EC2 to run cleanup when needed:

```bash
# Create cleanup script
cat > /opt/afirgen/db-cleanup.sh <<'EOF'
#!/bin/bash
# Database cleanup script for AFIRGen Free Tier

# Get current storage usage
STORAGE_USED=$(aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value=afirgen-free-tier-mysql \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --query 'Datapoints[0].Average' \
  --output text)

# Convert to GB
STORAGE_FREE_GB=$(echo "scale=2; $STORAGE_USED / 1024 / 1024 / 1024" | bc)

# If less than 2GB free, run cleanup
if (( $(echo "$STORAGE_FREE_GB < 2" | bc -l) )); then
    echo "Storage low ($STORAGE_FREE_GB GB free), running cleanup..."
    
    mysql -h $MYSQL_HOST -u $MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DB <<SQL
    DELETE FROM validation_history WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
    DELETE FROM fir_records WHERE status = 'archived' AND completed_at < DATE_SUB(NOW(), INTERVAL 180 DAY);
SQL
    
    echo "Cleanup completed"
else
    echo "Storage OK ($STORAGE_FREE_GB GB free)"
fi
EOF

chmod +x /opt/afirgen/db-cleanup.sh

# Add to crontab (run daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/afirgen/db-cleanup.sh >> /opt/afirgen/logs/db-cleanup.log 2>&1") | crontab -
```

## Backup and Recovery

### Automated Backups

Backups are automatically created daily during the backup window (03:00-04:00 UTC):
- Retention: 7 days
- Storage: Within 20GB Free Tier limit
- Location: AWS-managed backup storage

### Manual Snapshot

```bash
# Create manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier afirgen-free-tier-mysql \
  --db-snapshot-identifier afirgen-manual-snapshot-$(date +%Y%m%d-%H%M%S)

# List snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier afirgen-free-tier-mysql \
  --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime,Status]' \
  --output table
```

### Restore from Backup

```bash
# Restore from automated backup
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier afirgen-free-tier-mysql \
  --target-db-instance-identifier afirgen-free-tier-mysql-restored \
  --restore-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier afirgen-free-tier-mysql-restored \
  --db-snapshot-identifier <snapshot-id>
```

### Test Restore Procedure

Monthly restore test (Requirement 15.5):

```bash
# 1. Create test snapshot
aws rds create-db-snapshot \
  --db-instance-identifier afirgen-free-tier-mysql \
  --db-snapshot-identifier afirgen-restore-test-$(date +%Y%m%d)

# 2. Restore to new instance
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier afirgen-test-restore \
  --db-snapshot-identifier afirgen-restore-test-$(date +%Y%m%d) \
  --db-instance-class db.t3.micro

# 3. Verify data integrity
mysql -h <test-instance-endpoint> -u admin -p fir_db -e "SELECT COUNT(*) FROM fir_records;"

# 4. Delete test instance
aws rds delete-db-instance \
  --db-instance-identifier afirgen-test-restore \
  --skip-final-snapshot

# 5. Delete test snapshot
aws rds delete-db-snapshot \
  --db-snapshot-identifier afirgen-restore-test-$(date +%Y%m%d)
```

## Performance Optimization

### Connection Pooling

Application services should use connection pooling with these limits:
- Max connections per service: 5
- Total max connections: 50
- Idle timeout: 60 seconds

Example Python configuration:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}",
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### Query Optimization

Monitor slow queries:

```sql
-- Enable slow query log (already enabled in parameter group)
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;

-- View slow queries
SELECT * FROM mysql.slow_log ORDER BY query_time DESC LIMIT 10;

-- Analyze table statistics
ANALYZE TABLE fir_records;
ANALYZE TABLE validation_history;
```

### Index Optimization

```sql
-- Check missing indexes
SELECT 
    table_name,
    index_name,
    cardinality
FROM information_schema.statistics
WHERE table_schema = 'fir_db'
ORDER BY cardinality DESC;

-- Add indexes for common queries
CREATE INDEX idx_fir_status ON fir_records(status);
CREATE INDEX idx_fir_created ON fir_records(created_at);
CREATE INDEX idx_validation_created ON validation_history(created_at);
```

## Troubleshooting

### Connection Issues

```bash
# Test connectivity from EC2
telnet <rds-endpoint> 3306

# Check security group rules
aws ec2 describe-security-groups \
  --group-ids <rds-security-group-id> \
  --query 'SecurityGroups[0].IpPermissions'

# Verify RDS is in correct subnets
aws rds describe-db-instances \
  --db-instance-identifier afirgen-free-tier-mysql \
  --query 'DBInstances[0].DBSubnetGroup'
```

### High CPU Usage

```bash
# Check current CPU
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=afirgen-free-tier-mysql \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum

# Check for long-running queries
mysql -h <rds-endpoint> -u admin -p -e "SHOW PROCESSLIST;"

# Kill long-running query
mysql -h <rds-endpoint> -u admin -p -e "KILL <process_id>;"
```

### Storage Full

```bash
# Check storage usage
aws rds describe-db-instances \
  --db-instance-identifier afirgen-free-tier-mysql \
  --query 'DBInstances[0].[AllocatedStorage,DBInstanceStatus]'

# Run manual cleanup
/opt/afirgen/db-cleanup.sh

# If still full, consider:
# 1. Delete old backups (keep only 3 days)
# 2. Archive data to S3
# 3. Upgrade to larger instance (costs money)
```

## Cost Monitoring

### Free Tier Limits
- **Instance Hours**: 750 hours/month (db.t3.micro)
- **Storage**: 20GB
- **Backup Storage**: 20GB (same as allocated storage)
- **I/O Operations**: Unlimited in Free Tier

### Monitor Usage

```bash
# Check RDS costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '1 month ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --filter file://rds-filter.json

# rds-filter.json
{
  "Dimensions": {
    "Key": "SERVICE",
    "Values": ["Amazon Relational Database Service"]
  }
}
```

### After Free Tier (12 months)

Estimated monthly cost:
- db.t3.micro: ~$12/month (730 hours × $0.016/hour)
- Storage (20GB): ~$2.30/month (20GB × $0.115/GB)
- Backup storage: Free (equal to allocated storage)
- **Total**: ~$14.30/month

## Security Best Practices

### Password Management

```bash
# Rotate password (recommended every 90 days)
aws rds modify-db-instance \
  --db-instance-identifier afirgen-free-tier-mysql \
  --master-user-password <new-password> \
  --apply-immediately

# Update application configuration
sed -i 's/MYSQL_PASSWORD=.*/MYSQL_PASSWORD=<new-password>/' /opt/afirgen/.env

# Restart application
docker-compose -f /opt/afirgen/docker-compose.free-tier.yml restart
```

### Encryption

- **At Rest**: Enabled using AWS-managed keys (free)
- **In Transit**: Use SSL/TLS connections

```python
# Python MySQL connection with SSL
import pymysql

connection = pymysql.connect(
    host=host,
    user=user,
    password=password,
    database=database,
    ssl={'ssl': True}
)
```

### Audit Logging

```sql
-- Enable audit log (if needed, costs extra storage)
-- Not recommended for Free Tier due to storage limits

-- Instead, use application-level logging
-- Log all database operations in application logs
```

## Outputs Reference

After deployment, Terraform provides these outputs:

```bash
# Get all RDS outputs
terraform output | grep rds

# Specific outputs
terraform output rds_endpoint          # host:port
terraform output rds_address           # hostname only
terraform output rds_port              # 3306
terraform output rds_database_name     # fir_db
terraform output rds_instance_id       # afirgen-free-tier-mysql
```

## Next Steps

1. ✅ RDS instance created and configured
2. ⏭️ Deploy application code to EC2
3. ⏭️ Create database schema
4. ⏭️ Test database connectivity
5. ⏭️ Configure application connection pooling
6. ⏭️ Set up monitoring and alerts
7. ⏭️ Test backup and restore procedures

## Support and Resources

- [AWS RDS Free Tier Documentation](https://aws.amazon.com/rds/free/)
- [MySQL 8.0 Documentation](https://dev.mysql.com/doc/refman/8.0/en/)
- [RDS Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)
- [AFIRGen Design Document](.kiro/specs/aws-optimization-plan/design.md)
