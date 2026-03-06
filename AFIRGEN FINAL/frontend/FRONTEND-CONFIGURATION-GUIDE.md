# Frontend Configuration Guide

This guide explains how to configure the AFIRGen frontend to connect to different backend environments (local development vs EC2 production).

## Overview

The frontend uses a configuration file (`js/config.js`) to determine which backend API to connect to. The configuration supports:
- Local development (http://localhost:8000)
- EC2 production (http://98.86.30.145:8000)
- Custom backend URLs

## Configuration Files

### 1. `js/config.js` (Active Configuration)
This is the active configuration file used by the frontend. By default, it points to localhost for local development.

### 2. `js/config.production.js` (Production Template)
This is a template configuration for EC2 production deployment. It points to http://98.86.30.145:8000.

## Switching Between Environments

### Method 1: Using Deployment Scripts (Recommended)

#### Switch to EC2 Production:
```bash
cd "AFIRGEN FINAL/frontend"
chmod +x deploy-to-ec2.sh
./deploy-to-ec2.sh
```

This script will:
- Backup your current config
- Copy the production configuration
- Set the API URL to http://98.86.30.145:8000

#### Switch to Local Development:
```bash
cd "AFIRGEN FINAL/frontend"
chmod +x deploy-to-local.sh
./deploy-to-local.sh
```

This script will:
- Restore your local development configuration
- Set the API URL to http://localhost:8000

### Method 2: Manual Configuration

Edit `js/config.js` and change the `API_BASE_URL`:

For local development:
```javascript
window.ENV = {
  API_BASE_URL: 'http://localhost:8000',
  API_KEY: '',
  ENVIRONMENT: 'development',
  ENABLE_DEBUG: true
};
```

For EC2 production:
```javascript
window.ENV = {
  API_BASE_URL: 'http://98.86.30.145:8000',
  API_KEY: '',
  ENVIRONMENT: 'production',
  ENABLE_DEBUG: false
};
```

### Method 3: Runtime Override

You can override the configuration at runtime by setting `window.ENV_OVERRIDE` before loading the application:

```html
<script>
  window.ENV_OVERRIDE = {
    API_BASE_URL: 'http://custom-backend:8000'
  };
</script>
<script src="js/config.js"></script>
```

## API Authentication

The frontend sends an `X-API-Key` header with all API requests (except `/health`).

### Setting the API Key

#### For Local Development:
The API key can be left empty for local testing, or set in `js/config.js`:
```javascript
API_KEY: 'your-local-api-key'
```

#### For Production:
Set the API key via environment variable before deployment:
```bash
export API_KEY='your-production-api-key'
./deploy-to-ec2.sh
```

The deployment script will automatically inject the API key into the configuration.

**IMPORTANT:** Never hardcode production API keys in the configuration files that are committed to version control.

## Testing Backend Connectivity

Use the connectivity test page to verify the frontend can reach the backend:

1. Open `test-backend-connectivity.html` in your browser
2. Select the environment (Localhost or EC2)
3. Click "Test /health Endpoint" to verify connectivity
4. Click "Test All Endpoints" to test multiple endpoints

## API Endpoints

The frontend uses these backend endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (no auth required) |
| `/process` | POST | Start FIR generation |
| `/validate` | POST | Validate step content |
| `/regenerate/{sessionId}` | POST | Regenerate step content |
| `/session/{sessionId}/status` | GET | Get session status |
| `/fir/{firNumber}` | GET | Get FIR by number |

All endpoints except `/health` require the `X-API-Key` header.

## Troubleshooting

### CORS Errors
If you see CORS errors in the browser console:
1. Verify the backend is running
2. Check that CORS middleware is enabled in the backend
3. Ensure the backend allows requests from your frontend origin

### Connection Refused
If you see "Connection refused" errors:
1. Verify the backend is running on the correct port
2. Check the API_BASE_URL in `js/config.js`
3. For EC2: Verify security groups allow inbound traffic on port 8000

### 401 Unauthorized
If you see 401 errors:
1. Verify the API_KEY is set correctly in `js/config.js`
2. Check that the API key matches the backend configuration
3. Ensure the `X-API-Key` header is being sent with requests

### Network Timeout
If requests timeout:
1. Check your network connection
2. Verify the backend is responsive (test with curl)
3. Increase timeout values in `js/api.js` if needed

## Deployment Checklist

### Local Development
- [ ] Backend running on http://localhost:8000
- [ ] Frontend config points to localhost
- [ ] API key matches backend (or empty for testing)
- [ ] Test connectivity with test-backend-connectivity.html

### EC2 Production
- [ ] Backend running on EC2 (98.86.30.145:8000)
- [ ] Run `./deploy-to-ec2.sh` to switch configuration
- [ ] Set production API key via environment variable
- [ ] Test connectivity with test-backend-connectivity.html
- [ ] Verify all endpoints work correctly
- [ ] Check browser console for errors

## Environment Variables

The frontend configuration supports these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `API_BASE_URL` | Backend API base URL | http://localhost:8000 |
| `API_KEY` | API authentication key | (empty) |
| `ENVIRONMENT` | Environment name | development |
| `ENABLE_DEBUG` | Enable debug logging | true |

## Security Notes

1. **Never commit API keys** to version control
2. **Use HTTPS in production** (update API_BASE_URL to https://)
3. **Rotate API keys regularly** in production
4. **Use environment-specific keys** (different keys for dev/staging/prod)
5. **Monitor API usage** to detect unauthorized access

## Additional Resources

- Backend README: `../main backend/README.md`
- API Documentation: See backend OpenAPI docs at `/docs`
- Deployment Guide: `../main backend/README.md#deployment`
