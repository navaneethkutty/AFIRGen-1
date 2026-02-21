# Docker Compose Guide for AFIRGen Backend

## Overview

This guide explains how to use Docker Compose to run the AFIRGen backend system locally for development and testing.

## Prerequisites

- **Docker**: Version 24.0 or higher
- **Docker Compose**: Version 2.20 or higher
- **Disk Space**: At least 5 GB free

## Quick Start

### 1. Basic Setup (API + Database + Redis + Celery)

```bash
# Start all core services
docker compose up -d

# View logs
docker compose logs -f

# Check service status
docker compose ps
```

This starts:
- **app**: FastAPI application (port 8000)
- **db**: MySQL database (port 3306)
- **redis**: Redis cache (port 6379)
- **celery**: Celery worker for background tasks

### 2. Access the Application

- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

### 3. Stop Services

```bash
# Stop services (keeps data)
docker compose down

# Stop and remove volumes (deletes data)
docker compose down -v
```

---

## Service Profiles

Docker Compose profiles allow you to start optional services.

### Full Profile (includes scheduled tasks)

```bash
docker compose --profile full up -d
```

This adds:
- **celery-beat**: Scheduled task runner

### Monitoring Profile (includes monitoring stack)

```bash
docker compose --profile monitoring up -d
```

This adds:
- **prometheus**: Metrics collection (port 9090)
- **grafana**: Visualization dashboard (port 3000)

### All Services

```bash
docker compose --profile full --profile monitoring up -d
```

---

## Configuration

### Environment Variables

The `compose.yaml` file includes default environment variables. To customize:

1. Create a `.env` file:
```bash
cp .env.optimization.example .env
```

2. Edit `.env` with your values

3. Update `compose.yaml` to use `.env`:
```yaml
services:
  app:
    env_file:
      - .env
```

### Database Configuration

Default credentials (change for production):
- **Root Password**: `rootpassword`
- **Database**: `afirgen`
- **User**: `afirgen_user`
- **Password**: `afirgen_password`

### Redis Configuration

Default settings:
- **Max Memory**: 2 GB
- **Eviction Policy**: allkeys-lru
- **Persistence**: AOF enabled

---

## Database Migrations

### Run Migrations

```bash
# Wait for database to be ready
docker compose exec db mysqladmin ping -h localhost -u root -prootpassword

# Run migrations
docker compose exec app python migrations/migration_runner.py apply 001_add_fir_indexes
docker compose exec app python migrations/migration_runner.py apply 002_add_background_tasks_table
```

### Verify Migrations

```bash
# Check tables
docker compose exec db mysql -u afirgen_user -pafirgen_password afirgen -e "SHOW TABLES;"

# Check indexes
docker compose exec db mysql -u afirgen_user -pafirgen_password afirgen -e "SHOW INDEX FROM fir_records;"
```

---

## Development Workflow

### 1. Start Services

```bash
docker compose up -d
```

### 2. View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f app
docker compose logs -f celery
```

### 3. Execute Commands in Containers

```bash
# Python shell
docker compose exec app python

# Run tests
docker compose exec app pytest

# Access MySQL
docker compose exec db mysql -u afirgen_user -pafirgen_password afirgen

# Access Redis
docker compose exec redis redis-cli
```

### 4. Rebuild After Code Changes

```bash
# Rebuild and restart
docker compose up -d --build

# Rebuild specific service
docker compose up -d --build app
```

### 5. Scale Services

```bash
# Run multiple Celery workers
docker compose up -d --scale celery=3
```

---

## Monitoring

### Prometheus

Access Prometheus at http://localhost:9090

**Useful Queries**:
```promql
# Request rate
rate(api_requests_total[5m])

# Response time (95th percentile)
histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))

# Cache hit rate
cache_hit_rate

# Database connections
db_connection_pool_size
```

### Grafana

Access Grafana at http://localhost:3000

**Default Credentials**:
- Username: `admin`
- Password: `admin`

**Setup**:
1. Add Prometheus data source: http://prometheus:9090
2. Import dashboard or create custom dashboard
3. Add panels for key metrics

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs app

# Check service health
docker compose ps

# Restart service
docker compose restart app
```

### Database Connection Issues

```bash
# Check database is running
docker compose ps db

# Test connection
docker compose exec app python -c "import mysql.connector; conn = mysql.connector.connect(host='db', user='afirgen_user', password='afirgen_password', database='afirgen'); print('Connected!')"

# Check database logs
docker compose logs db
```

### Redis Connection Issues

```bash
# Check Redis is running
docker compose ps redis

# Test connection
docker compose exec redis redis-cli ping

# Check Redis logs
docker compose logs redis
```

### Port Already in Use

```bash
# Find process using port
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # macOS/Linux

# Change port in compose.yaml
services:
  app:
    ports:
      - "8001:8000"  # Map to different host port
```

