# Environment Configuration Guide

## Overview

This guide explains how to configure the AFIRGen backend for different environments (development, staging, production).

## Configuration Files

| File | Purpose | Use Case |
|------|---------|----------|
| `.env.optimization.example` | Template with all options | Reference and starting point |
| `.env.development` | Development settings | Local development |
| `.env.staging` | Staging settings | Pre-production testing |
| `.env.production` | Production settings | Live deployment |

## Quick Start

### Development Setup

```bash
# Copy development template
cp .env.development .env

# Edit with your local values
nano .env

# Start application
python agentv5.py
```

### Staging/Production Setup

```bash
# Copy appropriate template
cp .env.staging .env  # or .env.production

# Set secrets via environment variables
export DB_PASSWORD="your-secure-password"
export REDIS_PASSWORD="your-redis-password"
export API_KEY="your-api-key"
export SECRET_KEY="your-secret-key"

# Start application
uvicorn agentv5:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Configuration Sections

### 1. Application Configuration

```bash
SERVICE_NAME=afirgen-backend
ENVIRONMENT=development  # development, staging, production
DEBUG=false  # true only for development
```

**Best Practices**:
- Use descriptive service names for monitoring
- Set `DEBUG=false` in production
- Use `ENVIRONMENT` to conditionally enable features

---

### 2. Logging Configuration

```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json  # json or text
LOG_OUTPUT=stdout  # stdout, file, or both
LOG_MODULE_LEVELS=infrastructure.database=DEBUG,services=INFO
```

**Log Levels by Environment**:
- **Development**: `DEBUG` - See everything
- **Staging**: `INFO` - Normal operations
- **Production**: `WARNING` - Only issues

**Module-Specific Logging**:
```bash
# Enable debug logging for specific modules
LOG_MODULE_LEVELS=infrastructure.database=DEBUG,services.fir_service=INFO
```

---

### 3. Database Configuration

```bash
DB_HOST=localhost
DB_PORT=3306
DB_USER=afirgen_user
DB_PASSWORD=secure_password
DB_NAME=afirgen
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

**Connection Pool Sizing**:
- **Development**: 5-10 connections
- **Staging**: 20 connections
- **Production**: 30-50 connections (adjust based on load)

**Formula**: `pool_size = (2 * num_cores) + effective_spindle_count`

**SSL Configuration** (Production):
```bash
DB_SSL_ENABLED=true
DB_SSL_CA=/etc/ssl/certs/rds-ca-bundle.pem
```

---

### 4. Redis Cache Configuration

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5
```

**Connection Limits**:
- **Development**: 20 connections
- **Staging**: 50 connections
- **Production**: 100+ connections

**SSL Configuration** (Production):
```bash
REDIS_SSL_ENABLED=true
```

---

### 5. Celery Configuration

```bash
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
```

**Worker Concurrency**:
- **Development**: 2 workers
- **Staging**: 4 workers
- **Production**: 8+ workers (based on CPU cores)

**With SSL** (Production):
```bash
CELERY_BROKER_URL=rediss://:password@redis-host:6379/1
CELERY_RESULT_BACKEND=rediss://:password@redis-host:6379/2
```

---

### 6. Model Servers Configuration

```bash
MODEL_SERVER_URL=http://localhost:8001
ASR_OCR_SERVER_URL=http://localhost:8002
MODEL_SERVER_TIMEOUT=120
MODEL_SERVER_MAX_RETRIES=3
```

**Timeout Guidelines**:
- **LLM Server**: 120-180 seconds
- **ASR/OCR Server**: 60-120 seconds

---

### 7. API Configuration

```bash
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_RELOAD=false  # true only for development
API_KEY=your-api-key
```

**Worker Count**:
- Formula: `(2 * num_cores) + 1`
- **Development**: 1 worker (easier debugging)
- **Production**: 8+ workers

---

### 8. Rate Limiting

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
```

**Recommended Limits**:
- **Development**: Disabled or 1000/min
- **Staging**: 100/min
- **Production**: 100/min (adjust based on usage patterns)

---

### 9. CORS Configuration

```bash
CORS_ENABLED=true
CORS_ORIGINS=https://app.example.com,https://admin.example.com
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=*
```

**Security**:
- **Development**: `CORS_ORIGINS=*` (allow all)
- **Production**: Specific domains only

---

### 10. Security Configuration

```bash
ALLOWED_HOSTS=api.example.com,example.com
SECRET_KEY=your-secret-key-here
REQUIRE_HTTPS=true
```

**Generating Secure Keys**:
```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate API_KEY
openssl rand -base64 32
```

**HSTS Configuration** (Production):
```bash
HSTS_ENABLED=true
HSTS_MAX_AGE=31536000
HSTS_INCLUDE_SUBDOMAINS=true
HSTS_PRELOAD=true
```

---

### 11. Monitoring Configuration

```bash
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
PROMETHEUS_METRICS_PATH=/metrics
```

**CloudWatch** (AWS):
```bash
CLOUDWATCH_ENABLED=true
CLOUDWATCH_NAMESPACE=AFIRGen/Backend
CLOUDWATCH_REGION=us-east-1
```

---

### 12. Tracing Configuration

```bash
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=afirgen-backend
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1
```

**Sampling Rates**:
- **Development**: 1.0 (100% - trace everything)
- **Staging**: 0.1 (10%)
- **Production**: 0.01 (1%)

---

### 13. Cache TTL Configuration

```bash
CACHE_TTL_FIR_RECORD=3600      # 1 hour
CACHE_TTL_SESSION=86400        # 24 hours
CACHE_TTL_KB_QUERY=7200        # 2 hours
CACHE_TTL_VIOLATION_CHECK=1800 # 30 minutes
CACHE_TTL_STATS=300            # 5 minutes
```

