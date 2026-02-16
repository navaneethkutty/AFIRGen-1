#!/bin/bash

###############################################################################
# AFIRGen Frontend - Production Deployment Script
# 
# This script automates the deployment of the frontend to production
# 
# IMPORTANT: This script requires approval and should only be run after
# successful staging deployment and testing
# 
# Usage: ./scripts/deploy-production.sh
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PRODUCTION_SERVER="${PRODUCTION_SERVER:-afirgen.com}"
PRODUCTION_USER="${PRODUCTION_USER:-deploy}"
PRODUCTION_PATH="${PRODUCTION_PATH:-/var/www/afirgen}"
API_BASE_URL="${API_BASE_URL:-https://api.afirgen.com}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-registry.afirgen.com}"
IMAGE_NAME="afirgen-frontend"
VERSION=$(cat package.json | grep version | head -1 | awk -F: '{ print $2 }' | sed 's/[",]//g' | tr -d '[[:space:]]')
IMAGE_TAG="v$VERSION-$(date +%Y%m%d-%H%M%S)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AFIRGen Frontend - Production Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${RED}⚠️  WARNING: This will deploy to PRODUCTION${NC}"
echo ""
echo "Version: $VERSION"
echo "Server: $PRODUCTION_SERVER"
echo "API: $API_BASE_URL"
echo ""
read -p "Are you sure you want to continue? (yes/no) " -r
echo
if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "Deployment cancelled"
    exit 1
fi

# Step 1: Pre-deployment checks
echo -e "${YELLOW}Step 1: Running pre-deployment checks...${NC}"

# Check if we're on the main/master branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ] && [ "$CURRENT_BRANCH" != "master" ]; then
    echo -e "${RED}Error: Must be on main/master branch for production deployment${NC}"
    echo "Current branch: $CURRENT_BRANCH"
    exit 1
fi

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo -e "${RED}Error: You have uncommitted changes${NC}"
    git status -s
    exit 1
fi

# Verify staging deployment was successful
echo "Verifying staging deployment..."
STAGING_URL="https://staging.afirgen.com"
STAGING_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$STAGING_URL" || echo "000")

if [ "$STAGING_STATUS" != "200" ]; then
    echo -e "${RED}Error: Staging deployment not accessible (HTTP $STAGING_STATUS)${NC}"
    echo "Please verify staging deployment before proceeding to production"
    exit 1
fi

