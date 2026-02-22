"""
Integration Test for Task 25.4 - Regeneration Workflow

**Validates: Requirement 2.5**

This integration test verifies the regeneration workflow works correctly after Bug 5 fix:

1. Create session and reach validation step
2. POST /regenerate with JSON body (matching frontend format)
3. Verify regeneration succeeds

This test confirms that Bug 5 is fixed: the backend now accepts JSON body requests
for the /regenerate endpoint, matching the frontend's request format.
"""

import pytest
import sys
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
    
    # Mock the two_line_summary method
    mock_pool.two_line_summary = AsyncMock(return_value="Test summary of the complaint")
    
    # Mock the check_violation method
    mock_pool.check_violation = AsyncMock(return_value=True)
    
    # Mock the fir_narrative method
    mock_pool.fir_narrative = AsyncMock(return_value="Test FIR narrative content")
    
    return mock_pool


@pytest.fixture
def mock_kb():
    """Mock KB (knowledge base) to avoid external dependencies."""
    mock = Mock()
    mock.retrieve = Mock(return_value=[
        {
            "section": "Section 420",
            "title": "Cheating and dishonestly inducing delivery of property",
            "description": "Test violation description"
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
    
    # Import agentv5 and patch dependencies
    with patch('agentv5.ModelPool') as MockModelPool, \
         patch('agentv5.KB') as MockKB, \
         patch('agentv5.DB', return_value=mock_db):
        
        # Configure mocks
        MockModelPool.get = AsyncMock(return_value=mock_model_pool)
        MockKB.return_value = mock_kb
        
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
def test_regeneration_workflow_with_json_body(test_client):
    """
    Test the regeneration workflow with JSON body request format.
    
    **Validates: Requirement 2.5**
    
    This test verifies Bug 5 fix: the /regenerate endpoint now accepts JSON body
    requests matching the frontend format, instead of expecting query parameters.
    
    Test Flow:
    1. Create a text-only session
    2. Advance to SUMMARY_REVIEW step
    3. POST /regenerate with JSON body {step, user_input}
    4. Verify regeneration succeeds and returns updated content
    """
    
    # Step 1: Create a text-only session
    print("\n=== Step 1: Create text-only session ===")
    
    test_text = "I want to report a theft. Someone stole my mobile phone."
    
    response = test_client.post(
        "/process",
        data={"text": test_text},
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert response.status_code == 200, f"Process endpoint failed: {response.text}"
    
    process_data = response.json()
    print(f"Process response: {process_data}")
    
    assert process_data["success"] is True, "Process should succeed"
    assert "session_id" in process_data, "Response should include session_id"
    
    session_id = process_data["session_id"]
    print(f"Session ID: {session_id}")
    
    # Step 2: Advance to SUMMARY_REVIEW step
    print("\n=== Step 2: Advance to SUMMARY_REVIEW ===")
    
    # First, approve TRANSCRIPT_REVIEW
    validate_response = test_client.post(
        "/validate",
        json={
            "session_id": session_id,
            "approved": True,
            "user_input": None
        },
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert validate_response.status_code == 200, f"Validate failed: {validate_response.text}"
    
    validate_data = validate_response.json()
    print(f"Validate response: {validate_data}")
    
    assert validate_data["success"] is True, "Validation should succeed"
    assert validate_data["current_step"] == "SUMMARY_REVIEW", "Should advance to SUMMARY_REVIEW"
    assert "summary" in validate_data["content"], "Should return summary content"
    
    original_summary = validate_data["content"]["summary"]
    print(f"Original summary: {original_summary}")
    
    # Step 3: POST /regenerate with JSON body (Bug 5 fix)
    print("\n=== Step 3: POST /regenerate with JSON body ===")
    
    # This is the format the frontend sends (api.js lines 451-460)
    regenerate_request = {
        "step": "SUMMARY_REVIEW",
        "user_input": "Please make the summary more detailed and include the time of incident."
    }
    
    print(f"Regenerate request: {regenerate_request}")
    
    regenerate_response = test_client.post(
        f"/regenerate/{session_id}",
        json=regenerate_request,  # JSON body, not query params
        headers={"X-API-Key": "test-key-123"}
    )
    
    print(f"Regenerate response status: {regenerate_response.status_code}")
    print(f"Regenerate response: {regenerate_response.text}")
    
    assert regenerate_response.status_code == 200, \
        f"Bug 5 fix: Regenerate endpoint should accept JSON body requests. Error: {regenerate_response.text}"
    
    # Step 4: Verify regeneration succeeds
    print("\n=== Step 4: Verify regeneration succeeds ===")
    
    regenerate_data = regenerate_response.json()
    print(f"Regenerate data: {regenerate_data}")
    
    assert regenerate_data["success"] is True, "Regeneration should succeed"
    assert "content" in regenerate_data, "Response should include content"
    assert "summary" in regenerate_data["content"], "Content should include regenerated summary"
    
    regenerated_summary = regenerate_data["content"]["summary"]
    print(f"Regenerated summary: {regenerated_summary}")
    
    # Verify the summary was regenerated (it should be different or at least processed)
    assert regenerated_summary is not None, "Regenerated summary should not be None"
    assert len(regenerated_summary) > 0, "Regenerated summary should not be empty"
    
    # Verify session is still at SUMMARY_REVIEW step
    assert regenerate_data["current_step"] == "SUMMARY_REVIEW", \
        "Should remain at SUMMARY_REVIEW step after regeneration"
    
    print("\n=== Integration Test PASSED ===")
    print(f"Successfully tested regeneration workflow:")
    print(f"  - Session ID: {session_id}")
    print(f"  - Regeneration step: SUMMARY_REVIEW")
    print(f"  - User input: {regenerate_request['user_input']}")
    print(f"  - Regeneration succeeded with JSON body request")
    print(f"\nVerified fix:")
    print(f"  ✓ Bug 5: Regenerate endpoint accepts JSON body (frontend format)")


@pytest.mark.integration
def test_regeneration_at_different_steps(test_client):
    """
    Test regeneration at different validation steps.
    
    **Validates: Requirement 2.5**
    
    This test verifies that the regeneration endpoint works correctly at various
    validation steps, not just SUMMARY_REVIEW.
    """
    
    # Create a text-only session
    test_text = "Test complaint for regeneration at different steps"
    
    response = test_client.post(
        "/process",
        data={"text": test_text},
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert response.status_code == 200, f"Process failed: {response.text}"
    
    session_id = response.json()["session_id"]
    print(f"\nSession ID: {session_id}")
    
    # Test regeneration at TRANSCRIPT_REVIEW (initial step)
    print("\n=== Test regeneration at TRANSCRIPT_REVIEW ===")
    
    regenerate_response = test_client.post(
        f"/regenerate/{session_id}",
        json={
            "step": "TRANSCRIPT_REVIEW",
            "user_input": "Please correct the transcript"
        },
        headers={"X-API-Key": "test-key-123"}
    )
    
    print(f"Regenerate at TRANSCRIPT_REVIEW: {regenerate_response.status_code}")
    
    assert regenerate_response.status_code == 200, \
        f"Regeneration at TRANSCRIPT_REVIEW failed: {regenerate_response.text}"
    
    regenerate_data = regenerate_response.json()
    assert regenerate_data["success"] is True, "Regeneration should succeed"
    assert regenerate_data["current_step"] == "TRANSCRIPT_REVIEW", \
        "Should remain at TRANSCRIPT_REVIEW"
    
    # Advance to SUMMARY_REVIEW
    validate_response = test_client.post(
        "/validate",
        json={
            "session_id": session_id,
            "approved": True,
            "user_input": None
        },
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert validate_response.status_code == 200, f"Validate failed: {validate_response.text}"
    assert validate_response.json()["current_step"] == "SUMMARY_REVIEW"
    
    # Test regeneration at SUMMARY_REVIEW
    print("\n=== Test regeneration at SUMMARY_REVIEW ===")
    
    regenerate_response = test_client.post(
        f"/regenerate/{session_id}",
        json={
            "step": "SUMMARY_REVIEW",
            "user_input": "Make it more concise"
        },
        headers={"X-API-Key": "test-key-123"}
    )
    
    print(f"Regenerate at SUMMARY_REVIEW: {regenerate_response.status_code}")
    
    assert regenerate_response.status_code == 200, \
        f"Regeneration at SUMMARY_REVIEW failed: {regenerate_response.text}"
    
    regenerate_data = regenerate_response.json()
    assert regenerate_data["success"] is True, "Regeneration should succeed"
    assert regenerate_data["current_step"] == "SUMMARY_REVIEW", \
        "Should remain at SUMMARY_REVIEW"
    
    print("\n✓ Regeneration works at multiple validation steps")


@pytest.mark.integration
def test_regeneration_without_user_input(test_client):
    """
    Test regeneration without user_input (optional parameter).
    
    **Validates: Requirement 2.5**
    
    This test verifies that the regeneration endpoint works when user_input is None
    or not provided, as it's an optional parameter.
    """
    
    # Create a text-only session
    test_text = "Test complaint for regeneration without user input"
    
    response = test_client.post(
        "/process",
        data={"text": test_text},
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert response.status_code == 200, f"Process failed: {response.text}"
    
    session_id = response.json()["session_id"]
    print(f"\nSession ID: {session_id}")
    
    # Advance to SUMMARY_REVIEW
    validate_response = test_client.post(
        "/validate",
        json={
            "session_id": session_id,
            "approved": True,
            "user_input": None
        },
        headers={"X-API-Key": "test-key-123"}
    )
    
    assert validate_response.status_code == 200, f"Validate failed: {validate_response.text}"
    assert validate_response.json()["current_step"] == "SUMMARY_REVIEW"
    
    # Test regeneration without user_input
    print("\n=== Test regeneration without user_input ===")
    
    regenerate_response = test_client.post(
        f"/regenerate/{session_id}",
        json={
            "step": "SUMMARY_REVIEW",
            "user_input": None  # Optional parameter
        },
        headers={"X-API-Key": "test-key-123"}
    )
    
    print(f"Regenerate without user_input: {regenerate_response.status_code}")
    
    assert regenerate_response.status_code == 200, \
        f"Regeneration without user_input failed: {regenerate_response.text}"
    
    regenerate_data = regenerate_response.json()
    assert regenerate_data["success"] is True, "Regeneration should succeed"
    
    # Test regeneration with user_input omitted entirely
    print("\n=== Test regeneration with user_input omitted ===")
    
    regenerate_response = test_client.post(
        f"/regenerate/{session_id}",
        json={
            "step": "SUMMARY_REVIEW"
            # user_input not included
        },
        headers={"X-API-Key": "test-key-123"}
    )
    
    print(f"Regenerate with user_input omitted: {regenerate_response.status_code}")
    
    assert regenerate_response.status_code == 200, \
        f"Regeneration with user_input omitted failed: {regenerate_response.text}"
    
    regenerate_data = regenerate_response.json()
    assert regenerate_data["success"] is True, "Regeneration should succeed"
    
    print("\n✓ Regeneration works with and without user_input parameter")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
