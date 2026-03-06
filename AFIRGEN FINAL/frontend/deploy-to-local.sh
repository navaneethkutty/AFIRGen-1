#!/bin/bash
# Script to switch frontend configuration back to local development

set -e

echo "Switching frontend to local development configuration..."

# Restore backup if it exists
if [ -f "js/config.js.backup" ]; then
  cp js/config.js.backup js/config.js
  echo "Restored config from backup"
else
  # Create default local config
  cat > js/config.js << 'EOF'
// Frontend Configuration
// This file can be generated dynamically during deployment with environment-specific values

window.ENV = {
  // API Base URL - Local development
  API_BASE_URL: 'http://localhost:8000',

  // API key for local development
  API_KEY: '',

  // Environment name
  ENVIRONMENT: 'development',

  // Feature flags
  ENABLE_DEBUG: true
};

// Override with environment-specific config if available
if (typeof window.ENV_OVERRIDE !== 'undefined') {
  window.ENV = { ...window.ENV, ...window.ENV_OVERRIDE };
}
EOF
  echo "Created default local development config"
fi

echo "Frontend configuration updated for local development"
echo "API Base URL: http://localhost:8000"
