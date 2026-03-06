// Production Configuration for EC2 Deployment
// This file should be used when deploying to EC2 (98.86.30.145)
//
// DEPLOYMENT INSTRUCTIONS:
// 1. Copy this file to config.js before deploying to EC2
// 2. Or use a deployment script to switch configurations
//
// Example deployment command:
//   cp js/config.production.js js/config.js

window.ENV = {
  // API Base URL for EC2 Production
  API_BASE_URL: 'http://98.86.30.145:8000',

  // API key should be set via environment variable or deployment script
  // Set this to match the API_KEY configured in the backend .env file
  // Example: export API_KEY='your-api-key-here' before deployment
  API_KEY: '',

  // Environment name
  ENVIRONMENT: 'production',

  // Feature flags
  ENABLE_DEBUG: false
};

// Override with environment-specific config if available
if (typeof window.ENV_OVERRIDE !== 'undefined') {
  window.ENV = { ...window.ENV, ...window.ENV_OVERRIDE };
}
