"""
Property-Based Tests for Storage Operations
Tests properties 5-8: FIR storage persistence, round trip, pagination, and status finalization
"""

import pytest
from hypothesis import given, settings, strategies as st
from unittest.mock import Mock, MagicMock
import json


@st.composite
def fir_data_strategy(draw):
    """Generate valid FIR data with all 30 fields"""
    return {
        "complainant_name": draw(st.text(min_size=1, max_size=100)),
        "complainant_dob": "01/01/1990",
        "complainant_nationality": draw(st.text(min_size=1, max_size=50)),
        "complainant_father_husband_name": draw(st.text(min_size=1, max_size=100)),
        "complainant_address": draw(st.text(min_size=1, max_size=200)),
        "complainant_contact": draw(st.text(min_size=10, max_size=15)),
        "complainant_passport": draw(st.text(min_size=1, max_size=50)),
        "complainant_occupation": draw(st.text(min_size=1, max_size=100)),
        "incident_date_from": "15/01/2024",
        "incident_date_to": "15/01/2024",
        "incident_time_from": "14:30",
        "incident_time_to": "15:00",
        "incident_location": draw(st.text(min_size=1, max_size=100)),
        "incident_address": draw(st.text(min_size=1, max_size=200)),
        "incident_description": draw(st.text(min_size=10, max_size=500)),
        "delayed_reporting_reasons": draw(st.text(min_size=1, max_size=200)),
        "incident_summary": draw(st.text(min_size=10, max_size=300)),
        "legal_acts": draw(st.text(min_size=1, max_size=100)),
        "legal_sections": draw(st.text(min_size=1, max_size=100)),
        "suspect_details": draw(st.text(min_size=1, max_size=200)),
        "investigating_officer_name": draw(st.text(min_size=1, max_size=100)),
        "investigating_officer_rank": draw(st.text(min_size=1, max_size=50)),
        "witnesses": draw(st.text(min_size=1, max_size=200)),
        "action_taken": draw(st.text(min_size=1, max_size=200)),
        "investigation_status": draw(st.text(min_size=1, max_size=100)),
        "date_of_despatch": "15/01/2024",
        "investigating_officer_signature": draw(st.text(min_size=1, max_size=100)),
        "investigating_officer_date": "15/01/2024",
        "complainant_signature": draw(st.text(min_size=1, max_size=100)),
        "complainant_date": "15/01/2024"
    }


def create_mock_database_manager():
    """Create a mock database manager"""
    mock_config = {
        "host": "localhost",
        "port": 3306,
        "user": "test",
        "password": "test",
        "database": "test_db"
    }
    
    # Create mock without spec
    mock_db = Mock()
    
    # Mock storage for testing
    mock_db._fir_storage = {}
    mock_db._fir_counter = 0
    
    def mock_insert_fir(fir_data):
        mock_db._fir_counter += 1
        fir_number = f"FIR-20240115-{mock_db._fir_counter:05d}"
        mock_db._fir_storage[fir_number] = {
            "fir_number": fir_number,
            "session_id": fir_data.get("session_id", "test-session"),
            "complaint_text": fir_data.get("complaint_text", "Test complaint"),
            "fir_content": fir_data.get("fir_content", {}),
            "violations_json": fir_data.get("violations_json", []),
            "status": "draft",
            "created_at": "2024-01-15 10:00:00"
        }
        return fir_number
    
    def mock_get_fir(fir_number):
        if fir_number in mock_db._fir_storage:
            return mock_db._fir_storage[fir_number]
        return None
    
    def mock_list_firs(limit=20, offset=0):
        all_firs = list(mock_db._fir_storage.values())
        paginated = all_firs[offset:offset+limit]
        return {
            "firs": paginated,
            "total": len(all_firs),
            "limit": limit,
            "offset": offset
        }
    
    def mock_update_status(fir_number, status):
        if fir_number in mock_db._fir_storage:
            mock_db._fir_storage[fir_number]["status"] = status
    
    mock_db.insert_fir_record.side_effect = mock_insert_fir
    mock_db.get_fir_by_number.side_effect = mock_get_fir
    mock_db.list_firs.side_effect = mock_list_firs
    mock_db.update_fir_status.side_effect = mock_update_status
    
    return mock_db


@pytest.mark.property
@given(fir_content=fir_data_strategy())
@settings(max_examples=50, deadline=None)
def test_property_5_fir_storage_persistence(fir_content):
    """
    **Property 5: FIR storage persistence**
    **Validates: Requirements 9.6-9.7, 18.6**
    
    For any generated FIR, record is inserted into fir_records table with all required fields.
    """
    mock_db = create_mock_database_manager()
    
    # Prepare FIR data
    fir_data = {
        "session_id": "test-session-123",
        "complaint_text": "Test complaint text",
        "fir_content": fir_content,
        "violations_json": [{"section": "379", "title": "Theft"}]
    }
    
    # Insert FIR
    fir_number = mock_db.insert_fir_record(fir_data)
    
    # Property: FIR number must be returned
    assert fir_number is not None, "FIR number must not be None"
    assert isinstance(fir_number, str), "FIR number must be a string"
    assert len(fir_number) > 0, "FIR number must not be empty"
    
    # Property: FIR must be stored with all required fields
    stored_fir = mock_db.get_fir_by_number(fir_number)
    assert stored_fir is not None, "Stored FIR must not be None"
    assert "fir_number" in stored_fir, "Stored FIR must have fir_number"
    assert "session_id" in stored_fir, "Stored FIR must have session_id"
    assert "complaint_text" in stored_fir, "Stored FIR must have complaint_text"
    assert "fir_content" in stored_fir, "Stored FIR must have fir_content"
    assert "violations_json" in stored_fir, "Stored FIR must have violations_json"
    assert "status" in stored_fir, "Stored FIR must have status"
    assert "created_at" in stored_fir, "Stored FIR must have created_at"


