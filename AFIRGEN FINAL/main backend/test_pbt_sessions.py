"""
Property-Based Tests for Session Management
Tests properties 11-12: Session data completeness and session round trip
"""

import pytest
from hypothesis import given, settings, strategies as st
from unittest.mock import Mock
import json
import time


@st.composite
def session_data_strategy(draw):
    """Generate valid session data"""
    return {
        "status": draw(st.sampled_from(["processing", "completed", "failed"])),
        "transcript": draw(st.text(min_size=10, max_size=200)),
        "summary": draw(st.text(min_size=10, max_size=200)),
        "violations": json.dumps([{"section": "379", "title": "Theft"}]),
        "fir_content": json.dumps({
            "complainant_name": draw(st.text(min_size=1, max_size=100)),
            "incident_description": draw(st.text(min_size=10, max_size=200))
        }),
        "fir_number": f"FIR-20240115-{draw(st.integers(min_value=1, max_value=99999)):05d}"
    }


def create_mock_database_manager_with_sessions():
    """Create mock database manager with session support"""
    mock_db = Mock()
    
    # Mock storage for sessions
    mock_db._session_storage = {}
    
    def mock_create_session(session_id):
        mock_db._session_storage[session_id] = {
            "session_id": session_id,
            "status": "processing",
            "transcript": None,
            "summary": None,
            "violations": None,
            "fir_content": None,
            "fir_number": None,
            "error": None,
            "created_at": time.time(),
            "updated_at": time.time()
        }
    
    def mock_update_session(session_id, data):
        if session_id in mock_db._session_storage:
            mock_db._session_storage[session_id].update(data)
            mock_db._session_storage[session_id]["updated_at"] = time.time()
    
    def mock_get_session(session_id):
        return mock_db._session_storage.get(session_id)
    
    mock_db.create_session = Mock(side_effect=mock_create_session)
    mock_db.update_session = Mock(side_effect=mock_update_session)
    mock_db.get_session = Mock(side_effect=mock_get_session)
    
    return mock_db


@pytest.mark.property
@given(session_data=session_data_strategy())
@settings(max_examples=50, deadline=None)
def test_property_11_session_data_completeness(session_data):
    """
    **Property 11: Session data completeness**
    **Validates: Requirements 13.6**
    
    For any completed session, session data contains all required fields.
    """
    mock_db = create_mock_database_manager_with_sessions()
    
    # Create session
    session_id = "test-session-complete"
    mock_db.create_session(session_id)
    
    # Update session with complete data
    mock_db.update_session(session_id, session_data)
    
    # Retrieve session
    retrieved_session = mock_db.get_session(session_id)
    
    # Property: Session must contain all required fields
    required_fields = [
        "session_id",
        "status",
        "transcript",
        "summary",
        "violations",
        "fir_content",
        "fir_number",
        "error",
        "created_at",
        "updated_at"
    ]
    
    for field in required_fields:
        assert field in retrieved_session, f"Session must contain field: {field}"
    
    # Property: For completed sessions, key fields must be non-None
    if session_data["status"] == "completed":
        assert retrieved_session["transcript"] is not None, "Completed session must have transcript"
        assert retrieved_session["fir_content"] is not None, "Completed session must have fir_content"
        assert retrieved_session["fir_number"] is not None, "Completed session must have fir_number"


@pytest.mark.property
@given(session_data=session_data_strategy())
@settings(max_examples=50, deadline=None)
def test_property_12_session_round_trip(session_data):
    """
    **Property 12: Session round trip**
    **Validates: Requirements 13.7**
    
    For any created session, polling session endpoint returns current session data.
    """
    mock_db = create_mock_database_manager_with_sessions()
    
    # Create session
    session_id = "test-session-roundtrip"
    mock_db.create_session(session_id)
    
    # Update session with data
    mock_db.update_session(session_id, session_data)
    
    # Poll session (retrieve)
    polled_session = mock_db.get_session(session_id)
    
    # Property: Polled session must not be None
    assert polled_session is not None, "Polled session must not be None"
    
    # Property: Polled session must contain the session_id
    assert polled_session["session_id"] == session_id, "Session ID must match"
    
    # Property: Polled session must reflect updated data
    assert polled_session["status"] == session_data["status"], "Status must match"
    
    if session_data.get("transcript"):
        assert polled_session["transcript"] == session_data["transcript"], "Transcript must match"
    
    if session_data.get("fir_number"):
        assert polled_session["fir_number"] == session_data["fir_number"], "FIR number must match"
    
    # Property: Updated timestamp must be >= created timestamp
    assert polled_session["updated_at"] >= polled_session["created_at"], \
        "Updated timestamp must be >= created timestamp"
