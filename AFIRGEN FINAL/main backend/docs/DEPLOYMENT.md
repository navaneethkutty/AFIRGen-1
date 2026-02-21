# AFIRGen Backend Deployment Guide

## Overview

This guide covers deploying the AFIRGen backend system in various environments (development, staging, production). The system can be deployed using Docker Compose for local/development environments or as individual services in production.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Local Development Deployment](#local-development-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Production Deployment](#production-deployment)
6. [Database Setup](#database-setup)
7. [Monitoring Setup](#monitoring-setup)
8. [Troubleshooting](#troubleshooting)
9. [Deployment Checklist](#deployment-checklist)

---

## Prerequisites

### System Requirements

**Minimum Requirements**:
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Disk**: 50 GB SSD
- **OS**: Linux (Ubuntu 20.04+), macOS, or Windows with WSL2

**Recommended for Production**:
- **CPU**: 8+ cores
- **RAM**: 16+ GB
- **Disk**: 100+ GB SSD
- **OS**: Linux (Ubuntu 22.04 LTS)

### Software Dependencies

- **Python**: 3.11 or higher
- **MySQL**: 8.0 or higher
- **Redis**: 7.0 or higher
- **Docker**: 24.0+ (for containerized deployment)
- **Docker Compose**: 2.20+ (for local development)

### External Services

- **GGUF LLM Model Server**: Running on port 8001
- **ASR/OCR Server**: Running on port 8002
- **Prometheus** (optional): For metrics collection
- **Jaeger/Zipkin** (optional): For distributed tracing

---

## Environment Configuration

### Environment Variables

The application uses environment variables for configuration. Copy `.env.optimization.example` to `.env` and update values:

```bash
cp .env.optimization.example .env
```

### Core Configuration

```bash
# Application
SERVICE_NAME=afirgen-backend
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_OUTPUT=stdout

# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=afirgen_user
DB_PASSWORD=secure_password_here
DB_NAME=afirgen
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Redis Cache
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5

# Celery (Background Tasks)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_TASK_TIME_LIMIT=3600
CELERY_TASK_SOFT_TIME_LIMIT=3300
CELERY_WORKER_PREFETCH_MULTIPLIER=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
CELERY_WORKER_POOL=prefork
CELERY_WORKER_CONCURRENCY=4

# Model Servers
MODEL_SERVER_URL=http://localhost:8001
ASR_OCR_SERVER_URL=http://localhost:8002
MODEL_SERVER_TIMEOUT=120
MODEL_SERVER_MAX_RETRIES=3

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_KEY=your-secure-api-key-here
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60

# Monitoring
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
PROMETHEUS_METRICS_PATH=/metrics

# Tracing (OpenTelemetry)
OTEL_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=afirgen-backend
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1

# Security
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
ALLOWED_HOSTS=localhost,127.0.0.1
SECRET_KEY=your-secret-key-here-change-in-production

# File Upload
MAX_UPLOAD_SIZE_MB=50
ALLOWED_AUDIO_TYPES=audio/wav,audio/mpeg,audio/mp4,audio/ogg,audio/flac
ALLOWED_IMAGE_TYPES=image/png,image/jpeg,image/webp
```

### Environment-Specific Configurations

#### Development (.env.development)
```bash
LOG_LEVEL=DEBUG
DB_HOST=localhost
REDIS_HOST=localhost
OTEL_ENABLED=false
CORS_ORIGINS=*
```

#### Staging (.env.staging)
```bash
LOG_LEVEL=INFO
DB_HOST=staging-db.example.com
REDIS_HOST=staging-redis.example.com
OTEL_ENABLED=true
CORS_ORIGINS=https://staging.example.com
```

#### Production (.env.production)
```bash
LOG_LEVEL=WARNING
DB_HOST=prod-db.example.com
REDIS_HOST=prod-redis.example.com
OTEL_ENABLED=true
CORS_ORIGINS=https://app.example.com
SECRET_KEY=<strong-random-key>
API_KEY=<strong-random-key>
```

---

## Local Development Deployment

### 1. Clone Repository

```bash
git clone https://github.com/your-org/afirgen-backend.git
cd afirgen-backend
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.optimization.example .env
# Edit .env with your local configuration
```

### 5. Setup Database

```bash
# Start MySQL (if not running)
sudo systemctl start mysql

# Create database
mysql -u root -p << EOF
CREATE DATABASE afirgen CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'afirgen_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON afirgen.* TO 'afirgen_user'@'localhost';
FLUSH PRIVILEGES;
EOF

# Run migrations
python migrations/migration_runner.py apply 001_add_fir_indexes
python migrations/migration_runner.py apply 002_add_background_tasks_table
```

### 6. Start Redis

```bash
# Install Redis (if not installed)
sudo apt-get install redis-server  # Ubuntu/Debian
brew install redis  # macOS

# Start Redis
redis-server
```

### 7. Start Celery Workers

```bash
# In a separate terminal
celery -A infrastructure.celery_app worker --loglevel=info --concurrency=4
```

### 8. Start Application

```bash
# Development mode with auto-reload
uvicorn agentv5:app --reload --host 0.0.0.0 --port 8000

# Or using the startup script
python agentv5.py
```

### 9. Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

---

## Docker Deployment

### Using Docker Compose (Recommended for Development)

#### 1. Review Docker Compose Configuration

The `compose.yaml` file defines all services:

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=db
      - REDIS_HOST=redis
    depends_on:
      - db
      - redis
  
  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: afirgen
      MYSQL_USER: afirgen_user
      MYSQL_PASSWORD: password
    volumes:
      - mysql_data:/var/lib/mysql
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
  
  celery:
    build: .
    command: celery -A infrastructure.celery_app worker --loglevel=info
    environment:
      - DB_HOST=db
      - REDIS_HOST=redis
    depends_on:
      - db
      - redis

volumes:
  mysql_data:
  redis_data:
```

#### 2. Build and Start Services

```bash
# Build images
docker compose build

# Start all services
docker compose up -d

# View logs
docker compose logs -f app

# Check service status
docker compose ps
```

#### 3. Run Database Migrations

```bash
docker compose exec app python migrations/migration_runner.py apply 001_add_fir_indexes
docker compose exec app python migrations/migration_runner.py apply 002_add_background_tasks_table
```

#### 4. Access Application

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

#### 5. Stop Services

```bash
# Stop services
docker compose down

# Stop and remove volumes
docker compose down -v
```

### Building Docker Image Manually

```bash
# Build image
docker build -t afirgen-backend:latest .

# Run container
docker run -d \
  --name afirgen-backend \
  -p 8000:8000 \
  -e DB_HOST=host.docker.internal \
  -e REDIS_HOST=host.docker.internal \
  --env-file .env \
  afirgen-backend:latest
```

---

## Production Deployment

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer (AWS ALB/Nginx)             │
└─────────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  FastAPI     │  │  FastAPI     │  │  FastAPI     │
│  Instance 1  │  │  Instance 2  │  │  Instance 3  │
└──────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  MySQL RDS   │  │  Redis       │  │  Celery      │
│  (Primary)   │  │  ElastiCache │  │  Workers     │
└──────────────┘  └──────────────┘  └──────────────┘
```

### AWS Deployment

#### 1. Infrastructure Setup

**RDS (MySQL)**:
```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier afirgen-db \
  --db-instance-class db.t3.medium \
  --engine mysql \
  --engine-version 8.0.35 \
  --master-username admin \
  --master-user-password <secure-password> \
  --allocated-storage 100 \
  --storage-type gp3 \
  --vpc-security-group-ids sg-xxxxx \
  --db-subnet-group-name afirgen-subnet-group \
  --backup-retention-period 7 \
  --multi-az
```

**ElastiCache (Redis)**:
```bash
# Create Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id afirgen-redis \
  --cache-node-type cache.t3.medium \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1 \
  --cache-subnet-group-name afirgen-subnet-group \
  --security-group-ids sg-xxxxx
```

**EC2 Instances** (or ECS/EKS):
```bash
# Launch EC2 instances with Auto Scaling Group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name afirgen-asg \
  --launch-template LaunchTemplateName=afirgen-template \
  --min-size 2 \
  --max-size 10 \
  --desired-capacity 3 \
  --vpc-zone-identifier "subnet-xxxxx,subnet-yyyyy" \
  --target-group-arns arn:aws:elasticloadbalancing:...
```

#### 2. Application Deployment

**Using systemd (EC2)**:

Create `/etc/systemd/system/afirgen-backend.service`:
```ini
[Unit]
Description=AFIRGen Backend API
After=network.target

[Service]
Type=simple
User=afirgen
WorkingDirectory=/opt/afirgen-backend
Environment="PATH=/opt/afirgen-backend/venv/bin"
EnvironmentFile=/opt/afirgen-backend/.env
ExecStart=/opt/afirgen-backend/venv/bin/uvicorn agentv5:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-config logging.conf
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/afirgen-celery.service`:
```ini
[Unit]
Description=AFIRGen Celery Worker
After=network.target

[Service]
Type=simple
User=afirgen
WorkingDirectory=/opt/afirgen-backend
Environment="PATH=/opt/afirgen-backend/venv/bin"
EnvironmentFile=/opt/afirgen-backend/.env
ExecStart=/opt/afirgen-backend/venv/bin/celery \
  -A infrastructure.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=1000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable afirgen-backend afirgen-celery
sudo systemctl start afirgen-backend afirgen-celery
sudo systemctl status afirgen-backend afirgen-celery
```

#### 3. Load Balancer Configuration

**Nginx Configuration** (`/etc/nginx/sites-available/afirgen`):
```nginx
upstream afirgen_backend {
    least_conn;
    server 10.0.1.10:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.11:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.12:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.example.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://afirgen_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
    
    location /health {
        proxy_pass http://afirgen_backend/health;
        access_log off;
    }
    
    location /metrics {
        proxy_pass http://afirgen_backend/metrics;
        allow 10.0.0.0/8;  # Internal network only
        deny all;
    }
}
```

Enable configuration:
```bash
sudo ln -s /etc/nginx/sites-available/afirgen /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Database Setup

### Initial Database Creation

```sql
-- Create database
CREATE DATABASE afirgen 
  CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER 'afirgen_user'@'%' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON afirgen.* TO 'afirgen_user'@'%';
FLUSH PRIVILEGES;
```

### Running Migrations

```bash
# Set database connection environment variables
export DB_HOST=your-db-host
export DB_PORT=3306
export DB_USER=afirgen_user
export DB_PASSWORD=your_password
export DB_NAME=afirgen

# Apply migrations
python migrations/migration_runner.py apply 001_add_fir_indexes
python migrations/migration_runner.py apply 002_add_background_tasks_table

# Verify migrations
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "SHOW TABLES;"
```

### Database Backup

```bash
# Backup database
mysqldump -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore database
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME < backup_20240115_103000.sql
```

### Database Maintenance

```bash
# Optimize tables
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME << EOF
OPTIMIZE TABLE fir_records;
OPTIMIZE TABLE sessions;
OPTIMIZE TABLE background_tasks;
ANALYZE TABLE fir_records;
ANALYZE TABLE sessions;
ANALYZE TABLE background_tasks;
EOF
```

---

## Monitoring Setup

### Prometheus Configuration

Create `prometheus.yml`:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'afirgen-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics/prometheus'
    scrape_interval: 10s
```

Start Prometheus:
```bash
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

### Grafana Dashboard

1. Install Grafana:
```bash
docker run -d \
  --name grafana \
  -p 3000:3000 \
  grafana/grafana
```

2. Add Prometheus data source:
   - URL: http://prometheus:9090
   - Access: Server (default)

3. Import dashboard:
   - Use dashboard ID: 1860 (Node Exporter Full)
   - Create custom dashboard for AFIRGen metrics

### Log Aggregation

**Using ELK Stack**:

```bash
# Elasticsearch
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  elasticsearch:8.11.0

# Logstash
docker run -d \
  --name logstash \
  -p 5000:5000 \
  -v $(pwd)/logstash.conf:/usr/share/logstash/pipeline/logstash.conf \
  logstash:8.11.0

# Kibana
docker run -d \
  --name kibana \
  -p 5601:5601 \
  -e "ELASTICSEARCH_HOSTS=http://elasticsearch:9200" \
  kibana:8.11.0
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**Symptom**: `Can't connect to MySQL server`

**Solutions**:
```bash
# Check database is running
systemctl status mysql

# Test connection
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD -e "SELECT 1;"

# Check firewall rules
sudo ufw status
sudo ufw allow 3306/tcp

# Verify credentials in .env file
cat .env | grep DB_
```

#### 2. Redis Connection Errors

**Symptom**: `Error connecting to Redis`

**Solutions**:
```bash
# Check Redis is running
systemctl status redis

# Test connection
redis-cli ping

# Check Redis configuration
redis-cli CONFIG GET bind
redis-cli CONFIG GET protected-mode
```

#### 3. High Memory Usage

**Symptom**: Application consuming excessive memory

**Solutions**:
```bash
# Check memory usage
free -h
docker stats

# Reduce worker count
# In .env:
API_WORKERS=2
CELERY_WORKER_CONCURRENCY=2

# Restart services
systemctl restart afirgen-backend afirgen-celery
```

#### 4. Slow API Responses

**Symptom**: API response times > 5 seconds

**Solutions**:
```bash
# Check database query performance
mysql -e "SHOW PROCESSLIST;"

# Check cache hit rate
curl http://localhost:8000/metrics | grep cache_hit_rate

# Enable query logging
# In .env:
LOG_LEVEL=DEBUG
LOG_MODULE_LEVELS=infrastructure.database=DEBUG

# Check model server health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### Log Analysis

```bash
# View application logs
journalctl -u afirgen-backend -f

# View Celery logs
journalctl -u afirgen-celery -f

# Search for errors
journalctl -u afirgen-backend | grep ERROR

# View logs from Docker
docker compose logs -f app
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Review and update `.env` configuration
- [ ] Backup existing database
- [ ] Test migrations on staging environment
- [ ] Review security settings (API keys, secrets)
- [ ] Update CORS origins for production domain
- [ ] Configure SSL certificates
- [ ] Set up monitoring and alerting
- [ ] Prepare rollback plan

### Deployment Steps

- [ ] Stop existing services
- [ ] Pull latest code / Deploy new Docker image
- [ ] Install/update dependencies
- [ ] Run database migrations
- [ ] Update configuration files
- [ ] Start services
- [ ] Verify health checks
- [ ] Run smoke tests
- [ ] Monitor logs for errors
- [ ] Verify metrics collection

### Post-Deployment

- [ ] Monitor application metrics
- [ ] Check error rates
- [ ] Verify cache hit rates
- [ ] Test critical API endpoints
- [ ] Review logs for warnings/errors
- [ ] Update documentation
- [ ] Notify team of deployment completion

### Rollback Procedure

If deployment fails:

1. Stop new services:
```bash
systemctl stop afirgen-backend afirgen-celery
```

2. Rollback database migrations:
```bash
python migrations/migration_runner.py rollback 002_add_background_tasks_table
python migrations/migration_runner.py rollback 001_add_fir_indexes
```

3. Restore previous version:
```bash
git checkout <previous-tag>
pip install -r requirements.txt
```

4. Restore database backup (if needed):
```bash
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME < backup_before_deployment.sql
```

5. Start services:
```bash
systemctl start afirgen-backend afirgen-celery
```

6. Verify rollback:
```bash
curl http://localhost:8000/health
```

---

## Security Considerations

### Production Security Checklist

- [ ] Use strong, unique passwords for all services
- [ ] Enable SSL/TLS for all connections
- [ ] Configure firewall rules (allow only necessary ports)
- [ ] Use environment variables for secrets (never commit to git)
- [ ] Enable database encryption at rest
- [ ] Configure Redis password authentication
- [ ] Implement rate limiting
- [ ] Set up intrusion detection
- [ ] Regular security updates
- [ ] Enable audit logging
- [ ] Restrict SSH access
- [ ] Use VPN for administrative access

### Secrets Management

**Using AWS Secrets Manager**:
```bash
# Store secret
aws secretsmanager create-secret \
  --name afirgen/db-password \
  --secret-string "your-secure-password"

# Retrieve secret in application
aws secretsmanager get-secret-value \
  --secret-id afirgen/db-password \
  --query SecretString \
  --output text
```

---

## Support

For deployment issues or questions:
- **Documentation**: [Full Documentation]
- **GitHub Issues**: [Repository Issues]
- **Email**: devops@example.com
- **Slack**: #afirgen-deployments

---

## Appendix

### Useful Commands

```bash
# Check service status
systemctl status afirgen-backend

# View logs
journalctl -u afirgen-backend -f

# Restart service
systemctl restart afirgen-backend

# Check port usage
netstat -tulpn | grep 8000

# Test API endpoint
curl -X GET http://localhost:8000/health

# Monitor system resources
htop
iotop
```

### Performance Tuning

**Database**:
```sql
-- Increase buffer pool size (in my.cnf)
innodb_buffer_pool_size = 4G
innodb_log_file_size = 512M
max_connections = 200
```

**Redis**:
```conf
# In redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

**Application**:
```bash
# In .env
API_WORKERS=8  # Number of CPU cores
CELERY_WORKER_CONCURRENCY=8
DB_POOL_SIZE=30
```