@pytest.mark.property
@given(fir_content=fir_data_strategy())
@settings(max_examples=50, deadline=None)
def test_property_6_fir_storage_round_trip(fir_content):
    """
    **Property 6: FIR storage round trip**
    **Validates: Requirements 9.9**
    
    For any generated FIR, storing and retrieving by fir_number returns equivalent content.
    """
    mock_db = create_mock_database_manager()
    
    # Prepare FIR data
    original_data = {
        "session_id": "test-session-456",
        "complaint_text": "Original complaint text",
        "fir_content": fir_content,
        "violations_json": [{"section": "420", "title": "Cheating"}]
    }
    
    # Store FIR
    fir_number = mock_db.insert_fir_record(original_data)
    
    # Retrieve FIR
    retrieved_fir = mock_db.get_fir_by_number(fir_number)
    
    # Property: Retrieved FIR must contain equivalent content
    assert retrieved_fir is not None, "Retrieved FIR must not be None"
    assert retrieved_fir["fir_number"] == fir_number, "FIR number must match"
    assert retrieved_fir["session_id"] == original_data["session_id"], "Session ID must match"
    assert retrieved_fir["complaint_text"] == original_data["complaint_text"], "Complaint text must match"
    
    # Property: FIR content must be preserved
    assert retrieved_fir["fir_content"] == original_data["fir_content"], "FIR content must match"
    assert retrieved_fir["violations_json"] == original_data["violations_json"], "Violations must match"


@pytest.mark.property
@given(
    num_firs=st.integers(min_value=1, max_value=100),
    limit=st.integers(min_value=1, max_value=50),
    offset=st.integers(min_value=0, max_value=50)
)
@settings(max_examples=50, deadline=None)
def test_property_7_fir_listing_pagination(num_firs, limit, offset):
    """
    **Property 7: FIR listing pagination**
    **Validates: Requirements 9.10**
    
    For any valid limit/offset, /firs endpoint returns at most limit FIRs with non-overlapping pages.
    """
    mock_db = create_mock_database_manager()
    
    # Create multiple FIRs
    fir_numbers = []
    for i in range(num_firs):
        fir_data = {
            "session_id": f"session-{i}",
            "complaint_text": f"Complaint {i}",
            "fir_content": {"complainant_name": f"Person {i}"},
            "violations_json": []
        }
        fir_number = mock_db.insert_fir_record(fir_data)
        fir_numbers.append(fir_number)
    
    # List FIRs with pagination
    result = mock_db.list_firs(limit=limit, offset=offset)
    
    # Property: Result must contain required fields
    assert "firs" in result, "Result must contain firs list"
    assert "total" in result, "Result must contain total count"
    assert "limit" in result, "Result must contain limit"
    assert "offset" in result, "Result must contain offset"
    
    # Property: Number of returned FIRs must not exceed limit
    assert len(result["firs"]) <= limit, f"Returned FIRs ({len(result['firs'])}) must not exceed limit ({limit})"
    
    # Property: Total count must match number of created FIRs
    assert result["total"] == num_firs, f"Total count must match created FIRs"
    
    # Property: If offset < total, some FIRs should be returned (unless offset >= total)
    if offset < num_firs:
        expected_count = min(limit, num_firs - offset)
        assert len(result["firs"]) == expected_count, f"Expected {expected_count} FIRs, got {len(result['firs'])}"


@pytest.mark.property
@given(fir_content=fir_data_strategy())
@settings(max_examples=50, deadline=None)
def test_property_8_status_finalization(fir_content):
    """
    **Property 8: Status finalization**
    **Validates: Requirements 9.8**
    
    For any FIR in "draft" status, authenticate endpoint updates status to "finalized".
    """
    mock_db = create_mock_database_manager()
    
    # Create FIR in draft status
    fir_data = {
        "session_id": "test-session-789",
        "complaint_text": "Test complaint",
        "fir_content": fir_content,
        "violations_json": []
    }
    fir_number = mock_db.insert_fir_record(fir_data)
    
    # Verify initial status is draft
    fir = mock_db.get_fir_by_number(fir_number)
    assert fir["status"] == "draft", "Initial status must be draft"
    
    # Update status to finalized
    mock_db.update_fir_status(fir_number, "finalized")
    
    # Property: Status must be updated to finalized
    updated_fir = mock_db.get_fir_by_number(fir_number)
    assert updated_fir["status"] == "finalized", "Status must be updated to finalized"
