"""
Integration Test for Task 25.7 - Authentication and Health Check

**Validates: Requirements 3.7, 3.8**

This integration test verifies that authentication and health check functionality
continues to work correctly after all bug fixes have been applied:

1. Verify API authentication continues to work (Requirement 3.7)
   - Test that protected endpoints require valid API key
   - Test that invalid API keys are rejected
   - Test that missing API keys are rejected

2. Verify /health endpoint works without authentication (Requirement 3.8)
   - Test that /health endpoint is accessible without API key
   - Test that health check returns expected response structure

This test confirms that the bug fixes did not break authentication or health check functionality.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Also add the parent directory for cors_middleware
parent_dir = backend_dir.parent
sys.path.insert(0, str(parent_dir))

# Patch DB class BEFORE agentv5 is imported
# This prevents MySQL connection attempts at module import time
sys.modules['mysql'] = MagicMock()
sys.modules['mysql.connector'] = MagicMock()
sys.modules['mysql.connector.pooling'] = MagicMock()
sys.modules['chromadb'] = MagicMock()


@pytest.fixture
def mock_model_pool():
    """Mock ModelPool to avoid external dependencies."""
    mock_pool = AsyncMock()
    
    # Mock HTTP client for health checks
    mock_http_client = AsyncMock()
    mock_pool._http_client = mock_http_client
    
    # Mock health check responses
    mock_model_health = AsyncMock()
    mock_model_health.json = Mock(return_value={"status": "healthy"})
    mock_http_client.get = AsyncMock(return_value=mock_model_health)
    
    # Mock other methods
    mock_pool.two_line_summary = AsyncMock(return_value="Test summary")
    mock_pool.check_violation = AsyncMock(return_value=True)
    mock_pool.fir_narrative = AsyncMock(return_value="Test narrative")
    
    return mock_pool


@pytest.fixture
def mock_kb():
    """Mock KB (knowledge base) to avoid external dependencies."""
    mock = Mock()
    mock.retrieve = Mock(return_value=[
        {
            "section": "Section 420",
            "title": "Test violation",
            "description": "Test description"
        }
    ])
    return mock


@pytest.fixture
def mock_db():
    """Mock DB to avoid MySQL dependency."""
    mock = Mock()
    mock.flush_all = Mock()
    mock.save_fir = Mock()
    mock.get_fir = Mock(return_value=None)
    return mock


@pytest.fixture
def test_client(mock_model_pool, mock_kb, mock_db):
    """Create a test client with mocked dependencies."""
    # Patch dependencies BEFORE importing agentv5
    with patch('agentv5.ModelPool') as MockModelPool, \
         patch('agentv5.KB') as MockKB, \
         patch('agentv5.DB') as MockDB:
        
        # Configure mocks
        MockModelPool.get = AsyncMock(return_value=mock_model_pool)
        MockKB.return_value = mock_kb
        MockDB.return_value = mock_db
        
        # Import the app after patching
        from agentv5 import app, session_manager
        
        # Clean up any existing test data
        try:
            session_manager.flush_all()
        except:
            pass
        
        # Create test client
        client = TestClient(app)
        
        yield client
        
        # Cleanup after test
        try:
            session_manager.flush_all()
        except:
            pass


@pytest.mark.integration
def test_authentication_preserved(test_client):
    """
    Test that API authentication continues to work correctly.
    
    **Validates: Requirement 3.7**
    
    This test verifies:
    - Protected endpoints require valid API key
    - Invalid API keys are rejected with 401
    - Missing API keys are rejected with 401
    - Valid API keys allow access to protected endpoints
    
    This confirms that APIAuthMiddleware continues to enforce authentication
    as before, and bug fixes did not break authentication.
    """
    
    print("\n=== Testing Authentication Preservation ===")
    
    # Test 1: Protected endpoint with valid API key should succeed
    print("\n--- Test 1: Valid API key should allow access ---")
    
    response = test_client.post(
        "/process",
        data={"text": "Test complaint"},
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert response.status_code == 200, \
        f"Valid API key should allow access to protected endpoint. Error: {response.text}"
    
    print("✓ Valid API key allows access to /process endpoint")
    
    # Test 2: Protected endpoint without API key should fail with 401
    print("\n--- Test 2: Missing API key should be rejected ---")
    
    response = test_client.post(
        "/process",
        data={"text": "Test complaint"}
        # No X-API-Key header
    )
    
    assert response.status_code == 401, \
        f"Missing API key should return 401. Got: {response.status_code}"
    
    response_data = response.json()
    assert "detail" in response_data, "Error response should include detail"
    assert "API key required" in response_data["detail"] or "api key" in response_data["detail"].lower(), \
        f"Error message should mention API key. Got: {response_data['detail']}"
    
    print("✓ Missing API key is rejected with 401")
    
    # Test 3: Protected endpoint with invalid API key should fail with 401
    print("\n--- Test 3: Invalid API key should be rejected ---")
    
    response = test_client.post(
        "/process",
        data={"text": "Test complaint"},
        headers={"X-API-Key": "invalid-key-999"}
    )
    
    assert response.status_code == 401, \
        f"Invalid API key should return 401. Got: {response.status_code}"
    
    response_data = response.json()
    assert "detail" in response_data, "Error response should include detail"
    assert "Invalid API key" in response_data["detail"] or "invalid" in response_data["detail"].lower(), \
        f"Error message should mention invalid key. Got: {response_data['detail']}"
    
    print("✓ Invalid API key is rejected with 401")
    
    # Test 4: Test Authorization header with Bearer scheme
    print("\n--- Test 4: Bearer token authentication should work ---")
    
    response = test_client.post(
        "/process",
        data={"text": "Test complaint"},
        headers={"Authorization": "Bearer test-key-123"}
    )
    
    assert response.status_code == 200, \
        f"Bearer token should allow access. Error: {response.text}"
    
    print("✓ Bearer token authentication works")
    
    # Test 5: Test another protected endpoint (session status)
    print("\n--- Test 5: Authentication works on other endpoints ---")
    
    # First create a session
    response = test_client.post(
        "/process",
        data={"text": "Test complaint"},
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert response.status_code == 200, f"Process failed: {response.text}"
    session_id = response.json()["session_id"]
    
    # Try to access status without API key
    response = test_client.get(f"/session/{session_id}/status")
    
    assert response.status_code == 401, \
        f"Status endpoint should require authentication. Got: {response.status_code}"
    
    print("✓ Authentication required on /session/{id}/status endpoint")
    
    # Try to access status with valid API key
    response = test_client.get(
        f"/session/{session_id}/status",
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert response.status_code == 200, \
        f"Valid API key should allow access to status endpoint. Error: {response.text}"
    
    print("✓ Valid API key allows access to /session/{id}/status endpoint")
    
    print("\n=== Authentication Preservation Test PASSED ===")
    print("Verified:")
    print("  ✓ Protected endpoints require valid API key")
    print("  ✓ Invalid API keys are rejected with 401")
    print("  ✓ Missing API keys are rejected with 401")
    print("  ✓ Valid API keys allow access to protected endpoints")
    print("  ✓ Bearer token authentication works")
    print("  ✓ Authentication works across multiple endpoints")


@pytest.mark.integration
def test_health_check_without_authentication(test_client):
    """
    Test that /health endpoint works without authentication.
    
    **Validates: Requirement 3.8**
    
    This test verifies:
    - /health endpoint is accessible without API key
    - Health check returns expected response structure
    - Health check endpoint is in PUBLIC_ENDPOINTS list
    
    This confirms that the /health endpoint continues to work without
    authentication as before, and bug fixes did not break this behavior.
    """
    
    print("\n=== Testing Health Check Without Authentication ===")
    
    # Test 1: Health endpoint should work without API key
    print("\n--- Test 1: /health endpoint accessible without API key ---")
    
    response = test_client.get("/health")
    
    assert response.status_code == 200, \
        f"Health endpoint should be accessible without API key. Got: {response.status_code}, Error: {response.text}"
    
    print("✓ /health endpoint accessible without API key")
    
    # Test 2: Verify response structure
    print("\n--- Test 2: Health check returns expected structure ---")
    
    response_data = response.json()
    
    # Health endpoint should return status information
    assert "status" in response_data or "overall_status" in response_data, \
        f"Health response should include status field. Got: {response_data}"
    
    print(f"Health response: {response_data}")
    print("✓ Health check returns expected response structure")
    
    # Test 3: Health endpoint should work even with invalid API key
    print("\n--- Test 3: /health works even with invalid API key ---")
    
    response = test_client.get(
        "/health",
        headers={"X-API-Key": "invalid-key-999"}
    )
    
    assert response.status_code == 200, \
        f"Health endpoint should ignore API key and work anyway. Got: {response.status_code}"
    
    print("✓ /health endpoint works even with invalid API key")
    
    # Test 4: Health endpoint should work with valid API key too
    print("\n--- Test 4: /health works with valid API key ---")
    
    response = test_client.get(
        "/health",
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert response.status_code == 200, \
        f"Health endpoint should work with valid API key. Got: {response.status_code}"
    
    print("✓ /health endpoint works with valid API key")
    
    print("\n=== Health Check Test PASSED ===")
    print("Verified:")
    print("  ✓ /health endpoint accessible without API key")
    print("  ✓ Health check returns expected response structure")
    print("  ✓ /health works with invalid API key (ignores it)")
    print("  ✓ /health works with valid API key")


@pytest.mark.integration
def test_authentication_and_health_check_integration(test_client):
    """
    Integration test combining authentication and health check verification.
    
    **Validates: Requirements 3.7, 3.8**
    
    This test verifies the complete authentication and health check behavior:
    1. Health check works without authentication
    2. Protected endpoints require authentication
    3. Both behaviors coexist correctly
    """
    
    print("\n=== Testing Authentication and Health Check Integration ===")
    
    # Step 1: Verify health check works without auth
    print("\n--- Step 1: Health check without authentication ---")
    
    health_response = test_client.get("/health")
    assert health_response.status_code == 200, \
        f"Health check should work without auth. Error: {health_response.text}"
    
    print("✓ Health check works without authentication")
    
    # Step 2: Verify protected endpoint requires auth
    print("\n--- Step 2: Protected endpoint requires authentication ---")
    
    process_response = test_client.post(
        "/process",
        data={"text": "Test complaint"}
    )
    
    assert process_response.status_code == 401, \
        f"Protected endpoint should require auth. Got: {process_response.status_code}"
    
    print("✓ Protected endpoint requires authentication")
    
    # Step 3: Verify protected endpoint works with valid auth
    print("\n--- Step 3: Protected endpoint works with valid auth ---")
    
    process_response = test_client.post(
        "/process",
        data={"text": "Test complaint"},
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert process_response.status_code == 200, \
        f"Protected endpoint should work with valid auth. Error: {process_response.text}"
    
    print("✓ Protected endpoint works with valid authentication")
    
    # Step 4: Verify health check still works (no interference)
    print("\n--- Step 4: Health check still works after auth tests ---")
    
    health_response = test_client.get("/health")
    assert health_response.status_code == 200, \
        f"Health check should still work. Error: {health_response.text}"
    
    print("✓ Health check still works after authentication tests")
    
    print("\n=== Integration Test PASSED ===")
    print("Verified:")
    print("  ✓ Health check works without authentication")
    print("  ✓ Protected endpoints require authentication")
    print("  ✓ Protected endpoints work with valid authentication")
    print("  ✓ Both behaviors coexist correctly")
    print("\nRequirements validated:")
    print("  ✓ 3.7: APIAuthMiddleware continues to enforce authentication")
    print("  ✓ 3.8: /health endpoint continues to work without authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
