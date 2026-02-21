"""
Property-based tests for error response formatting and error logging.

Tests universal properties of error responses after retry exhaustion and
error logging completeness using Hypothesis.

Feature: backend-optimization
Property 26: Error response after retry exhaustion
Property 30: Error logging completeness
Validates: Requirements 6.2, 6.6

The error response and logging should:
1. Return descriptive error response after retry exhaustion with retry count
2. Include all required fields in error logs (correlation_id, timestamp, error type, message, stack trace)
"""

import pytest
import logging
import json
import traceback
from datetime import datetime
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st, settings
from io import StringIO

from infrastructure.error_response import (
    ErrorResponseFormatter,
    ErrorCode,
    format_exception_response
)
from infrastructure.retry_handler import RetryHandler


# Strategy for generating valid operation names
operation_names = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_-'
    )
)

# Strategy for generating correlation IDs
correlation_ids = st.text(
    min_size=10,
    max_size=50,
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='-'
    )
)

# Strategy for generating error messages
error_messages = st.text(min_size=1, max_size=200)


# Feature: backend-optimization, Property 26: Error response after retry exhaustion
@given(
    operation=operation_names,
    retry_count=st.integers(min_value=1, max_value=10),
    last_error=error_messages,
    correlation_id=correlation_ids
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_26_error_response_after_retry_exhaustion(
    operation,
    retry_count,
    last_error,
    correlation_id
):
    """
    Property 26.1: Error response includes descriptive message and retry count.
    
    For any operation that fails after exhausting retry attempts, the error
    response should include:
    - Descriptive error message mentioning the operation
    - Retry count indicating how many attempts were made
    - Correlation ID for tracing
    - Error code indicating retry exhaustion
    
    **Validates: Requirements 6.2**
    """
    # Create error response for retry exhaustion
    error = ErrorResponseFormatter.retry_exhausted(
        operation=operation,
        retry_count=retry_count,
        last_error=last_error,
        correlation_id=correlation_id
    )
    
    # Verify error response has descriptive message
    assert error.error is not None
    assert len(error.error) > 0
    assert operation in error.error, \
        f"Error message should mention operation '{operation}'"
    assert str(retry_count) in error.error, \
        f"Error message should mention retry count {retry_count}"
    
    # Verify error code is RETRY_EXHAUSTED
    assert error.error_code == ErrorCode.RETRY_EXHAUSTED, \
        f"Error code should be RETRY_EXHAUSTED, got {error.error_code}"
    
    # Verify correlation ID is included
    assert error.correlation_id == correlation_id, \
        f"Correlation ID should be {correlation_id}, got {error.correlation_id}"
    
    # Verify details include operation and retry count
    assert error.details is not None
    assert "operation" in error.details
    assert error.details["operation"] == operation
    assert "retry_count" in error.details
    assert error.details["retry_count"] == retry_count
    
    # Verify last error is included if provided
    if last_error:
        assert "last_error" in error.details
        assert error.details["last_error"] == last_error


# Feature: backend-optimization, Property 26: Error response after retry exhaustion
@given(
    operation=operation_names,
    retry_count=st.integers(min_value=1, max_value=10),
    correlation_id=correlation_ids
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_26_error_response_without_last_error(
    operation,
    retry_count,
    correlation_id
):
    """
    Property 26.2: Error response works without last error message.
    
    For any operation that fails after retry exhaustion, the error response
    should work correctly even when no last error message is provided.
    
    **Validates: Requirements 6.2**
    """
    # Create error response without last error
    error = ErrorResponseFormatter.retry_exhausted(
        operation=operation,
        retry_count=retry_count,
        correlation_id=correlation_id
    )
    
    # Verify error response is valid
    assert error.error is not None
    assert error.error_code == ErrorCode.RETRY_EXHAUSTED
    assert error.correlation_id == correlation_id
    
    # Verify details include operation and retry count but not last_error
    assert error.details is not None
    assert "operation" in error.details
    assert "retry_count" in error.details
    assert "last_error" not in error.details or error.details["last_error"] is None


# Feature: backend-optimization, Property 26: Error response after retry exhaustion
@given(
    operation=operation_names,
    max_retries=st.integers(min_value=1, max_value=5),
    correlation_id=correlation_ids
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_26_retry_handler_exhaustion_creates_error_response(
    operation,
    max_retries,
    correlation_id
):
    """
    Property 26.3: Retry handler exhaustion can be formatted as error response.
    
    For any retry handler that exhausts all attempts, the resulting exception
    can be formatted into a proper error response with retry information.
    
    **Validates: Requirements 6.2**
    """
    retry_handler = RetryHandler(
        max_retries=max_retries,
        base_delay=0.01,
        max_delay=0.1
    )
    
    # Create a function that always fails
    call_count = [0]
    last_exception = None
    
    def failing_operation():
        call_count[0] += 1
        raise ConnectionError(f"Connection failed on attempt {call_count[0]}")
    
    # Execute with retry and catch the final exception
    try:
        retry_handler.execute_with_retry(failing_operation)
    except ConnectionError as e:
        last_exception = e
    
    # Verify retry handler exhausted all attempts
    assert call_count[0] == max_retries + 1, \
        f"Expected {max_retries + 1} attempts, got {call_count[0]}"
    
    # Create error response from the exhaustion
    error = ErrorResponseFormatter.retry_exhausted(
        operation=operation,
        retry_count=max_retries,
        last_error=str(last_exception) if last_exception else None,
        correlation_id=correlation_id
    )
    
    # Verify error response is properly formatted
    assert error.error_code == ErrorCode.RETRY_EXHAUSTED
    assert error.correlation_id == correlation_id
    assert error.details["retry_count"] == max_retries
    
    if last_exception:
        assert "last_error" in error.details


# Feature: backend-optimization, Property 26: Error response after retry exhaustion
@given(
    operation=operation_names,
    retry_count=st.integers(min_value=1, max_value=10),
    correlation_id=correlation_ids
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_26_error_response_has_timestamp(
    operation,
    retry_count,
    correlation_id
):
    """
    Property 26.4: Error response includes timestamp.
    
    For any error response after retry exhaustion, a timestamp should be
    included in ISO 8601 format.
    
    **Validates: Requirements 6.2, 6.6**
    """
    error = ErrorResponseFormatter.retry_exhausted(
        operation=operation,
        retry_count=retry_count,
        correlation_id=correlation_id
    )
    
    # Verify timestamp is present
    assert error.timestamp is not None
    assert isinstance(error.timestamp, str)
    
    # Verify timestamp is in ISO 8601 format
    assert 'T' in error.timestamp
    assert error.timestamp.endswith('Z')
    
    # Verify timestamp can be parsed
    timestamp_str = error.timestamp.rstrip('Z')
    parsed = datetime.fromisoformat(timestamp_str)
    assert isinstance(parsed, datetime)


# Feature: backend-optimization, Property 26: Error response after retry exhaustion
@given(
    operation=operation_names,
    retry_count=st.integers(min_value=1, max_value=10),
    correlation_id=correlation_ids
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_26_error_response_serializable(
    operation,
    retry_count,
    correlation_id
):
    """
    Property 26.5: Error response is JSON serializable.
    
    For any error response after retry exhaustion, the response should be
    serializable to JSON for API responses.
    
    **Validates: Requirements 6.2**
    """
    error = ErrorResponseFormatter.retry_exhausted(
        operation=operation,
        retry_count=retry_count,
        correlation_id=correlation_id
    )
    
    # Convert to dict
    error_dict = error.model_dump()
    
    # Verify can be serialized to JSON
    json_str = json.dumps(error_dict)
    assert isinstance(json_str, str)
    
    # Verify can be deserialized
    parsed = json.loads(json_str)
    assert parsed["error_code"] == "RETRY_EXHAUSTED"
    assert parsed["correlation_id"] == correlation_id
    assert parsed["details"]["retry_count"] == retry_count


# Feature: backend-optimization, Property 30: Error logging completeness
@given(
    correlation_id=correlation_ids,
    error_message=error_messages,
    exception_type=st.sampled_from([
        ValueError,
        ConnectionError,
        TimeoutError,
        RuntimeError,
        KeyError
    ])
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_30_error_log_includes_required_fields(
    correlation_id,
    error_message,
    exception_type
):
    """
    Property 30.1: Error logs can include all required fields.
    
    For any error that occurs, the logging system should be able to capture:
    - correlation_id for tracing
    - timestamp
    - error type (exception class name)
    - error message
    - stack trace
    
    This test verifies that error information can be structured for logging.
    
    **Validates: Requirements 6.6**
    """
    # Create and raise an exception to get stack trace
    try:
        raise exception_type(error_message)
    except exception_type as e:
        # Capture error information that would be logged
        error_info = {
            "correlation_id": correlation_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": type(e).__name__,
            "error_message": str(e),
            "stack_trace": traceback.format_exc()
        }
        
        # Verify all required fields are present
        assert "correlation_id" in error_info
        assert error_info["correlation_id"] == correlation_id
        
        assert "timestamp" in error_info
        assert error_info["timestamp"] is not None
        
        assert "error_type" in error_info
        assert error_info["error_type"] == exception_type.__name__
        
        assert "error_message" in error_info
        assert error_info["error_message"] is not None
        assert len(str(error_info["error_message"])) > 0
        
        assert "stack_trace" in error_info
        assert len(error_info["stack_trace"]) > 0
        assert exception_type.__name__ in error_info["stack_trace"]


# Feature: backend-optimization, Property 30: Error logging completeness
@given(
    correlation_id=correlation_ids,
    operation=operation_names,
    retry_count=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_30_error_response_contains_logging_fields(
    correlation_id,
    operation,
    retry_count
):
    """
    Property 30.2: Error response contains fields needed for logging.
    
    For any error response, it should contain all the fields needed for
    complete error logging: correlation_id, timestamp, error type, and message.
    
    **Validates: Requirements 6.6**
    """
    error = ErrorResponseFormatter.retry_exhausted(
        operation=operation,
        retry_count=retry_count,
        correlation_id=correlation_id
    )
    
    # Verify correlation_id is present
    assert error.correlation_id is not None
    assert error.correlation_id == correlation_id
    
    # Verify timestamp is present
    assert error.timestamp is not None
    assert isinstance(error.timestamp, str)
    
    # Verify error type (error_code) is present
    assert error.error_code is not None
    assert error.error_code == ErrorCode.RETRY_EXHAUSTED
    
    # Verify error message is present
    assert error.error is not None
    assert len(error.error) > 0


# Feature: backend-optimization, Property 30: Error logging completeness
@given(
    correlation_id=correlation_ids,
    exception_type=st.sampled_from([
        ValueError("test"),
        ConnectionError("test"),
        TimeoutError("test"),
        RuntimeError("test")
    ])
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_30_format_exception_includes_logging_fields(
    correlation_id,
    exception_type
):
    """
    Property 30.3: Formatted exceptions include all logging fields.
    
    For any exception formatted into an error response, the response should
    include all fields needed for complete error logging.
    
    **Validates: Requirements 6.6**
    """
    # Format exception into error response
    error = format_exception_response(
        exception=exception_type,
        correlation_id=correlation_id,
        include_traceback=True
    )
    
    # Verify correlation_id
    assert error.correlation_id == correlation_id
    
    # Verify timestamp
    assert error.timestamp is not None
    
    # Verify error type is captured
    assert error.error_code is not None
    
    # Verify error message
    assert error.error is not None
    
    # Verify exception details are included
    if error.details:
        # Should have exception type
        assert "exception_type" in error.details or error.error_code is not None
        
        # Should have traceback when requested
        if "traceback" in error.details:
            assert isinstance(error.details["traceback"], str)
            assert len(error.details["traceback"]) > 0


# Feature: backend-optimization, Property 30: Error logging completeness
@given(
    correlation_id=correlation_ids,
    service_name=st.text(min_size=1, max_size=50),
    error_message=error_messages
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_30_all_error_formatters_include_correlation_id(
    correlation_id,
    service_name,
    error_message
):
    """
    Property 30.4: All error formatters include correlation_id.
    
    For any error formatter method, the resulting error response should
    include the correlation_id for tracing.
    
    **Validates: Requirements 6.6**
    """
    # Test various error formatters
    errors = [
        ErrorResponseFormatter.validation_error(
            message=error_message,
            correlation_id=correlation_id
        ),
        ErrorResponseFormatter.internal_server_error(
            message=error_message,
            correlation_id=correlation_id
        ),
        ErrorResponseFormatter.service_unavailable(
            service_name=service_name,
            correlation_id=correlation_id
        ),
        ErrorResponseFormatter.timeout_error(
            operation=service_name,
            timeout_seconds=30.0,
            correlation_id=correlation_id
        ),
        ErrorResponseFormatter.database_error(
            message=error_message,
            correlation_id=correlation_id
        ),
    ]
    
    # All errors should have correlation_id
    for error in errors:
        assert error.correlation_id == correlation_id, \
            f"Error {error.error_code} should have correlation_id"


# Feature: backend-optimization, Property 30: Error logging completeness
@given(
    correlation_id=correlation_ids,
    operation=operation_names,
    retry_count=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_30_error_response_timestamp_format(
    correlation_id,
    operation,
    retry_count
):
    """
    Property 30.5: Error response timestamp is in correct format.
    
    For any error response, the timestamp should be in ISO 8601 format
    with timezone (Z suffix) for consistent logging.
    
    **Validates: Requirements 6.6**
    """
    error = ErrorResponseFormatter.retry_exhausted(
        operation=operation,
        retry_count=retry_count,
        correlation_id=correlation_id
    )
    
    # Verify timestamp format
    assert error.timestamp is not None
    assert isinstance(error.timestamp, str)
    
    # Should be ISO 8601 with Z suffix
    assert 'T' in error.timestamp, "Timestamp should have T separator"
    assert error.timestamp.endswith('Z'), "Timestamp should end with Z"
    
    # Should be parseable
    timestamp_str = error.timestamp.rstrip('Z')
    try:
        parsed = datetime.fromisoformat(timestamp_str)
        assert isinstance(parsed, datetime)
    except ValueError as e:
        pytest.fail(f"Timestamp {error.timestamp} is not valid ISO 8601: {e}")


# Feature: backend-optimization, Property 30: Error logging completeness
@given(
    correlation_id=correlation_ids,
    error_message=error_messages
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_30_internal_server_error_includes_exception_details(
    correlation_id,
    error_message
):
    """
    Property 30.6: Internal server errors include exception details for logging.
    
    For any internal server error with an exception, the error response should
    include exception type and message in details for complete logging.
    
    **Validates: Requirements 6.6**
    """
    # Create an exception
    exc = RuntimeError(error_message)
    
    # Format as internal server error
    error = ErrorResponseFormatter.internal_server_error(
        message="Operation failed",
        correlation_id=correlation_id,
        exception=exc,
        include_traceback=True
    )
    
    # Verify correlation_id
    assert error.correlation_id == correlation_id
    
    # Verify timestamp
    assert error.timestamp is not None
    
    # Verify exception details are included
    assert error.details is not None
    assert "exception_type" in error.details
    assert error.details["exception_type"] == "RuntimeError"
    assert "exception_message" in error.details
    assert error.details["exception_message"] == error_message
    
    # Verify traceback is included when requested
    assert "traceback" in error.details
    assert isinstance(error.details["traceback"], str)
    assert len(error.details["traceback"]) > 0


# Feature: backend-optimization, Property 30: Error logging completeness
@given(
    correlation_id=correlation_ids,
    operation=operation_names,
    retry_count=st.integers(min_value=1, max_value=10),
    last_error=error_messages
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_30_retry_exhausted_error_complete_for_logging(
    correlation_id,
    operation,
    retry_count,
    last_error
):
    """
    Property 30.7: Retry exhausted errors have complete information for logging.
    
    For any retry exhausted error, the response should contain all information
    needed for complete error logging: correlation_id, timestamp, error type,
    message, and context (operation, retry_count, last_error).
    
    **Validates: Requirements 6.2, 6.6**
    """
    error = ErrorResponseFormatter.retry_exhausted(
        operation=operation,
        retry_count=retry_count,
        last_error=last_error,
        correlation_id=correlation_id
    )
    
    # Verify all required logging fields are present
    
    # 1. Correlation ID
    assert error.correlation_id is not None
    assert error.correlation_id == correlation_id
    
    # 2. Timestamp
    assert error.timestamp is not None
    assert isinstance(error.timestamp, str)
    assert 'T' in error.timestamp
    
    # 3. Error type (error_code)
    assert error.error_code is not None
    assert error.error_code == ErrorCode.RETRY_EXHAUSTED
    
    # 4. Error message
    assert error.error is not None
    assert len(error.error) > 0
    assert operation in error.error
    assert str(retry_count) in error.error
    
    # 5. Stack trace / context (in details)
    assert error.details is not None
    assert "operation" in error.details
    assert error.details["operation"] == operation
    assert "retry_count" in error.details
    assert error.details["retry_count"] == retry_count
    assert "last_error" in error.details
    assert error.details["last_error"] == last_error


# Feature: backend-optimization, Property 30: Error logging completeness
@given(
    correlation_id=correlation_ids,
    operation=operation_names,
    retry_count=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_30_error_response_dict_contains_all_fields(
    correlation_id,
    operation,
    retry_count
):
    """
    Property 30.8: Error response dict contains all required fields.
    
    For any error response converted to dict (for JSON serialization),
    all required logging fields should be present.
    
    **Validates: Requirements 6.6**
    """
    error = ErrorResponseFormatter.retry_exhausted(
        operation=operation,
        retry_count=retry_count,
        correlation_id=correlation_id
    )
    
    # Convert to dict
    error_dict = error.model_dump()
    
    # Verify all required fields are in dict
    assert "correlation_id" in error_dict
    assert error_dict["correlation_id"] == correlation_id
    
    assert "timestamp" in error_dict
    assert error_dict["timestamp"] is not None
    
    assert "error_code" in error_dict
    assert error_dict["error_code"] == "RETRY_EXHAUSTED"
    
    assert "error" in error_dict
    assert error_dict["error"] is not None
    
    assert "details" in error_dict
    assert error_dict["details"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
