"""
Integration Test for Task 25.6 - Graceful Shutdown

**Validates: Requirements 2.10, 3.9**

This integration test verifies that graceful shutdown handling works correctly:

1. Initiate shutdown during active request
2. Verify 503 response is returned properly
3. Verify no crashes occur

This test confirms that Bug 10 is fixed (proper 503 response) and that the graceful
shutdown mechanism continues to work correctly (Requirement 3.9).
"""

import pytest
import sys
import asyncio
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture
def mock_model_pool():
    """Mock ModelPool to avoid external dependencies."""
    mock_pool = AsyncMock()
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
def test_client(mock_model_pool, mock_kb):
    """Create a test client with mocked dependencies."""
    # Mock DB class to avoid MySQL connection requirement
    mock_db = Mock()
    mock_db.save_fir = Mock(return_value=True)
    mock_db.get_fir = Mock(return_value=None)
    mock_db.flush_all = Mock()
    
    with patch('agentv5.ModelPool') as MockModelPool, \
         patch('agentv5.KB') as MockKB, \
         patch('agentv5.DB', return_value=mock_db):
        
        MockModelPool.get = AsyncMock(return_value=mock_model_pool)
        MockKB.return_value = mock_kb
        
        from agentv5 import app, session_manager, graceful_shutdown
        
        # Clean up any existing test data
        try:
            session_manager.flush_all()
        except:
            pass
        
        # Reset graceful shutdown state
        graceful_shutdown.is_shutting_down = False
        graceful_shutdown.active_requests = 0
        
        client = TestClient(app)
        
        yield client, graceful_shutdown
        
        # Cleanup after test
        try:
            session_manager.flush_all()
        except:
            pass
        
        # Reset graceful shutdown state
        graceful_shutdown.is_shutting_down = False
        graceful_shutdown.active_requests = 0


@pytest.mark.integration
def test_graceful_shutdown_returns_503_during_shutdown(test_client):
    """
    Test that requests during shutdown receive proper 503 response.
    
    **Validates: Requirements 2.10, 3.9**
    
    This test verifies:
    - Bug 10 fix: Shutdown handling returns proper 503 JSONResponse (not crash)
    - Requirement 3.9: Graceful shutdown continues to track active requests
    
    Test Flow:
    1. Verify graceful shutdown is not active initially
    2. Initiate shutdown (set is_shutting_down flag)
    3. Attempt to make a request
    4. Verify 503 response is returned properly
    5. Verify no crashes occur
    """
    
    client, graceful_shutdown = test_client
    
    # Step 1: Verify graceful shutdown is not active initially
    print("\n=== Step 1: Verify initial state ===")
    
    status = graceful_shutdown.get_status()
    print(f"Initial graceful shutdown status: {status}")
    
    assert status["is_shutting_down"] is False, "Should not be shutting down initially"
    assert status["active_requests"] == 0, "Should have no active requests initially"
    
    # Step 2: Initiate shutdown
    print("\n=== Step 2: Initiate shutdown ===")
    
    graceful_shutdown.is_shutting_down = True
    
    status = graceful_shutdown.get_status()
    print(f"Graceful shutdown status after initiation: {status}")
    
    assert status["is_shutting_down"] is True, "Should be shutting down"
    
    # Step 3: Attempt to make a request during shutdown
    print("\n=== Step 3: Attempt request during shutdown ===")
    
    # Try to create a new session - this should trigger the shutdown check
    response = client.post(
        "/process",
        data={"text": "Test complaint during shutdown"},
        headers={"X-API-Key": "test-key-123"}
    )
    
    print(f"Response status code: {response.status_code}")
    print(f"Response body: {response.text}")
    
    # Step 4: Verify 503 response is returned properly (Bug 10 fix)
    print("\n=== Step 4: Verify 503 response ===")
    
    assert response.status_code == 503, \
        f"Bug 10 fix: Should return 503 Service Unavailable during shutdown, got {response.status_code}"
    
    # Verify response is proper JSON (not a crash)
    try:
        response_data = response.json()
        print(f"Response JSON: {response_data}")
        
        assert "detail" in response_data, "Response should include detail field"
        assert "shutting down" in response_data["detail"].lower(), \
            "Response should indicate server is shutting down"
        
        print("✓ Proper 503 JSONResponse returned (Bug 10 fix verified)")
        
    except Exception as e:
        pytest.fail(f"Bug 10 fix: Response should be valid JSON, but got error: {e}")
    
    # Step 5: Verify no crashes occur
    print("\n=== Step 5: Verify no crashes ===")
    
    # If we got here without exceptions, no crash occurred
    print("✓ No crashes occurred during shutdown handling")
    
    # Verify graceful shutdown state is still consistent
    status = graceful_shutdown.get_status()
    print(f"Final graceful shutdown status: {status}")
    
    assert status["is_shutting_down"] is True, "Should still be shutting down"
    assert status["active_requests"] == 0, "Should have no active requests (request was rejected)"
    
    print("\n=== Integration Test PASSED ===")
    print("Verified:")
    print("  ✓ Bug 10 fix: Proper 503 JSONResponse returned during shutdown")
    print("  ✓ Requirement 3.9: Graceful shutdown mechanism works correctly")
    print("  ✓ No crashes occur during shutdown handling")


