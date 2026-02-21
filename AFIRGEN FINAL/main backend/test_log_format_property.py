"""
Property-based tests for log format and redaction.

Tests universal properties of JSON log format, required log fields,
and sensitive data redaction using Hypothesis.

Feature: backend-optimization
Property 33: JSON log format
Property 34: Required log fields
Property 35: Sensitive data redaction
Validates: Requirements 7.3, 7.4, 7.5

The structured logging system should:
1. Output logs in valid JSON format
2. Include required fields (timestamp, level, service, message) in all logs
3. Redact sensitive data (passwords, tokens, API keys, etc.)
"""

import pytest
import json
import logging
import os
from io import StringIO
from unittest.mock import patch
from hypothesis import given, strategies as st, settings, assume
import structlog

from infrastructure.logging import (
    configure_logging,
    get_logger,
    redact_sensitive_fields,
    add_service_name,
    rename_event_to_message
)
from infrastructure.config import config


# Strategies for generating test data
log_messages = st.text(min_size=1, max_size=200)

log_levels = st.sampled_from(["debug", "info", "warning", "error", "critical"])

# Strategy for context data (non-sensitive)
context_keys = st.text(
    min_size=1,
    max_size=20,
    alphabet='abcdefghijklmnopqrstuvwxyz_'
)

context_values = st.one_of(
    st.text(max_size=100),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.booleans()
)

# Strategy for sensitive field names
sensitive_field_names = st.sampled_from([
    "password", "token", "api_key", "secret", "authorization",
    "credit_card", "ssn", "phone", "email",
    "PASSWORD", "Token", "API_KEY", "Secret",  # Case variations
    "user_password", "access_token", "api_key_value"  # With prefixes/suffixes
])

# Strategy for sensitive values
sensitive_values = st.text(min_size=1, max_size=100)


def capture_log_output(logger_func, *args, **kwargs):
    """Capture log output to a string buffer."""
    output = StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(logging.Formatter("%(message)s"))
    
    # Temporarily replace handlers
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    root_logger.handlers = [handler]
    
    try:
        logger_func(*args, **kwargs)
        handler.flush()
        return output.getvalue().strip()
    finally:
        root_logger.handlers = original_handlers


