"""
Unit Test for Task 8.1 - API Key Authentication Middleware

**Validates: Requirements 15.10**

This test verifies that the centralized API key authentication middleware:
1. Verifies X-API-Key header matches configured API_KEY
2. Excludes /health endpoint from authentication
3. Returns HTTP 401 for invalid or missing API key
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Mock external dependencies before importing
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['mysql.connector.pooling'] = MagicMock()
sys.modules['boto3'] = MagicMock()


@pytest.fixture
def test_client():
    """Create a test client with mocked dependencies."""
    
    # Set test environment variables
    os.environ['API_KEY'] = 'test-api-key-123'
    os.environ['AWS_REGION'] = 'us-east-1'
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_PASSWORD'] = 'test-password'
    
    # Mock AWS clients
    with patch('agentv5_clean.boto3') as mock_boto3:
        mock_boto3.client.return_value = MagicMock()
        
        # Mock MySQL connection pool
        with patch('agentv5_clean.mysql.connector.pooling.MySQLConnectionPool') as mock_pool:
            mock_pool.return_value = MagicMock()
            
            # Mock SQLite connection
            with patch('agentv5_clean.sqlite3.connect') as mock_sqlite:
                mock_sqlite.return_value = MagicMock()
                
                # Import the app after patching
                from agentv5_clean import app
                
                # Create test client
                client = TestClient(app)
                
                yield client


def test_health_endpoint_without_api_key(test_client):
    """
    Test that /health endpoint works without API key.
    
    **Validates: Requirement 15.10 (exclusion of /health from authentication)**
    """
    print("\n=== Testing /health endpoint without API key ===")
    
    response = test_client.get("/health")
    
    # Health endpoint should work without API key
    assert response.status_code == 200, \
        f"/health should be accessible without API key. Got: {response.status_code}"
    
    print("✓ /health endpoint accessible without API key")


def test_protected_endpoint_without_api_key(test_client):
    """
    Test that protected endpoints require API key.
    
    **Validates: Requirement 15.10 (authentication required for non-health endpoints)**
    """
    print("\n=== Testing protected endpoint without API key ===")
    
    # Try to access /session endpoint without API key
    response = test_client.get("/session/test-session-id")
    
    # Should return 401 Unauthorized
    assert response.status_code == 401, \
        f"Protected endpoint should return 401 without API key. Got: {response.status_code}"
    
    # Check error message
    response_data = response.json()
    assert "error" in response_data, "Response should include error field"
    assert "Authentication failed" in response_data["error"], \
        f"Error should mention authentication failure. Got: {response_data['error']}"
    
    print("✓ Protected endpoint returns 401 without API key")


def test_protected_endpoint_with_invalid_api_key(test_client):
    """
    Test that protected endpoints reject invalid API key.
    
    **Validates: Requirement 15.10 (invalid API key rejection)**
    """
    print("\n=== Testing protected endpoint with invalid API key ===")
    
    # Try to access /session endpoint with invalid API key
    response = test_client.get(
        "/session/test-session-id",
        headers={"x-api-key": "invalid-key-999"}
    )
    
    # Should return 401 Unauthorized
    assert response.status_code == 401, \
        f"Protected endpoint should return 401 with invalid API key. Got: {response.status_code}"
    
    # Check error message
    response_data = response.json()
    assert "error" in response_data, "Response should include error field"
    assert "Authentication failed" in response_data["error"], \
        f"Error should mention authentication failure. Got: {response_data['error']}"
    
    print("✓ Protected endpoint returns 401 with invalid API key")


def test_protected_endpoint_with_valid_api_key(test_client):
    """
    Test that protected endpoints work with valid API key.
    
    **Validates: Requirement 15.10 (valid API key acceptance)**
    """
    print("\n=== Testing protected endpoint with valid API key ===")
    
    # Mock the database manager to return a session
    with patch('agentv5_clean.db_manager') as mock_db:
        mock_db.get_session.return_value = {
            'session_id': 'test-session-id',
            'status': 'processing',
            'transcript': None,
            'summary': None,
            'violations': None,
            'fir_content': None,
            'fir_number': None,
            'error': None
        }
        
        # Try to access /session endpoint with valid API key
        response = test_client.get(
            "/session/test-session-id",
            headers={"x-api-key": "test-api-key-123"}
        )
        
        # Should return 200 OK (or 404 if session not found, but not 401)
        assert response.status_code in [200, 404], \
            f"Protected endpoint should not return 401 with valid API key. Got: {response.status_code}"
        
        # If we got 404, it's because the session doesn't exist, not because of auth
        if response.status_code == 404:
            print("✓ Protected endpoint passed authentication (returned 404 for missing session)")
        else:
            print("✓ Protected endpoint works with valid API key")


def test_multiple_endpoints_require_authentication(test_client):
    """
    Test that multiple endpoints require authentication.
    
    **Validates: Requirement 15.10 (all endpoints except /health require authentication)**
    """
    print("\n=== Testing multiple endpoints require authentication ===")
    
    endpoints = [
        ("GET", "/session/test-id"),
        ("GET", "/fir/test-fir"),
        ("GET", "/firs"),
    ]
    
    for method, path in endpoints:
        if method == "GET":
            response = test_client.get(path)
        elif method == "POST":
            response = test_client.post(path, json={})
        
        assert response.status_code == 401, \
            f"{method} {path} should return 401 without API key. Got: {response.status_code}"
        
        print(f"✓ {method} {path} requires authentication")


def test_health_endpoint_ignores_api_key(test_client):
    """
    Test that /health endpoint works even with invalid API key.
    
    **Validates: Requirement 15.10 (health endpoint exclusion)**
    """
    print("\n=== Testing /health endpoint ignores API key ===")
    
    # Test with invalid API key
    response = test_client.get(
        "/health",
        headers={"x-api-key": "invalid-key"}
    )
    
    assert response.status_code == 200, \
        f"/health should work even with invalid API key. Got: {response.status_code}"
    
    print("✓ /health endpoint works with invalid API key")
    
    # Test with valid API key
    response = test_client.get(
        "/health",
        headers={"x-api-key": "test-api-key-123"}
    )
    
    assert response.status_code == 200, \
        f"/health should work with valid API key. Got: {response.status_code}"
    
    print("✓ /health endpoint works with valid API key")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