### Out of Disk Space

```bash
# Check disk usage
docker system df

# Clean up unused resources
docker system prune -a --volumes

# Remove specific volumes
docker volume rm afirgen_mysql_data
docker volume rm afirgen_redis_data
```

### Slow Performance

```bash
# Check resource usage
docker stats

# Increase resources in Docker Desktop settings
# - CPU: 4+ cores
# - Memory: 8+ GB
# - Disk: 50+ GB
```

---

## Data Management

### Backup Database

```bash
# Backup to file
docker compose exec db mysqldump -u afirgen_user -pafirgen_password afirgen > backup_$(date +%Y%m%d_%H%M%S).sql

# Or using docker cp
docker compose exec db mysqldump -u afirgen_user -pafirgen_password afirgen > /tmp/backup.sql
docker cp afirgen-db:/tmp/backup.sql ./backup.sql
```

### Restore Database

```bash
# Restore from file
docker compose exec -T db mysql -u afirgen_user -pafirgen_password afirgen < backup.sql

# Or using docker cp
docker cp backup.sql afirgen-db:/tmp/backup.sql
docker compose exec db mysql -u afirgen_user -pafirgen_password afirgen -e "source /tmp/backup.sql"
```

### Clear Redis Cache

```bash
# Flush all Redis data
docker compose exec redis redis-cli FLUSHALL

# Flush specific database
docker compose exec redis redis-cli -n 0 FLUSHDB
```

### Reset Everything

```bash
# Stop and remove all containers, networks, and volumes
docker compose down -v

# Remove images
docker compose down --rmi all

# Start fresh
docker compose up -d --build
```

---

## Production Considerations

### Security

1. **Change Default Passwords**:
```yaml
environment:
  - MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
  - MYSQL_PASSWORD=${MYSQL_PASSWORD}
```

2. **Use Secrets** (Docker Swarm):
```yaml
secrets:
  db_password:
    external: true

services:
  db:
    secrets:
      - db_password
    environment:
      - MYSQL_PASSWORD_FILE=/run/secrets/db_password
```

3. **Restrict Network Access**:
```yaml
services:
  db:
    ports: []  # Don't expose to host
```

### Performance

1. **Resource Limits**:
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

2. **Optimize Database**:
```yaml
services:
  db:
    command: >
      --innodb_buffer_pool_size=4G
      --max_connections=500
```

3. **Scale Workers**:
```bash
docker compose up -d --scale celery=5
```

### High Availability

For production, consider:
- **Load Balancer**: Nginx or AWS ALB
- **Database Replication**: MySQL master-slave
- **Redis Cluster**: Redis Sentinel or Cluster mode
- **Container Orchestration**: Kubernetes or Docker Swarm

---

## Advanced Usage

### Custom Network

```yaml
networks:
  afirgen-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

### Volume Mounts for Development

```yaml
services:
  app:
    volumes:
      - .:/app  # Mount source code for live reload
      - /app/venv  # Exclude virtual environment
```

### Health Checks

```yaml
services:
  app:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Logging

```yaml
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## Useful Commands

```bash
# View resource usage
docker compose stats

# Execute command in running container
docker compose exec app bash

# Copy files to/from container
docker compose cp app:/app/logs/app.log ./app.log

# View container details
docker compose inspect app

# Restart specific service
docker compose restart app

# Pull latest images
docker compose pull

# Build without cache
docker compose build --no-cache

# Remove orphaned containers
docker compose down --remove-orphans
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Docker Compose Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start services
        run: docker compose up -d
      
      - name: Wait for services
        run: |
          timeout 60 bash -c 'until docker compose exec -T app curl -f http://localhost:8000/health; do sleep 2; done'
      
      - name: Run tests
        run: docker compose exec -T app pytest
      
      - name: Stop services
        run: docker compose down -v
```

---

## FAQ

**Q: How do I connect to the database from my host machine?**

A: Use `localhost:3306` with the credentials from `compose.yaml`.

**Q: Can I use this for production?**

A: This configuration is designed for development. For production, use proper secrets management, resource limits, and consider orchestration platforms like Kubernetes.

**Q: How do I update to a new version?**

A: Pull the latest code, rebuild images, and restart:
```bash
git pull
docker compose up -d --build
```

**Q: Where is the data stored?**

A: Data is stored in Docker volumes:
- `mysql_data`: Database files
- `redis_data`: Redis persistence files

**Q: How do I access logs?**

A: Use `docker compose logs -f [service]` or check the `./logs` directory mounted in containers.

---

## Support

For issues or questions:
- **Documentation**: See main README.md
- **GitHub Issues**: [Repository Issues]
- **Docker Compose Docs**: https://docs.docker.com/compose/
