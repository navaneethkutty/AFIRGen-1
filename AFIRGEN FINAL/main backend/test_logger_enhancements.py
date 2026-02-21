"""
Test enhancements to structured logger for task 10.4.

Tests:
1. Required fields (timestamp, level, service, message)
2. Context injection for correlation IDs
3. Sensitive data redaction
"""

import json
import logging
from io import StringIO
import structlog
import pytest

from infrastructure.logging import get_logger, configure_logging


class TestRequiredFields:
    """Test that all required fields are present in log output."""
    
    def setup_method(self):
        """Set up test fixtures."""
        configure_logging()
        self.output = StringIO()
        handler = logging.StreamHandler(self.output)
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        root_logger = logging.getLogger()
        root_logger.handlers = [handler]
    
    def teardown_method(self):
        """Clean up after tests."""
        structlog.contextvars.clear_contextvars()
    
    def get_log_entry(self) -> dict:
        """Get the parsed log entry from output."""
        log_output = self.output.getvalue().strip()
        if log_output:
            return json.loads(log_output)
        return {}
    
    def test_timestamp_field_present(self):
        """Test that timestamp field is present in log output."""
        logger = get_logger("test")
        logger.info("Test message")
        
        log_entry = self.get_log_entry()
        assert "timestamp" in log_entry
        assert log_entry["timestamp"]  # Not empty
        # Verify ISO format (basic check)
        assert "T" in log_entry["timestamp"]
        assert "Z" in log_entry["timestamp"]
    
    def test_level_field_present(self):
        """Test that level field is present in log output."""
        logger = get_logger("test")
        logger.info("Test message")
        
        log_entry = self.get_log_entry()
        assert "level" in log_entry
        assert log_entry["level"] == "info"
    
    def test_service_field_present(self):
        """Test that service field is present in log output."""
        logger = get_logger("test")
        logger.info("Test message")
        
        log_entry = self.get_log_entry()
        assert "service" in log_entry
        assert log_entry["service"]  # Not empty
    
    def test_message_field_present(self):
        """Test that message field is present (not 'event')."""
        logger = get_logger("test")
        logger.info("Test message content")
        
        log_entry = self.get_log_entry()
        assert "message" in log_entry
        assert log_entry["message"] == "Test message content"
        # Ensure 'event' is not used
        assert "event" not in log_entry
    
    def test_all_required_fields_together(self):
        """Test that all required fields are present together."""
        logger = get_logger("test")
        logger.info("Complete test")
        
        log_entry = self.get_log_entry()
        required_fields = ["timestamp", "level", "service", "message"]
        
        for field in required_fields:
            assert field in log_entry, f"Required field '{field}' is missing"
            assert log_entry[field], f"Required field '{field}' is empty"


