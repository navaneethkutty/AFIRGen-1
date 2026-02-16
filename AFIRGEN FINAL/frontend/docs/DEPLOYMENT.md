# AFIRGen Frontend Deployment Guide

Complete guide for deploying the AFIRGen frontend to various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Docker Deployment](#docker-deployment)
3. [Manual Deployment](#manual-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Production Checklist](#production-checklist)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- Docker 20.10+ and Docker Compose 2.0+ (for Docker deployment)
- Node.js 18+ and npm 8+ (for manual deployment)
- nginx 1.20+ or Apache 2.4+ (for manual deployment)

### Required Access
- Server with root/sudo access
- Domain name (for production)
- SSL certificate (for HTTPS)

---

## Docker Deployment

### Quick Start

1. **Clone the repository**:
```bash
git clone <repository-url>
cd AFIRGEN\ FINAL/frontend
```

2. **Create environment file**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Build and run**:
```bash
docker-compose up -d
```

The application will be available at `http://localhost:80`

### Docker Build Options

#### Build with custom API URL:
```bash
docker build \
  --build-arg API_BASE_URL=https://api.afirgen.com \
  --build-arg ENVIRONMENT=production \
  -t afirgen-frontend:latest .
```

#### Run container:
```bash
docker run -d \
  --name afirgen-frontend \
  -p 80:80 \
  afirgen-frontend:latest
```

#### Using Docker Compose:
```bash
# Development
docker-compose up -d

# Production with custom settings
API_BASE_URL=https://api.afirgen.com \
ENVIRONMENT=production \
docker-compose up -d
```

### Docker Commands

```bash
# View logs
docker-compose logs -f frontend

# Restart service
docker-compose restart frontend

# Stop service
docker-compose stop frontend

# Remove containers
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

---

## Manual Deployment

### Step 1: Build Production Bundle

```bash
# Install dependencies
npm ci --only=production

# Build for production
npm run build
```

This creates optimized files in the `dist/` directory.

### Step 2: Deploy to Web Server

#### Option A: nginx

1. **Copy files to web root**:
```bash
sudo cp -r dist/* /var/www/html/afirgen/
sudo cp manifest.json /var/www/html/afirgen/
sudo cp sw.js /var/www/html/afirgen/
sudo cp -r assets /var/www/html/afirgen/
```

2. **Create nginx configuration**:
```bash
sudo nano /etc/nginx/sites-available/afirgen
```

```nginx
server {
    listen 80;
    server_name afirgen.example.com;
    root /var/www/html/afirgen;
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://api.afirgen.com; img-src 'self' data: blob:;" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_comp_level 6;
    gzip_min_length 1000;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;

    # Cache static assets
    location ~* \.(css|js|jpg|jpeg|png|gif|ico|svg|woff|woff2|ttf|eot|webp)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Service worker
    location = /sw.js {
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
    }

    # No cache for HTML
    location ~* \.html$ {
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

3. **Enable site and restart nginx**:
```bash
sudo ln -s /etc/nginx/sites-available/afirgen /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Option B: Apache

1. **Copy files**:
```bash
sudo cp -r dist/* /var/www/html/afirgen/
```

2. **Create .htaccess**:
```apache
# Enable rewrite engine
RewriteEngine On

# SPA fallback
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^ index.html [L]

# Gzip compression
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/html text/plain text/xml text/css text/javascript application/javascript application/json
</IfModule>

# Cache control
<IfModule mod_expires.c>
    ExpiresActive On
    ExpiresByType text/css "access plus 1 year"
    ExpiresByType application/javascript "access plus 1 year"
    ExpiresByType image/jpeg "access plus 1 year"
    ExpiresByType image/png "access plus 1 year"
    ExpiresByType image/svg+xml "access plus 1 year"
    ExpiresByType text/html "access plus 0 seconds"
</IfModule>

# Security headers
<IfModule mod_headers.c>
    Header set X-Frame-Options "SAMEORIGIN"
    Header set X-Content-Type-Options "nosniff"
    Header set X-XSS-Protection "1; mode=block"
</IfModule>
```

3. **Restart Apache**:
```bash
sudo systemctl restart apache2
```

---

## Environment Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# API Configuration
API_BASE_URL=https://api.afirgen.com
API_KEY=your-api-key-here

# Environment
ENVIRONMENT=production
ENABLE_DEBUG=false

# Server Configuration
FRONTEND_PORT=80

# Optional: Analytics
ANALYTICS_ID=UA-XXXXXXXXX-X

# Optional: Error Tracking
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
```

### Build-time Configuration

Configure during Docker build:

```bash
docker build \
  --build-arg API_BASE_URL=https://api.afirgen.com \
  --build-arg ENVIRONMENT=production \
  --build-arg ENABLE_DEBUG=false \
  -t afirgen-frontend:latest .
```

### Runtime Configuration

For nginx, update config.js after deployment:

```bash
# Update API URL
sed -i "s|API_BASE_URL: '[^']*'|API_BASE_URL: 'https://api.afirgen.com'|g" /var/www/html/afirgen/js/config.js
```

---

## SSL/HTTPS Configuration

### Using Let's Encrypt (Certbot)

1. **Install Certbot**:
```bash
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx
```

2. **Obtain certificate**:
```bash
sudo certbot --nginx -d afirgen.example.com
```

3. **Auto-renewal**:
```bash
sudo certbot renew --dry-run
```

### Manual SSL Configuration

Update nginx configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name afirgen.example.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # ... rest of configuration
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name afirgen.example.com;
    return 301 https://$server_name$request_uri;
}
```

---

## Production Checklist

### Before Deployment

- [ ] Run production build: `npm run build`
- [ ] Verify bundle sizes: `npm run audit:performance`
- [ ] Run all tests: `npm test`
- [ ] Run E2E tests: `npm run test:e2e`
- [ ] Check for security vulnerabilities: `npm audit`
- [ ] Update environment variables
- [ ] Configure API endpoints
- [ ] Set up SSL certificates
- [ ] Configure domain DNS

### After Deployment

- [ ] Verify application loads correctly
- [ ] Test all critical user flows
- [ ] Check service worker registration
- [ ] Verify offline functionality
- [ ] Test on multiple browsers
- [ ] Test on mobile devices
- [ ] Monitor error logs
- [ ] Set up monitoring and alerts
- [ ] Configure backup strategy
- [ ] Document deployment process

---

## Monitoring and Maintenance

### Health Checks

The Docker container includes a health check:

```bash
# Check container health
docker ps

# View health check logs
docker inspect --format='{{json .State.Health}}' afirgen-frontend
```

### Log Monitoring

```bash
# Docker logs
docker-compose logs -f frontend

# nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Performance Monitoring

Set up monitoring tools:
- Google Analytics for user analytics
- Sentry for error tracking
- New Relic or Datadog for performance monitoring
- Uptime monitoring (Pingdom, UptimeRobot)

---

## Scaling and Load Balancing

### Horizontal Scaling

Deploy multiple instances behind a load balancer:

```yaml
# docker-compose.yml
version: '3.8'

services:
  frontend-1:
    build: .
    ports:
      - "8001:80"

  frontend-2:
    build: .
    ports:
      - "8002:80"

  frontend-3:
    build: .
    ports:
      - "8003:80"

  nginx-lb:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
    depends_on:
      - frontend-1
      - frontend-2
      - frontend-3
```

### CDN Integration

Use a CDN for static assets:
- CloudFlare
- AWS CloudFront
- Fastly
- Akamai

---

## Rollback Procedure

### Docker Rollback

```bash
# Tag current version
docker tag afirgen-frontend:latest afirgen-frontend:backup

# Pull previous version
docker pull afirgen-frontend:previous

# Restart with previous version
docker-compose down
docker-compose up -d
```

### Manual Rollback

```bash
# Restore from backup
sudo cp -r /var/www/html/afirgen.backup/* /var/www/html/afirgen/
sudo systemctl restart nginx
```

---

## Troubleshooting

### Application Won't Start

**Check Docker logs**:
```bash
docker-compose logs frontend
```

**Common issues**:
- Port already in use: Change `FRONTEND_PORT` in .env
- Build failed: Check Node.js version and dependencies
- Permission denied: Run with sudo or fix file permissions

### 502 Bad Gateway

**Causes**:
- Backend API not accessible
- Incorrect API_BASE_URL configuration
- nginx misconfiguration

**Solutions**:
```bash
# Check nginx configuration
sudo nginx -t

# Verify API connectivity
curl https://api.afirgen.com/health

# Check nginx error logs
sudo tail -f /var/log/nginx/error.log
```

### Service Worker Issues

**Clear service worker**:
```javascript
// In browser console
navigator.serviceWorker.getRegistrations().then(registrations => {
  registrations.forEach(registration => registration.unregister());
});
```

### Performance Issues

**Check**:
- Gzip compression enabled
- Static assets cached properly
- CDN configured correctly
- Server resources (CPU, memory)

**Optimize**:
```bash
# Enable nginx caching
sudo nano /etc/nginx/nginx.conf
# Add: proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m;
```

---

## Security Best Practices

1. **Always use HTTPS in production**
2. **Keep dependencies updated**: `npm audit fix`
3. **Configure CSP headers** properly
4. **Enable rate limiting** on nginx
5. **Regular security audits**
6. **Monitor for suspicious activity**
7. **Implement proper authentication**
8. **Use environment variables** for secrets
9. **Regular backups**
10. **Disaster recovery plan**

---

## Support

For deployment issues:
1. Check this documentation
2. Review application logs
3. Check nginx/Apache logs
4. Verify environment configuration
5. Contact DevOps team

---

## Additional Resources

- [nginx Documentation](https://nginx.org/en/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Let's Encrypt](https://letsencrypt.org/)
- [AFIRGen README](../README.md)
- [AFIRGen API Documentation](./API.md)