# Feature: backend-optimization, Property 33: JSON log format
@given(
    message=log_messages,
    level=log_levels
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_33_logs_are_valid_json(message, level):
    """
    Property 33.1: All log entries are valid JSON.
    
    For any log message at any log level, the output should be valid JSON
    that can be parsed without errors.
    
    **Validates: Requirements 7.3**
    """
    # Filter out empty messages
    assume(len(message.strip()) > 0)
    
    # Configure JSON logging
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        from infrastructure import config as config_module
        config_module.config = config_module.AppConfig()
        configure_logging()
        
        logger = get_logger("test")
        
        # Capture log output
        log_method = getattr(logger, level)
        output = capture_log_output(log_method, message)
        
        if output:
            # Should be valid JSON
            try:
                log_entry = json.loads(output)
                assert isinstance(log_entry, dict), \
                    "Log entry should be a JSON object"
            except json.JSONDecodeError as e:
                pytest.fail(f"Log output is not valid JSON: {e}\nOutput: {output}")


# Feature: backend-optimization, Property 33: JSON log format
@given(
    message=log_messages,
    num_context_items=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_33_json_format_with_context(message, num_context_items):
    """
    Property 33.2: Logs with context data are valid JSON.
    
    For any log message with additional context data, the output should
    be valid JSON with all context fields properly serialized.
    
    **Validates: Requirements 7.3**
    """
    # Filter out empty messages
    assume(len(message.strip()) > 0)
    
    # Generate context data
    context = {
        f"key_{i}": f"value_{i}"
        for i in range(num_context_items)
    }
    
    # Configure JSON logging
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        from infrastructure import config as config_module
        config_module.config = config_module.AppConfig()
        configure_logging()
        
        logger = get_logger("test")
        
        # Capture log output
        output = capture_log_output(logger.info, message, **context)
        
        if output:
            # Should be valid JSON
            try:
                log_entry = json.loads(output)
                assert isinstance(log_entry, dict), \
                    "Log entry should be a JSON object"
                
                # Context fields should be present
                for key, value in context.items():
                    assert key in log_entry, \
                        f"Context field '{key}' should be in log entry"
                    assert log_entry[key] == value, \
                        f"Context field '{key}' should have value '{value}'"
            except json.JSONDecodeError as e:
                pytest.fail(f"Log output is not valid JSON: {e}\nOutput: {output}")


# Feature: backend-optimization, Property 33: JSON log format
@given(
    messages=st.lists(log_messages, min_size=2, max_size=10)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_33_multiple_logs_are_valid_json(messages):
    """
    Property 33.3: Multiple consecutive log entries are all valid JSON.
    
    For any sequence of log messages, each log entry should be valid JSON
    on its own line.
    
    **Validates: Requirements 7.3**
    """
    # Filter out empty messages
    messages = [m for m in messages if len(m.strip()) > 0]
    assume(len(messages) >= 2)
    
    # Configure JSON logging
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        from infrastructure import config as config_module
        config_module.config = config_module.AppConfig()
        configure_logging()
        
        logger = get_logger("test")
        
        # Capture multiple log outputs
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers[:]
        root_logger.handlers = [handler]
        
        try:
            for message in messages:
                logger.info(message)
            handler.flush()
            
            log_output = output.getvalue()
            
            if log_output:
                # Split by newlines and parse each line
                lines = [line.strip() for line in log_output.split('\n') if line.strip()]
                
                for line in lines:
                    try:
                        log_entry = json.loads(line)
                        assert isinstance(log_entry, dict), \
                            "Each log entry should be a JSON object"
                    except json.JSONDecodeError as e:
                        pytest.fail(f"Log line is not valid JSON: {e}\nLine: {line}")
        finally:
            root_logger.handlers = original_handlers


# Feature: backend-optimization, Property 34: Required log fields
@given(
    message=log_messages,
    level=log_levels
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_34_required_fields_present(message, level):
    """
    Property 34.1: All log entries include required fields.
    
    For any log message, the JSON output should include the four required
    fields: timestamp, level, service, and message.
    
    **Validates: Requirements 7.4**
    """
    # Filter out empty messages
    assume(len(message.strip()) > 0)
    
    # Configure JSON logging
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        from infrastructure import config as config_module
        config_module.config = config_module.AppConfig()
        configure_logging()
        
        logger = get_logger("test")
        
        # Capture log output
        log_method = getattr(logger, level)
        output = capture_log_output(log_method, message)
        
        if output:
            log_entry = json.loads(output)
            
            # Check required fields
            required_fields = ["timestamp", "level", "service", "message"]
            for field in required_fields:
                assert field in log_entry, \
                    f"Required field '{field}' missing from log entry"
                assert log_entry[field] is not None, \
                    f"Required field '{field}' should not be None"
                assert log_entry[field] != "", \
                    f"Required field '{field}' should not be empty"


# Feature: backend-optimization, Property 34: Required log fields
@given(
    message=log_messages,
    level=log_levels
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_34_timestamp_format(message, level):
    """
    Property 34.2: Timestamp field is in ISO 8601 format.
    
    For any log message, the timestamp field should be a valid ISO 8601
    formatted timestamp.
    
    **Validates: Requirements 7.4**
    """
    # Filter out empty messages
    assume(len(message.strip()) > 0)
    
    # Configure JSON logging
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        from infrastructure import config as config_module
        config_module.config = config_module.AppConfig()
        configure_logging()
        
        logger = get_logger("test")
        
        # Capture log output
        log_method = getattr(logger, level)
        output = capture_log_output(log_method, message)
        
        if output:
            log_entry = json.loads(output)
            
            timestamp = log_entry.get("timestamp")
            assert timestamp is not None, "Timestamp should be present"
            
            # Should be parseable as ISO 8601
            from datetime import datetime
            try:
                # Try parsing with various ISO 8601 formats
                parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                assert parsed is not None, "Timestamp should be parseable"
            except (ValueError, AttributeError) as e:
                pytest.fail(f"Timestamp '{timestamp}' is not valid ISO 8601: {e}")


# Feature: backend-optimization, Property 34: Required log fields
@given(
    message=log_messages,
    level=log_levels
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_34_level_field_matches_log_level(message, level):
    """
    Property 34.3: Level field matches the log level used.
    
    For any log message at a specific level, the level field in the JSON
    output should match the log level used.
    
    **Validates: Requirements 7.4**
    """
    # Filter out empty messages
    assume(len(message.strip()) > 0)
    
    # Configure JSON logging
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        from infrastructure import config as config_module
        config_module.config = config_module.AppConfig()
        configure_logging()
        
        logger = get_logger("test")
        
        # Capture log output
        log_method = getattr(logger, level)
        output = capture_log_output(log_method, message)
        
        if output:
            log_entry = json.loads(output)
            
            log_level = log_entry.get("level")
            assert log_level is not None, "Level field should be present"
            assert log_level.lower() == level.lower(), \
                f"Level field should be '{level}', got '{log_level}'"


# Feature: backend-optimization, Property 34: Required log fields
@given(
    message=log_messages
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_34_service_field_from_config(message):
    """
    Property 34.4: Service field matches configured service name.
    
    For any log message, the service field should match the service name
    from the configuration.
    
    **Validates: Requirements 7.4**
    """
    # Filter out empty messages
    assume(len(message.strip()) > 0)
    
    # Configure JSON logging
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        from infrastructure import config as config_module
        config_module.config = config_module.AppConfig()
        configure_logging()
        
        logger = get_logger("test")
        
        # Capture log output
        output = capture_log_output(logger.info, message)
        
        if output:
            log_entry = json.loads(output)
            
            service = log_entry.get("service")
            assert service is not None, "Service field should be present"
            # Service should match the configured service name (from config)
            expected_service = config_module.config.logging.service_name
            assert service == expected_service, \
                f"Service field should be '{expected_service}', got '{service}'"


# Feature: backend-optimization, Property 34: Required log fields
@given(
    message=log_messages,
    num_context_items=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=20, deadline=None)
@pytest.mark.property_test
def test_property_34_required_fields_with_context(message, num_context_items):
    """
    Property 34.5: Required fields present even with additional context.
    
    For any log message with additional context data, the required fields
    should still be present alongside the context fields.
    
    **Validates: Requirements 7.4**
    """
    # Filter out empty messages
    assume(len(message.strip()) > 0)
    
    # Generate context data
    context = {
        f"context_key_{i}": f"context_value_{i}"
        for i in range(num_context_items)
    }
    
    # Configure JSON logging
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        from infrastructure import config as config_module
        config_module.config = config_module.AppConfig()
        configure_logging()
        
        logger = get_logger("test")
        
        # Capture log output
        output = capture_log_output(logger.info, message, **context)
        
        if output:
            log_entry = json.loads(output)
            
            # Check required fields
            required_fields = ["timestamp", "level", "service", "message"]
            for field in required_fields:
                assert field in log_entry, \
                    f"Required field '{field}' missing even with context"
            
            # Check context fields
            for key in context.keys():
                assert key in log_entry, \
                    f"Context field '{key}' should be present"


# Feature: backend-optimization, Property 35: Sensitive data redaction
@given(
    message=log_messages,
    sensitive_field=sensitive_field_names,
    sensitive_value=sensitive_values
)
@settings(max_examples=30, deadline=None)
@pytest.mark.property_test
def test_property_35_sensitive_fields_redacted(message, sensitive_field, sensitive_value):
    """
    Property 35.1: Sensitive fields are redacted in logs.
    
    For any log message containing sensitive fields (password, token, api_key,
    etc.), those fields should be redacted with "***REDACTED***".
    
    **Validates: Requirements 7.5**
    """
    # Filter out empty messages and values
    assume(len(message.strip()) > 0)
    assume(len(sensitive_value.strip()) > 0)
    # Ensure message and sensitive value are different to avoid collision
    assume(message != sensitive_value)
    
    # Configure JSON logging
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        from infrastructure import config as config_module
        config_module.config = config_module.AppConfig()
        configure_logging()
        
        logger = get_logger("test")
        
        # Create context with sensitive field
        context = {sensitive_field: sensitive_value}
        
        # Capture log output
        output = capture_log_output(logger.info, message, **context)
        
        if output:
            log_entry = json.loads(output)
            
            # Sensitive field should be redacted
            if sensitive_field in log_entry:
                assert log_entry[sensitive_field] == "***REDACTED***", \
                    f"Sensitive field '{sensitive_field}' should be redacted, got '{log_entry[sensitive_field]}'"
            
            # Original value should not appear in the sensitive field's value
            # (it may appear in the message field, which is acceptable)
            if sensitive_field in log_entry:
                assert log_entry[sensitive_field] != sensitive_value, \
                    f"Sensitive value should be redacted in field '{sensitive_field}'"


# Feature: backend-optimization, Property 35: Sensitive data redaction
@given(
    message=log_messages,
    num_sensitive_fields=st.integers(min_value=2, max_value=5)
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_35_multiple_sensitive_fields_redacted(message, num_sensitive_fields):
    """
    Property 35.2: Multiple sensitive fields are all redacted.
    
    For any log message containing multiple sensitive fields, all of them
    should be redacted.
    
    **Validates: Requirements 7.5**
    """
    # Filter out empty messages
    assume(len(message.strip()) > 0)
    
    # Create multiple sensitive fields
    sensitive_fields = ["password", "token", "api_key", "secret", "credit_card"][:num_sensitive_fields]
    context = {field: f"sensitive_{field}_value" for field in sensitive_fields}
    
    # Configure JSON logging
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        from infrastructure import config as config_module
        config_module.config = config_module.AppConfig()
        configure_logging()
        
        logger = get_logger("test")
        
        # Capture log output
        output = capture_log_output(logger.info, message, **context)
        
        if output:
            log_entry = json.loads(output)
            
            # All sensitive fields should be redacted
            for field in sensitive_fields:
                if field in log_entry:
                    assert log_entry[field] == "***REDACTED***", \
                        f"Sensitive field '{field}' should be redacted"
                
                # Original values should not appear
                original_value = f"sensitive_{field}_value"
                assert original_value not in output, \
                    f"Sensitive value for '{field}' should not appear in output"


# Feature: backend-optimization, Property 35: Sensitive data redaction
@given(
    message=log_messages,
    sensitive_field=sensitive_field_names,
    sensitive_value=sensitive_values
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_35_nested_sensitive_fields_redacted(message, sensitive_field, sensitive_value):
    """
    Property 35.3: Sensitive fields in nested dictionaries are redacted.
    
    For any log message with nested context containing sensitive fields,
    those fields should be redacted even when nested.
    
    **Validates: Requirements 7.5**
    """
    # Filter out empty messages and values
    assume(len(message.strip()) > 0)
    assume(len(sensitive_value.strip()) > 0)
    # Ensure message and sensitive value are different to avoid collision
    assume(message != sensitive_value)
    
    # Configure JSON logging
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        from infrastructure import config as config_module
        config_module.config = config_module.AppConfig()
        configure_logging()
        
        logger = get_logger("test")
        
        # Create nested context with sensitive field
        context = {
            "user_data": {
                "username": "testuser",
                sensitive_field: sensitive_value
            }
        }
        
        # Capture log output
        output = capture_log_output(logger.info, message, **context)
        
        if output:
            log_entry = json.loads(output)
            
            # Check nested sensitive field is redacted
            if "user_data" in log_entry and isinstance(log_entry["user_data"], dict):
                user_data = log_entry["user_data"]
                if sensitive_field in user_data:
                    assert user_data[sensitive_field] == "***REDACTED***", \
                        f"Nested sensitive field '{sensitive_field}' should be redacted"
                    # Verify the value is actually redacted, not the original
                    assert user_data[sensitive_field] != sensitive_value, \
                        f"Nested sensitive field should not contain original value"


# Feature: backend-optimization, Property 35: Sensitive data redaction
@given(
    message=log_messages,
    sensitive_value=sensitive_values,
    non_sensitive_value=st.text(min_size=1, max_size=100)
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_35_non_sensitive_fields_not_redacted(message, sensitive_value, non_sensitive_value):
    """
    Property 35.4: Non-sensitive fields are not redacted.
    
    For any log message with both sensitive and non-sensitive fields,
    only the sensitive fields should be redacted while non-sensitive
    fields remain unchanged.
    
    **Validates: Requirements 7.5**
    """
    # Filter out empty messages and values
    assume(len(message.strip()) > 0)
    assume(len(sensitive_value.strip()) > 0)
    assume(len(non_sensitive_value.strip()) > 0)
    
    # Configure JSON logging
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        from infrastructure import config as config_module
        config_module.config = config_module.AppConfig()
        configure_logging()
        
        logger = get_logger("test")
        
        # Create context with both sensitive and non-sensitive fields
        context = {
            "password": sensitive_value,
            "username": non_sensitive_value,
            "user_id": "12345"
        }
        
        # Capture log output
        output = capture_log_output(logger.info, message, **context)
        
        if output:
            log_entry = json.loads(output)
            
            # Sensitive field should be redacted
            if "password" in log_entry:
                assert log_entry["password"] == "***REDACTED***", \
                    "Password should be redacted"
            
            # Non-sensitive fields should not be redacted
            if "username" in log_entry:
                assert log_entry["username"] == non_sensitive_value, \
                    f"Username should not be redacted, expected '{non_sensitive_value}'"
            
            if "user_id" in log_entry:
                assert log_entry["user_id"] == "12345", \
                    "User ID should not be redacted"


# Feature: backend-optimization, Property 35: Sensitive data redaction
@given(
    message=log_messages,
    sensitive_field=sensitive_field_names
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_35_case_insensitive_redaction(message, sensitive_field):
    """
    Property 35.5: Redaction is case-insensitive.
    
    For any sensitive field name in any case (lowercase, uppercase, mixed),
    the field should be redacted.
    
    **Validates: Requirements 7.5**
    """
    # Filter out empty messages
    assume(len(message.strip()) > 0)
    
    # Configure JSON logging
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        from infrastructure import config as config_module
        config_module.config = config_module.AppConfig()
        configure_logging()
        
        logger = get_logger("test")
        
        # Test with the field as-is
        context = {sensitive_field: "sensitive_value"}
        
        # Capture log output
        output = capture_log_output(logger.info, message, **context)
        
        if output:
            log_entry = json.loads(output)
            
            # Field should be redacted regardless of case
            if sensitive_field in log_entry:
                assert log_entry[sensitive_field] == "***REDACTED***", \
                    f"Sensitive field '{sensitive_field}' should be redacted (case-insensitive)"
            
            # Original value should not appear
            assert "sensitive_value" not in output, \
                "Sensitive value should not appear in output"


# Feature: backend-optimization, Property 35: Sensitive data redaction
@given(
    message=log_messages
)
@settings(max_examples=25, deadline=None)
@pytest.mark.property_test
def test_property_35_common_sensitive_fields_redacted(message):
    """
    Property 35.6: All common sensitive field types are redacted.
    
    For any log message, common sensitive field types (password, token,
    api_key, secret, authorization, credit_card, ssn, phone, email)
    should all be redacted.
    
    **Validates: Requirements 7.5**
    """
    # Filter out empty messages
    assume(len(message.strip()) > 0)
    
    # Configure JSON logging
    with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
        from infrastructure import config as config_module
        config_module.config = config_module.AppConfig()
        configure_logging()
        
        logger = get_logger("test")
        
        # Test all common sensitive fields
        sensitive_fields = [
            "password", "token", "api_key", "secret", "authorization",
            "credit_card", "ssn", "phone", "email"
        ]
        
        context = {field: f"value_{field}" for field in sensitive_fields}
        
        # Capture log output
        output = capture_log_output(logger.info, message, **context)
        
        if output:
            log_entry = json.loads(output)
            
            # All sensitive fields should be redacted
            for field in sensitive_fields:
                if field in log_entry:
                    assert log_entry[field] == "***REDACTED***", \
                        f"Common sensitive field '{field}' should be redacted"
                
                # Original values should not appear
                original_value = f"value_{field}"
                assert original_value not in output, \
                    f"Sensitive value for '{field}' should not appear in output"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
