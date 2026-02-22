# Multi-stage build for AFIRGen Frontend
# Stage 1: Build the application
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source files
COPY . .

# Build production bundle
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Build arguments for configuration
ARG API_BASE_URL=http://localhost:8000
ARG API_KEY=
ARG ENVIRONMENT=production
ARG ENABLE_DEBUG=false

# Copy built files from builder stage
COPY --from=builder /app/dist/ /usr/share/nginx/html/

# Copy additional assets if not in dist
COPY --from=builder /app/manifest.json /usr/share/nginx/html/
COPY --from=builder /app/sw.js /usr/share/nginx/html/
COPY --from=builder /app/assets/ /usr/share/nginx/html/assets/

# Configure API URL at build time if config.js exists
RUN if [ -f /usr/share/nginx/html/js/config.js ]; then \
    sed -i "s|API_BASE_URL: '[^']*'|API_BASE_URL: '${API_BASE_URL}'|g" /usr/share/nginx/html/js/config.js && \
    sed -i "s|API_KEY: '[^']*'|API_KEY: '${API_KEY}'|g" /usr/share/nginx/html/js/config.js && \
    sed -i "s|ENVIRONMENT: '[^']*'|ENVIRONMENT: '${ENVIRONMENT}'|g" /usr/share/nginx/html/js/config.js && \
    sed -i "s|ENABLE_DEBUG: [^,]*,|ENABLE_DEBUG: ${ENABLE_DEBUG},|g" /usr/share/nginx/html/js/config.js; \
    fi

# Add custom nginx configuration for SPA routing and optimization
RUN echo 'server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    \
    # Security headers \
    add_header X-Frame-Options "SAMEORIGIN" always; \
    add_header X-Content-Type-Options "nosniff" always; \
    add_header X-XSS-Protection "1; mode=block" always; \
    add_header Referrer-Policy "strict-origin-when-cross-origin" always; \
    add_header Content-Security-Policy "default-src '\''self'\''; script-src '\''self'\'' '\''unsafe-inline'\''; style-src '\''self'\'' '\''unsafe-inline'\'' https://fonts.googleapis.com; font-src '\''self'\'' https://fonts.gstatic.com; connect-src '\''self'\'' http://localhost:8000 https://*; img-src '\''self'\'' data: blob:; frame-ancestors '\''none'\''; base-uri '\''self'\''; form-action '\''self'\'';" always; \
    \
    # Gzip compression \
    gzip on; \
    gzip_vary on; \
    gzip_comp_level 6; \
    gzip_min_length 1000; \
    gzip_proxied any; \
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml font/truetype font/opentype application/vnd.ms-fontobject image/svg+xml; \
    gzip_disable "msie6"; \
    \
    # Cache static assets (1 year) \
    location ~* \.(css|js|jpg|jpeg|png|gif|ico|svg|woff|woff2|ttf|eot|webp)$ { \
        expires 1y; \
        add_header Cache-Control "public, immutable"; \
        access_log off; \
    } \
    \
    # Cache service worker (short cache) \
    location = /sw.js { \
        expires 1h; \
        add_header Cache-Control "public, max-age=3600"; \
    } \
    \
    # Cache manifest \
    location = /manifest.json { \
        expires 1d; \
        add_header Cache-Control "public, max-age=86400"; \
    } \
    \
    # No cache for HTML \
    location ~* \.html$ { \
        expires -1; \
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0"; \
    } \
    \
    # SPA fallback \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