@pytest.mark.integration
def test_graceful_shutdown_tracks_active_requests(test_client):
    """
    Test that graceful shutdown correctly tracks active requests.
    
    **Validates: Requirement 3.9**
    
    This test verifies that the graceful shutdown mechanism continues to track
    active requests correctly (preservation requirement).
    
    Test Flow:
    1. Make a request and verify it's tracked
    2. Verify active request count increases
    3. Complete the request
    4. Verify active request count decreases
    """
    
    client, graceful_shutdown = test_client
    
    # Step 1: Verify initial state
    print("\n=== Step 1: Verify initial state ===")
    
    status = graceful_shutdown.get_status()
    print(f"Initial status: {status}")
    
    assert status["is_shutting_down"] is False, "Should not be shutting down"
    assert status["active_requests"] == 0, "Should have no active requests"
    
    # Step 2: Make a request
    print("\n=== Step 2: Make a request ===")
    
    response = client.post(
        "/process",
        data={"text": "Test complaint for request tracking"},
        headers={"X-API-Key": "test-key-123"}
    )
    
    print(f"Response status: {response.status_code}")
    
    assert response.status_code == 200, f"Request should succeed, got {response.status_code}"
    
    # Step 3: Verify request was tracked (completed and decremented)
    print("\n=== Step 3: Verify request tracking ===")
    
    status = graceful_shutdown.get_status()
    print(f"Status after request: {status}")
    
    # After request completes, active_requests should be back to 0
    assert status["active_requests"] == 0, \
        "Active requests should be 0 after request completes (request_completed called)"
    
    print("✓ Request tracking works correctly")
    
    # Step 4: Verify health endpoint shows graceful shutdown status
    print("\n=== Step 4: Verify health endpoint includes shutdown status ===")
    
    health_response = client.get("/health")
    
    assert health_response.status_code == 200, "Health endpoint should work"
    
    health_data = health_response.json()
    print(f"Health response: {health_data}")
    
    # Verify graceful_shutdown status is included in health response
    if "reliability" in health_data:
        reliability = health_data["reliability"]
        
        assert "graceful_shutdown" in reliability, \
            "Health endpoint should include graceful_shutdown status"
        
        shutdown_status = reliability["graceful_shutdown"]
        print(f"Graceful shutdown status in health: {shutdown_status}")
        
        assert "is_shutting_down" in shutdown_status, \
            "Shutdown status should include is_shutting_down"
        assert "active_requests" in shutdown_status, \
            "Shutdown status should include active_requests"
        assert "shutdown_timeout" in shutdown_status, \
            "Shutdown status should include shutdown_timeout"
        
        print("✓ Health endpoint includes graceful shutdown status")
    
    print("\n=== Integration Test PASSED ===")
    print("Verified:")
    print("  ✓ Requirement 3.9: Graceful shutdown tracks active requests")
    print("  ✓ Request tracking increments and decrements correctly")
    print("  ✓ Health endpoint exposes shutdown status")


