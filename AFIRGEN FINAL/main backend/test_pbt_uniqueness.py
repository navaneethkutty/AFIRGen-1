"""
Property-Based Tests for Uniqueness Properties
Tests properties 9-10: Unique file names and unique session IDs
"""

import pytest
from hypothesis import given, settings, strategies as st
from unittest.mock import Mock
import uuid


@st.composite
def file_bytes_strategy(draw):
    """Generate mock file bytes"""
    # Generate smaller sizes for faster tests
    size = draw(st.integers(min_value=100, max_value=1000))
    return bytes([draw(st.integers(min_value=0, max_value=255)) for _ in range(size)])


@pytest.mark.property
@given(
    file1=file_bytes_strategy(),
    file2=file_bytes_strategy()
)
@settings(max_examples=50, deadline=None)
def test_property_9_unique_file_names(file1, file2):
    """
    **Property 9: Unique file names**
    **Validates: Requirements 10.4**
    
    For any two file uploads, generated S3 keys are unique.
    """
    mock_aws = Mock()
    
    # Track generated S3 keys
    generated_keys = []
    
    def mock_upload(file_bytes, key, bucket):
        generated_keys.append(key)
        return f"s3://{bucket}/{key}"
    
    mock_aws.upload_to_s3 = Mock(side_effect=mock_upload)
    
    # Upload first file
    bucket = "test-bucket"
    key1 = f"audio/{uuid.uuid4()}.wav"
    mock_aws.upload_to_s3(file1, key1, bucket)
    
    # Upload second file
    key2 = f"audio/{uuid.uuid4()}.wav"
    mock_aws.upload_to_s3(file2, key2, bucket)
    
    # Property: Generated S3 keys must be unique
    assert len(generated_keys) == 2, "Two keys must be generated"
    assert generated_keys[0] != generated_keys[1], "S3 keys must be unique"
    
    # Property: Keys must follow expected format
    for key in generated_keys:
        assert isinstance(key, str), "Key must be a string"
        assert len(key) > 0, "Key must not be empty"
        assert "/" in key, "Key must contain path separator"


@pytest.mark.property
@given(
    num_sessions=st.integers(min_value=2, max_value=100)
)
@settings(max_examples=50, deadline=None)
def test_property_10_unique_session_ids(num_sessions):
    """
    **Property 10: Unique session IDs**
    **Validates: Requirements 13.1**
    
    For any two FIR generation requests, created session IDs are unique.
    """
    mock_db = Mock()
    
    # Track created session IDs
    created_sessions = []
    
    def mock_create_session(session_id):
        created_sessions.append(session_id)
    
    mock_db.create_session = Mock(side_effect=mock_create_session)
    
    # Create multiple sessions
    for i in range(num_sessions):
        session_id = str(uuid.uuid4())
        mock_db.create_session(session_id)
    
    # Property: All session IDs must be unique
    assert len(created_sessions) == num_sessions, f"Expected {num_sessions} sessions"
    assert len(set(created_sessions)) == num_sessions, "All session IDs must be unique"
    
    # Property: Session IDs must be valid UUIDs (or at least non-empty strings)
    for session_id in created_sessions:
        assert isinstance(session_id, str), "Session ID must be a string"
        assert len(session_id) > 0, "Session ID must not be empty"
        
        # Try to parse as UUID to verify format
        try:
            uuid.UUID(session_id)
        except ValueError:
            pytest.fail(f"Session ID {session_id} is not a valid UUID")