class TestCorrelationIDInjection:
    """Test correlation ID injection functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        configure_logging()
        self.output = StringIO()
        handler = logging.StreamHandler(self.output)
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        root_logger = logging.getLogger()
        root_logger.handlers = [handler]
    
    def teardown_method(self):
        """Clean up after tests."""
        structlog.contextvars.clear_contextvars()
    
    def get_log_entry(self) -> dict:
        """Get the parsed log entry from output."""
        log_output = self.output.getvalue().strip()
        if log_output:
            return json.loads(log_output)
        return {}
    
    def test_correlation_id_via_contextvars(self):
        """Test correlation ID injection via structlog contextvars."""
        logger = get_logger("test")
        
        # Bind correlation ID
        structlog.contextvars.bind_contextvars(correlation_id="test-corr-123")
        
        logger.info("Test message")
        
        log_entry = self.get_log_entry()
        assert "correlation_id" in log_entry
        assert log_entry["correlation_id"] == "test-corr-123"
    
    def test_correlation_id_via_with_context(self):
        """Test correlation ID injection via with_context method."""
        logger = get_logger("test")
        logger_with_context = logger.with_context(correlation_id="ctx-456")
        
        logger_with_context.info("Test message")
        
        log_entry = self.get_log_entry()
        assert "correlation_id" in log_entry
        assert log_entry["correlation_id"] == "ctx-456"
    
    def test_correlation_id_via_with_correlation_id(self):
        """Test correlation ID injection via with_correlation_id convenience method."""
        logger = get_logger("test")
        logger_with_corr = logger.with_correlation_id("conv-789")
        
        logger_with_corr.info("Test message")
        
        log_entry = self.get_log_entry()
        assert "correlation_id" in log_entry
        assert log_entry["correlation_id"] == "conv-789"
    
    def test_correlation_id_propagation(self):
        """Test that correlation ID is propagated through multiple log calls."""
        logger = get_logger("test")
        logger_with_corr = logger.with_correlation_id("prop-abc")
        
        # First log
        logger_with_corr.info("First message")
        log1 = self.get_log_entry()
        
        # Clear output for second log
        self.output.truncate(0)
        self.output.seek(0)
        
        # Second log
        logger_with_corr.info("Second message")
        log2 = self.get_log_entry()
        
        # Both should have the same correlation ID
        assert log1["correlation_id"] == "prop-abc"
        assert log2["correlation_id"] == "prop-abc"
    
    def test_multiple_context_fields_with_correlation_id(self):
        """Test that correlation ID works alongside other context fields."""
        logger = get_logger("test")
        logger_with_context = logger.with_correlation_id("multi-123").with_context(
            user_id="user_456",
            action="test_action"
        )
        
        logger_with_context.info("Test message")
        
        log_entry = self.get_log_entry()
        assert log_entry["correlation_id"] == "multi-123"
        assert log_entry["user_id"] == "user_456"
        assert log_entry["action"] == "test_action"


class TestSensitiveDataRedaction:
    """Test sensitive data redaction functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        configure_logging()
        self.output = StringIO()
        handler = logging.StreamHandler(self.output)
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        root_logger = logging.getLogger()
        root_logger.handlers = [handler]
    
    def teardown_method(self):
        """Clean up after tests."""
        structlog.contextvars.clear_contextvars()
    
    def get_log_entry(self) -> dict:
        """Get the parsed log entry from output."""
        log_output = self.output.getvalue().strip()
        if log_output:
            return json.loads(log_output)
        return {}
    
    def test_password_redaction(self):
        """Test that password fields are redacted."""
        logger = get_logger("test")
        logger.info("User login", username="john", password="secret123")
        
        log_entry = self.get_log_entry()
        assert log_entry["username"] == "john"
        assert log_entry["password"] == "***REDACTED***"
    
    def test_token_redaction(self):
        """Test that token fields are redacted."""
        logger = get_logger("test")
        logger.info("API call", api_token="abc123", access_token="xyz789")
        
        log_entry = self.get_log_entry()
        assert log_entry["api_token"] == "***REDACTED***"
        assert log_entry["access_token"] == "***REDACTED***"
    
    def test_api_key_redaction(self):
        """Test that API key fields are redacted."""
        logger = get_logger("test")
        logger.info("External call", api_key="key_12345", service_name="model_server")
        
        log_entry = self.get_log_entry()
        assert log_entry["api_key"] == "***REDACTED***"
        assert log_entry["service_name"] == "model_server"
        # Note: "service" is a reserved field for the service name from config
    
    def test_email_redaction(self):
        """Test that email fields are redacted."""
        logger = get_logger("test")
        logger.info("User data", username="john", email="john@example.com")
        
        log_entry = self.get_log_entry()
        assert log_entry["username"] == "john"
        assert log_entry["email"] == "***REDACTED***"
    
    def test_multiple_sensitive_fields(self):
        """Test redaction of multiple sensitive fields at once."""
        logger = get_logger("test")
        logger.info(
            "Authentication",
            username="john",
            password="pass123",
            token="token456",
            api_key="key789"
        )
        
        log_entry = self.get_log_entry()
        assert log_entry["username"] == "john"
        assert log_entry["password"] == "***REDACTED***"
        assert log_entry["token"] == "***REDACTED***"
        assert log_entry["api_key"] == "***REDACTED***"


class TestIntegration:
    """Integration tests combining all features."""
    
    def setup_method(self):
        """Set up test fixtures."""
        configure_logging()
        self.output = StringIO()
        handler = logging.StreamHandler(self.output)
        handler.setFormatter(logging.Formatter("%(message)s"))
        
        root_logger = logging.getLogger()
        root_logger.handlers = [handler]
    
    def teardown_method(self):
        """Clean up after tests."""
        structlog.contextvars.clear_contextvars()
    
    def get_log_entry(self) -> dict:
        """Get the parsed log entry from output."""
        log_output = self.output.getvalue().strip()
        if log_output:
            return json.loads(log_output)
        return {}
    
    def test_complete_logging_flow(self):
        """Test complete logging flow with all features."""
        logger = get_logger("test.service")
        
        # Create logger with correlation ID and context
        request_logger = logger.with_correlation_id("req-abc-123").with_context(
            user_id="user_789",
            endpoint="/api/fir"
        )
        
        # Log with sensitive data
        request_logger.info(
            "User authentication",
            username="john",
            password="secret",
            action="login"
        )
        
        log_entry = self.get_log_entry()
        
        # Verify required fields
        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "service" in log_entry
        assert "message" in log_entry
        
        # Verify correlation ID
        assert log_entry["correlation_id"] == "req-abc-123"
        
        # Verify context
        assert log_entry["user_id"] == "user_789"
        assert log_entry["endpoint"] == "/api/fir"
        
        # Verify sensitive data redaction
        assert log_entry["username"] == "john"
        assert log_entry["password"] == "***REDACTED***"
        
        # Verify non-sensitive data
        assert log_entry["action"] == "login"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