**Tuning Guidelines**:
- Longer TTL = Better performance, stale data risk
- Shorter TTL = Fresher data, more database load
- Monitor cache hit rates to optimize

---

### 14. Retry & Circuit Breaker Configuration

```bash
# Retry Configuration
RETRY_MAX_ATTEMPTS=3
RETRY_BASE_DELAY=1.0
RETRY_MAX_DELAY=60.0
RETRY_EXPONENTIAL_BASE=2.0
RETRY_JITTER=true

# Circuit Breaker Configuration
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS=3
```

---

## Secrets Management

### Development

Store secrets in `.env` file (not committed to git):

```bash
# .env
DB_PASSWORD=dev_password
API_KEY=dev-api-key
```

### Production

**Option 1: Environment Variables**
```bash
export DB_PASSWORD="$(aws secretsmanager get-secret-value --secret-id prod/db/password --query SecretString --output text)"
export API_KEY="$(aws secretsmanager get-secret-value --secret-id prod/api/key --query SecretString --output text)"
```

**Option 2: AWS Secrets Manager**
```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

secrets = get_secret('prod/afirgen/config')
```

**Option 3: HashiCorp Vault**
```bash
vault kv get -field=db_password secret/afirgen/prod
```

---

## Environment-Specific Configurations

### Development

**Focus**: Easy debugging, fast iteration

```bash
DEBUG=true
LOG_LEVEL=DEBUG
API_WORKERS=1
API_RELOAD=true
RATE_LIMIT_ENABLED=false
CORS_ORIGINS=*
OTEL_ENABLED=false
```

### Staging

**Focus**: Production-like testing

```bash
DEBUG=false
LOG_LEVEL=INFO
API_WORKERS=4
API_RELOAD=false
RATE_LIMIT_ENABLED=true
CORS_ORIGINS=https://staging.example.com
OTEL_ENABLED=true
OTEL_TRACES_SAMPLER_ARG=0.1
```

### Production

**Focus**: Performance, security, reliability

```bash
DEBUG=false
LOG_LEVEL=WARNING
API_WORKERS=8
API_RELOAD=false
RATE_LIMIT_ENABLED=true
CORS_ORIGINS=https://app.example.com
REQUIRE_HTTPS=true
OTEL_ENABLED=true
OTEL_TRACES_SAMPLER_ARG=0.01
DB_SSL_ENABLED=true
REDIS_SSL_ENABLED=true
```

---

## Validation

### Check Configuration

```python
# config_validator.py
import os
from typing import List, Tuple

def validate_config() -> List[Tuple[str, str]]:
    """Validate required configuration variables."""
    errors = []
    
    required_vars = [
        'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME',
        'REDIS_HOST', 'API_KEY', 'SECRET_KEY'
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            errors.append((var, 'Missing required variable'))
    
    # Validate SECRET_KEY strength
    secret_key = os.getenv('SECRET_KEY', '')
    if len(secret_key) < 32:
        errors.append(('SECRET_KEY', 'Must be at least 32 characters'))
    
    # Validate production settings
    if os.getenv('ENVIRONMENT') == 'production':
        if os.getenv('DEBUG', 'false').lower() == 'true':
            errors.append(('DEBUG', 'Must be false in production'))
        
        if not os.getenv('REQUIRE_HTTPS', 'false').lower() == 'true':
            errors.append(('REQUIRE_HTTPS', 'Must be true in production'))
    
    return errors

if __name__ == '__main__':
    errors = validate_config()
    if errors:
        print("Configuration errors:")
        for var, msg in errors:
            print(f"  {var}: {msg}")
        exit(1)
    else:
        print("Configuration valid!")
```

Run validation:
```bash
python config_validator.py
```

---

## Troubleshooting

### Configuration Not Loading

**Issue**: Environment variables not being read

**Solutions**:
1. Check `.env` file exists in correct location
2. Verify no syntax errors in `.env`
3. Ensure no spaces around `=` in `.env`
4. Check file permissions: `chmod 600 .env`

### Database Connection Fails

**Issue**: Can't connect to database

**Check**:
```bash
# Test connection
mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "SELECT 1;"

# Verify environment variables
echo $DB_HOST
echo $DB_USER
echo $DB_NAME
```

### Redis Connection Fails

**Issue**: Can't connect to Redis

**Check**:
```bash
# Test connection
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping

# Verify environment variables
echo $REDIS_HOST
echo $REDIS_PORT
```

---

## Best Practices

1. **Never Commit Secrets**: Add `.env` to `.gitignore`
2. **Use Strong Keys**: Generate with `openssl rand -hex 32`
3. **Rotate Secrets**: Change passwords every 90 days
4. **Validate on Startup**: Check required variables exist
5. **Document Changes**: Update this guide when adding variables
6. **Use Secrets Manager**: For production deployments
7. **Separate Environments**: Different credentials per environment
8. **Monitor Configuration**: Alert on missing/invalid values
9. **Backup Configuration**: Store encrypted backups
10. **Audit Access**: Log who accesses secrets

---

## Reference

### Complete Variable List

See `.env.optimization.example` for complete list with descriptions.

### External Documentation

- [FastAPI Configuration](https://fastapi.tiangolo.com/advanced/settings/)
- [Celery Configuration](https://docs.celeryq.dev/en/stable/userguide/configuration.html)
- [Redis Configuration](https://redis.io/docs/management/config/)
- [MySQL Configuration](https://dev.mysql.com/doc/refman/8.0/en/server-system-variables.html)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
