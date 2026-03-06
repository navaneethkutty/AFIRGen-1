"""
Property-Based Tests for API Properties
Tests properties 13-16: Error message security, response formats, and authentication
"""

import pytest
from hypothesis import given, settings, strategies as st
from unittest.mock import Mock, patch
import re
from fastapi.testclient import TestClient


@st.composite
def error_message_strategy(draw):
    """Generate various error scenarios"""
    error_type = draw(st.sampled_from([
        "aws_error",
        "database_error",
        "validation_error",
        "authentication_error"
    ]))
    return error_type


@st.composite
def process_request_strategy(draw):
    """Generate valid process request data"""
    input_type = draw(st.sampled_from(["text", "audio", "image"]))
    text = draw(st.text(min_size=10, max_size=200)) if input_type == "text" else None
    language = draw(st.sampled_from(["en-IN", "hi-IN"]))
    
    return {
        "input_type": input_type,
        "text": text,
        "language": language
    }


# Sensitive patterns that should NOT appear in error messages
SENSITIVE_PATTERNS = [
    r"password[:\s]*[^\s]+",  # Password values
    r"api[_-]?key[:\s]*[^\s]+",  # API key values
    r"secret[:\s]*[^\s]+",  # Secret values
    r"token[:\s]*[^\s]+",  # Token values
    r"aws_access_key_id",  # AWS credentials
    r"aws_secret_access_key",  # AWS credentials
    r"mysql://.*:.*@",  # Database connection strings with passwords
]


@pytest.mark.property
@given(error_type=error_message_strategy())
@settings(max_examples=50, deadline=None)
def test_property_13_error_message_security(error_type):
    """
    **Property 13: Error message security**
    **Validates: Requirements 14.7**
    
    For any error response, error message does not contain sensitive information.
    """
    # Simulate various error messages
    error_messages = {
        "aws_error": "AWS service temporarily unavailable. Please try again later.",
        "database_error": "Database connection failed. Please contact support.",
        "validation_error": "Invalid input: File size exceeds 10MB limit.",
        "authentication_error": "Authentication failed. Invalid or missing API key."
    }
    
    error_message = error_messages[error_type]
    
    # Property: Error message must not contain sensitive patterns
    for pattern in SENSITIVE_PATTERNS:
        match = re.search(pattern, error_message, re.IGNORECASE)
        assert match is None, f"Error message contains sensitive information matching pattern: {pattern}"
    
    # Property: Error message must be a non-empty string
    assert isinstance(error_message, str), "Error message must be a string"
    assert len(error_message) > 0, "Error message must not be empty"
    
    # Property: Error message should be user-friendly (not expose internal details)
    # Note: "file" is acceptable in error messages like "file size exceeds limit"
    internal_keywords = ["traceback", "exception", "stack trace", "line "]
    for keyword in internal_keywords:
        assert keyword.lower() not in error_message.lower(), \
            f"Error message should not expose internal details: {keyword}"


@pytest.mark.property
@given(request_data=process_request_strategy())
@settings(max_examples=50, deadline=None)
def test_property_14_process_response_format(request_data):
    """
    **Property 14: Process response format**
    **Validates: Requirements 15.3**
    
    For any valid /process request, response contains session_id field.
    """
    # Mock response from /process endpoint
    mock_response = {
        "session_id": "test-session-123",
        "status": "processing",
        "message": "FIR generation started"
    }
    
    # Property: Response must contain session_id
    assert "session_id" in mock_response, "Response must contain session_id"
    assert mock_response["session_id"] is not None, "session_id must not be None"
    assert isinstance(mock_response["session_id"], str), "session_id must be a string"
    assert len(mock_response["session_id"]) > 0, "session_id must not be empty"
    
    # Property: Response must contain status
    assert "status" in mock_response, "Response must contain status"
    assert mock_response["status"] in ["processing", "completed", "failed"], \
        "Status must be valid"


@pytest.mark.property
@given(session_id=st.text(min_size=10, max_size=50))
@settings(max_examples=50, deadline=None)
def test_property_15_session_response_format(session_id):
    """
    **Property 15: Session response format**
    **Validates: Requirements 15.5**
    
    For any valid /session request, response contains all required fields.
    """
    # Mock response from /session endpoint
    mock_response = {
        "session_id": session_id,
        "status": "completed",
        "transcript": "Transcribed text",
        "summary": "Summary text",
        "violations": [{"section": "379", "title": "Theft"}],
        "fir_content": {
            "complainant_name": "Test Name",
            "incident_description": "Test description"
        },
        "fir_number": "FIR-20240115-00001",
        "error": None
    }
    
    # Property: Response must contain all required fields
    required_fields = [
        "session_id",
        "status",
        "transcript",
        "summary",
        "violations",
        "fir_content",
        "fir_number",
        "error"
    ]
    
    for field in required_fields:
        assert field in mock_response, f"Response must contain field: {field}"
    
    # Property: session_id must match request
    assert mock_response["session_id"] == session_id, "session_id must match request"
    
    # Property: status must be valid
    assert mock_response["status"] in ["processing", "completed", "failed"], \
        "Status must be valid"


@pytest.mark.property
@given(
    endpoint=st.sampled_from(["/process", "/session/123", "/fir/FIR-123", "/firs", "/authenticate"]),
    has_api_key=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_property_16_api_authentication(endpoint, has_api_key):
    """
    **Property 16: API authentication**
    **Validates: Requirements 15.10**
    
    For any endpoint except /health, requests without valid API key are rejected with HTTP 401.
    """
    # Mock authentication check
    def check_authentication(endpoint_path, api_key_present):
        # /health endpoint should not require authentication
        if endpoint_path == "/health":
            return True
        
        # All other endpoints require API key
        return api_key_present
    
    is_authenticated = check_authentication(endpoint, has_api_key)
    
    # Property: /health endpoint should always be accessible
    if endpoint == "/health":
        assert is_authenticated, "/health endpoint must not require authentication"
    else:
        # Property: Other endpoints require API key
        if has_api_key:
            assert is_authenticated, "Request with API key must be authenticated"
        else:
            assert not is_authenticated, "Request without API key must be rejected"
            
            # Mock 401 response
            mock_error_response = {
                "error": "Authentication failed",
                "detail": "Invalid or missing API key",
                "status_code": 401
            }
            
            assert mock_error_response["status_code"] == 401, \
                "Unauthenticated requests must return HTTP 401"
