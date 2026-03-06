#!/bin/bash
# Deployment script for EC2 (98.86.30.145)
# This script switches the frontend configuration to use the EC2 backend

set -e

echo "Deploying frontend to EC2..."

# Backup current config
if [ -f "js/config.js" ]; then
  cp js/config.js js/config.js.backup
  echo "Backed up current config to js/config.js.backup"
fi

# Copy production config
cp js/config.production.js js/config.js
echo "Switched to production configuration (EC2: http://98.86.30.145:8000)"

# Optional: Set API key if provided as environment variable
if [ -n "$API_KEY" ]; then
  sed -i "s|API_KEY: ''|API_KEY: '$API_KEY'|g" js/config.js
  echo "API key configured"
fi

echo "Frontend configuration updated for EC2 deployment"
echo "API Base URL: http://98.86.30.145:8000"