# Check if all required tools are installed
for cmd in node npm docker git; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Error: $cmd is not installed${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✓ Pre-deployment checks passed${NC}"
echo ""

# Step 2: Create git tag
echo -e "${YELLOW}Step 2: Creating git tag...${NC}"

GIT_TAG="v$VERSION"
if git rev-parse "$GIT_TAG" >/dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Tag $GIT_TAG already exists${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    git tag -a "$GIT_TAG" -m "Production release $VERSION"
    git push origin "$GIT_TAG"
    echo -e "${GREEN}✓ Created and pushed tag: $GIT_TAG${NC}"
fi

echo ""

# Step 3: Run comprehensive tests
echo -e "${YELLOW}Step 3: Running comprehensive tests...${NC}"

# Run linting
echo "Running ESLint..."
npm run lint || {
    echo -e "${RED}Error: Linting failed${NC}"
    echo "Fix linting errors before deploying to production"
    exit 1
}

# Run unit tests
echo "Running unit tests..."
npm test -- --passWithNoTests || {
    echo -e "${YELLOW}Warning: Some tests failed${NC}"
    read -p "Continue despite test failures? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
}

# Run E2E tests
if [ -f "playwright.config.js" ]; then
    echo "Running E2E tests..."
    npm run test:e2e || {
        echo -e "${RED}Error: E2E tests failed${NC}"
        exit 1
    }
fi

# Run accessibility audit
echo "Running accessibility audit..."
node scripts/accessibility-audit.js || {
    echo -e "${YELLOW}Warning: Accessibility audit had issues${NC}"
}

# Run performance audit
echo "Running performance audit..."
node scripts/performance-audit.js || {
    echo -e "${YELLOW}Warning: Performance audit had issues${NC}"
}

echo -e "${GREEN}✓ Tests completed${NC}"
echo ""

# Step 4: Build production bundle
echo -e "${YELLOW}Step 4: Building production bundle...${NC}"

# Clean previous build
rm -rf dist/

# Build for production
NODE_ENV=production npm run build || {
    echo -e "${RED}Error: Build failed${NC}"
    exit 1
}

# Verify build output
if [ ! -d "dist" ]; then
    echo -e "${RED}Error: dist/ directory not created${NC}"
    exit 1
fi

# Verify bundle sizes
echo "Verifying bundle sizes..."
TOTAL_SIZE=$(du -sb dist/ | awk '{print $1}')
GZIPPED_SIZE=$(tar -czf - dist/ | wc -c)

echo "Total size: $(numfmt --to=iec $TOTAL_SIZE)"
echo "Gzipped size: $(numfmt --to=iec $GZIPPED_SIZE)"

if [ $GZIPPED_SIZE -gt 524288000 ]; then  # 500MB
    echo -e "${RED}Error: Bundle size exceeds 500MB${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Production bundle built and verified${NC}"
echo ""

# Step 5: Build Docker image
echo -e "${YELLOW}Step 5: Building Docker image...${NC}"

docker build \
    --build-arg API_BASE_URL="$API_BASE_URL" \
    --build-arg ENVIRONMENT=production \
    --build-arg ENABLE_DEBUG=false \
    -t "$IMAGE_NAME:$IMAGE_TAG" \
    -t "$IMAGE_NAME:latest" \
    -t "$IMAGE_NAME:v$VERSION" \
    . || {
    echo -e "${RED}Error: Docker build failed${NC}"
    exit 1
}

echo -e "${GREEN}✓ Docker image built: $IMAGE_NAME:$IMAGE_TAG${NC}"
echo ""

# Step 6: Push to Docker registry
echo -e "${YELLOW}Step 6: Pushing to Docker registry...${NC}"

if [ -n "$DOCKER_REGISTRY" ]; then
    docker tag "$IMAGE_NAME:$IMAGE_TAG" "$DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
    docker tag "$IMAGE_NAME:$IMAGE_TAG" "$DOCKER_REGISTRY/$IMAGE_NAME:latest"
    docker tag "$IMAGE_NAME:$IMAGE_TAG" "$DOCKER_REGISTRY/$IMAGE_NAME:v$VERSION"
    
    docker push "$DOCKER_REGISTRY/$IMAGE_NAME:$IMAGE_TAG" || {
        echo -e "${RED}Error: Failed to push to registry${NC}"
        exit 1
    }
    
    docker push "$DOCKER_REGISTRY/$IMAGE_NAME:latest" || {
        echo -e "${RED}Error: Failed to push latest tag${NC}"
        exit 1
    }
    
    docker push "$DOCKER_REGISTRY/$IMAGE_NAME:v$VERSION" || {
        echo -e "${RED}Error: Failed to push version tag${NC}"
        exit 1
    }
    
    echo -e "${GREEN}✓ Images pushed to registry${NC}"
else
    echo -e "${YELLOW}Warning: DOCKER_REGISTRY not set, skipping push${NC}"
fi

echo ""

# Step 7: Final confirmation
echo -e "${RED}========================================${NC}"
echo -e "${RED}FINAL CONFIRMATION${NC}"
echo -e "${RED}========================================${NC}"
echo ""
echo "You are about to deploy to PRODUCTION:"
echo ""
echo "  Version:     $VERSION"
echo "  Image Tag:   $IMAGE_TAG"
echo "  Server:      $PRODUCTION_SERVER"
echo "  API:         $API_BASE_URL"
echo "  Git Commit:  $(git rev-parse --short HEAD)"
echo ""
read -p "Type 'DEPLOY' to confirm: " -r
echo
if [[ ! $REPLY == "DEPLOY" ]]; then
    echo "Deployment cancelled"
    exit 1
fi

# Step 8: Deploy to production server
echo -e "${YELLOW}Step 8: Deploying to production server...${NC}"

# Create deployment package
DEPLOY_PACKAGE="afirgen-frontend-prod-$VERSION-$(date +%Y%m%d-%H%M%S).tar.gz"
tar -czf "$DEPLOY_PACKAGE" \
    dist/ \
    Dockerfile \
    docker-compose.yml \
    manifest.json \
    sw.js \
    assets/ 2>/dev/null || true

echo "Created deployment package: $DEPLOY_PACKAGE"

# Upload to production server
if [ -n "$PRODUCTION_SERVER" ] && [ -n "$PRODUCTION_USER" ]; then
    echo "Uploading to $PRODUCTION_SERVER..."
    
    scp "$DEPLOY_PACKAGE" "$PRODUCTION_USER@$PRODUCTION_SERVER:/tmp/" || {
        echo -e "${RED}Error: Failed to upload package${NC}"
        exit 1
    }
    
    # Deploy on remote server with zero-downtime
    ssh "$PRODUCTION_USER@$PRODUCTION_SERVER" << EOF
        set -e
        cd /tmp
        
        # Backup current deployment
        BACKUP_DIR="${PRODUCTION_PATH}.backup-\$(date +%Y%m%d-%H%M%S)"
        if [ -d "$PRODUCTION_PATH" ]; then
            echo "Creating backup: \$BACKUP_DIR"
            sudo cp -r "$PRODUCTION_PATH" "\$BACKUP_DIR"
        fi
        
        # Extract new deployment to temporary location
        TEMP_DIR="/tmp/afirgen-deploy-\$(date +%Y%m%d-%H%M%S)"
        mkdir -p "\$TEMP_DIR"
        tar -xzf "$DEPLOY_PACKAGE" -C "\$TEMP_DIR"
        
        # Deploy with Docker Compose (zero-downtime)
        cd "\$TEMP_DIR"
        
        # Pull new image
        sudo docker-compose pull
        
        # Start new containers
        sudo docker-compose up -d --no-deps --build
        
        # Wait for health check
        echo "Waiting for health check..."
        sleep 10
        
        # Verify deployment
        if sudo docker ps | grep -q afirgen-frontend; then
            echo "New deployment is healthy"
            
            # Move to production path
            sudo rm -rf "$PRODUCTION_PATH"
            sudo mv "\$TEMP_DIR" "$PRODUCTION_PATH"
            
            # Remove old containers
            sudo docker system prune -f
            
            echo "Deployment completed successfully"
        else
            echo "Deployment failed health check, rolling back..."
            sudo docker-compose down
            
            # Restore backup
            if [ -d "\$BACKUP_DIR" ]; then
                cd "\$BACKUP_DIR"
                sudo docker-compose up -d
            fi
            
            exit 1
        fi
        
        # Clean up
        rm /tmp/"$DEPLOY_PACKAGE"
EOF
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Deployed to production server${NC}"
    else
        echo -e "${RED}Error: Deployment failed, rollback initiated${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Note: Manual deployment required${NC}"
    echo "Deployment package created: $DEPLOY_PACKAGE"
    echo "Upload this package to your production server"
fi

echo ""

# Step 9: Run smoke tests
echo -e "${YELLOW}Step 9: Running smoke tests...${NC}"

# Wait for service to be ready
echo "Waiting for service to be ready..."
sleep 15

# Test production URL
PRODUCTION_URL="https://$PRODUCTION_SERVER"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$PRODUCTION_URL" || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ Production site is accessible (HTTP $HTTP_STATUS)${NC}"
else
    echo -e "${RED}ERROR: Production site returned HTTP $HTTP_STATUS${NC}"
    echo "Immediate rollback may be required!"
    exit 1
fi

# Run comprehensive smoke tests
if [ -f "scripts/smoke-tests.sh" ]; then
    ./scripts/smoke-tests.sh "$PRODUCTION_URL" || {
        echo -e "${RED}ERROR: Smoke tests failed${NC}"
        echo "Immediate investigation required!"
        exit 1
    }
fi

echo ""

# Step 10: Monitor for errors
echo -e "${YELLOW}Step 10: Monitoring deployment...${NC}"

echo "Monitoring for 60 seconds..."
for i in {1..12}; do
    sleep 5
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$PRODUCTION_URL" || echo "000")
    if [ "$STATUS" != "200" ]; then
        echo -e "${RED}ERROR: Site became unavailable (HTTP $STATUS)${NC}"
        exit 1
    fi
    echo -n "."
done
echo ""

echo -e "${GREEN}✓ Deployment stable${NC}"
echo ""

# Step 11: Deployment summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}PRODUCTION DEPLOYMENT SUCCESSFUL${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Version:         $VERSION"
echo "Image Tag:       $IMAGE_TAG"
echo "Production URL:  $PRODUCTION_URL"
echo "API URL:         $API_BASE_URL"
echo "Deployed At:     $(date)"
echo "Git Commit:      $(git rev-parse --short HEAD)"
echo "Git Tag:         $GIT_TAG"
echo ""
echo -e "${GREEN}✓ Production deployment completed successfully!${NC}"
echo ""
echo "Post-deployment tasks:"
echo "1. Monitor application logs: docker-compose logs -f frontend"
echo "2. Monitor error rates and performance metrics"
echo "3. Verify all critical user flows"
echo "4. Announce deployment to stakeholders"
echo "5. Update deployment documentation"
echo "6. Monitor for 24 hours for any issues"
echo ""
echo "Rollback command (if needed):"
echo "  ssh $PRODUCTION_USER@$PRODUCTION_SERVER"
echo "  cd $PRODUCTION_PATH.backup-<timestamp>"
echo "  sudo docker-compose up -d"
echo ""

# Clean up local deployment package
rm -f "$DEPLOY_PACKAGE"

# Send deployment notification (if configured)
if [ -n "$SLACK_WEBHOOK" ]; then
    curl -X POST "$SLACK_WEBHOOK" \
        -H 'Content-Type: application/json' \
        -d "{\"text\":\"✅ AFIRGen Frontend v$VERSION deployed to production successfully\"}"
fi

exit 0