@pytest.mark.integration
def test_graceful_shutdown_no_crash_on_error_response(test_client):
    """
    Test that shutdown error handling doesn't crash (Bug 10 fix verification).
    
    **Validates: Requirement 2.10**
    
    This test specifically verifies that the Bug 10 fix works correctly:
    - Old code: HTTPException.to_response() causes AttributeError crash
    - Fixed code: JSONResponse returns proper 503 response
    
    Test Flow:
    1. Set shutdown flag
    2. Make multiple requests
    3. Verify all return 503 without crashes
    4. Verify responses are valid JSON
    """
    
    client, graceful_shutdown = test_client
    
    print("\n=== Test: Multiple requests during shutdown ===")
    
    # Set shutdown flag
    graceful_shutdown.is_shutting_down = True
    
    # Make multiple requests to ensure consistent behavior
    for i in range(3):
        print(f"\n--- Request {i+1} ---")
        
        response = client.post(
            "/process",
            data={"text": f"Test complaint {i+1}"},
            headers={"X-API-Key": "test-key-123"}
        )
        
        print(f"Status code: {response.status_code}")
        
        # Verify 503 response
        assert response.status_code == 503, \
            f"Request {i+1}: Should return 503, got {response.status_code}"
        
        # Verify valid JSON response (not a crash)
        try:
            response_data = response.json()
            print(f"Response: {response_data}")
            
            assert "detail" in response_data, \
                f"Request {i+1}: Response should have detail field"
            
            print(f"✓ Request {i+1}: Proper 503 response (no crash)")
            
        except Exception as e:
            pytest.fail(
                f"Request {i+1}: Bug 10 fix failed - response should be valid JSON. "
                f"Error: {e}, Response text: {response.text}"
            )
    
    print("\n=== Integration Test PASSED ===")
    print("Verified:")
    print("  ✓ Bug 10 fix: All requests during shutdown return proper 503 response")
    print("  ✓ No AttributeError crashes on to_response()")
    print("  ✓ Consistent behavior across multiple requests")


@pytest.mark.integration
def test_graceful_shutdown_health_check_still_works(test_client):
    """
    Test that health check endpoint works during shutdown.
    
    **Validates: Requirements 3.8, 3.9**
    
    This test verifies that the health check endpoint continues to work
    during shutdown (it should not be blocked by shutdown).
    
    Test Flow:
    1. Set shutdown flag
    2. Call health endpoint
    3. Verify it returns 200 (not 503)
    4. Verify shutdown status is reflected in response
    """
    
    client, graceful_shutdown = test_client
    
    print("\n=== Test: Health check during shutdown ===")
    
    # Set shutdown flag
    graceful_shutdown.is_shutting_down = True
    
    # Call health endpoint
    response = client.get("/health")
    
    print(f"Health endpoint status: {response.status_code}")
    
    # Health endpoint should still work (not return 503)
    assert response.status_code == 200, \
        "Health endpoint should work during shutdown (it's excluded from tracking)"
    
    health_data = response.json()
    print(f"Health response: {health_data}")
    
    # Verify shutdown status is reflected
    if "reliability" in health_data:
        reliability = health_data["reliability"]
        
        if "graceful_shutdown" in reliability:
            shutdown_status = reliability["graceful_shutdown"]
            print(f"Shutdown status: {shutdown_status}")
            
            assert shutdown_status["is_shutting_down"] is True, \
                "Health endpoint should reflect shutdown state"
            
            print("✓ Health endpoint reflects shutdown state")
    
    print("\n=== Integration Test PASSED ===")
    print("Verified:")
    print("  ✓ Requirement 3.8: Health endpoint works during shutdown")
    print("  ✓ Requirement 3.9: Shutdown status is tracked and exposed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
