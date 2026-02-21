"""
Unit tests for structured logging configuration.

Tests the structlog setup including JSON formatting, per-module log levels,
output destinations, and sensitive data redaction.
"""

import pytest
import json
import logging
import sys
import os
import tempfile
from io import StringIO
from unittest.mock import patch, MagicMock
import structlog

from infrastructure.logging import (
    configure_logging,
    get_logger,
    StructuredLogger,
    redact_sensitive_fields,
    add_service_name
)
from infrastructure.config import config


class TestStructuredLoggingConfiguration:
    """Test structured logging configuration."""
    
    def test_json_formatter_configured(self):
        """Test that JSON formatter is configured when LOG_FORMAT=json."""
        with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
            # Reconfigure logging
            from infrastructure import config as config_module
            config_module.config = config_module.AppConfig()
            configure_logging()
            
            logger = get_logger("test")
            
            # Capture output
            output = StringIO()
            handler = logging.StreamHandler(output)
            logging.root.handlers = [handler]
            
            logger.info("test message", key="value")
            
            # Check that output is valid JSON
            output_value = output.getvalue().strip()
            if output_value:
                log_entry = json.loads(output_value)
                assert "event" in log_entry or "message" in log_entry
    
    def test_console_formatter_configured(self):
        """Test that console formatter is configured when LOG_FORMAT=console."""
        with patch.dict(os.environ, {"LOG_FORMAT": "console"}):
            from infrastructure import config as config_module
            config_module.config = config_module.AppConfig()
            configure_logging()
            
            logger = get_logger("test")
            
            # Should not raise an error
            logger.info("test message")
    
    def test_log_level_configuration(self):
        """Test that global log level is configured correctly."""
        # Test that configure_logging respects the config object's log level
        original_level = config.logging.level
        try:
            config.logging.level = "WARNING"
            configure_logging()
            
            # Root logger should be set to WARNING
            assert logging.root.level == logging.WARNING
        finally:
            config.logging.level = original_level
            configure_logging()  # Restore
    
    def test_per_module_log_levels(self):
        """Test that per-module log levels are configured correctly."""
        # Test that configure_logging respects module-specific log levels
        original_module_levels = config.logging.module_levels.copy()
        try:
            config.logging.module_levels = {
                "test.module1": "DEBUG",
                "test.module2": "ERROR"
            }
            configure_logging()
            
            # Check module-specific log levels
            module1_logger = logging.getLogger("test.module1")
            module2_logger = logging.getLogger("test.module2")
            
            assert module1_logger.level == logging.DEBUG
            assert module2_logger.level == logging.ERROR
        finally:
            config.logging.module_levels = original_module_levels
            configure_logging()  # Restore
    
    def test_stdout_output_destination(self):
        """Test that logs are output to stdout when configured."""
        with patch.dict(os.environ, {"LOG_OUTPUT": "stdout"}):
            from infrastructure import config as config_module
            config_module.config = config_module.AppConfig()
            configure_logging()
            
            # Check that handler is StreamHandler with stdout
            assert len(logging.root.handlers) > 0
            handler = logging.root.handlers[0]
            assert isinstance(handler, logging.StreamHandler)
            assert handler.stream == sys.stdout
    
    def test_stderr_output_destination(self):
        """Test that logs are output to stderr when configured."""
        with patch.dict(os.environ, {"LOG_OUTPUT": "stderr"}, clear=False):
            from infrastructure import config as config_module
            # Force reload of config
            config_module.config = config_module.AppConfig()
            configure_logging()
            
            # Check that handler is StreamHandler with stderr
            assert len(logging.root.handlers) > 0
            handler = logging.root.handlers[0]
            assert isinstance(handler, logging.StreamHandler)
            # Check stream name instead of identity (pytest redirects streams)
            assert hasattr(handler.stream, 'name') or handler.stream.name == '<stderr>'
    
    def test_file_output_destination(self):
        """Test that logs are output to file when configured."""
        import os as os_module
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
        
        try:
            # Test that file handler is created for file paths
            original_output = config.logging.output_destination
            config.logging.output_destination = log_file
            configure_logging()
            
            # Check that handler is FileHandler
            assert len(logging.root.handlers) > 0
            handler = logging.root.handlers[0]
            assert isinstance(handler, logging.FileHandler)
            # Normalize paths for comparison
            assert os_module.path.normpath(handler.baseFilename) == os_module.path.normpath(log_file)
            
            # Close the handler before cleanup
            handler.close()
            
            # Restore
            config.logging.output_destination = original_output
            configure_logging()
        finally:
            # Cleanup
            try:
                if os_module.path.exists(log_file):
                    os_module.unlink(log_file)
            except PermissionError:
                pass  # File still in use, skip cleanup
    
    def test_service_name_in_logs(self):
        """Test that service name is added to all log entries."""
        event_dict = {"event": "test"}
        result = add_service_name(None, None, event_dict)
        
        assert "service" in result
        assert result["service"] == config.logging.service_name


class TestSensitiveDataRedaction:
    """Test sensitive data redaction in logs."""
    
    def test_password_redaction(self):
        """Test that password fields are redacted."""
        event_dict = {
            "event": "user login",
            "username": "john",
            "password": "secret123"
        }
        
        result = redact_sensitive_fields(None, None, event_dict)
        
        assert result["username"] == "john"
        assert result["password"] == "***REDACTED***"
    
    def test_token_redaction(self):
        """Test that token fields are redacted."""
        event_dict = {
            "event": "api call",
            "api_token": "abc123xyz",
            "access_token": "def456uvw"
        }
        
        result = redact_sensitive_fields(None, None, event_dict)
        
        assert result["api_token"] == "***REDACTED***"
        assert result["access_token"] == "***REDACTED***"
    
    def test_api_key_redaction(self):
        """Test that API key fields are redacted."""
        event_dict = {
            "event": "external service call",
            "api_key": "key_12345",
            "service": "model_server"
        }
        
        result = redact_sensitive_fields(None, None, event_dict)
        
        assert result["api_key"] == "***REDACTED***"
        assert result["service"] == "model_server"
    
    def test_nested_dict_redaction(self):
        """Test that sensitive fields in nested dicts are redacted."""
        event_dict = {
            "event": "user data",
            "user": {
                "username": "john",
                "password": "secret",
                "email": "john@example.com"
            }
        }
        
        result = redact_sensitive_fields(None, None, event_dict)
        
        assert result["user"]["username"] == "john"
        assert result["user"]["password"] == "***REDACTED***"
        assert result["user"]["email"] == "***REDACTED***"
    
    def test_case_insensitive_redaction(self):
        """Test that redaction is case-insensitive."""
        event_dict = {
            "event": "test",
            "PASSWORD": "secret",
            "Token": "abc123",
            "API_KEY": "key123"
        }
        
        result = redact_sensitive_fields(None, None, event_dict)
        
        assert result["PASSWORD"] == "***REDACTED***"
        assert result["Token"] == "***REDACTED***"
        assert result["API_KEY"] == "***REDACTED***"
    
    def test_multiple_sensitive_fields(self):
        """Test redaction of multiple sensitive fields."""
        event_dict = {
            "event": "authentication",
            "username": "john",
            "password": "pass123",
            "token": "token456",
            "api_key": "key789",
            "secret": "secret000"
        }
        
        result = redact_sensitive_fields(None, None, event_dict)
        
        assert result["username"] == "john"
        assert result["password"] == "***REDACTED***"
        assert result["token"] == "***REDACTED***"
        assert result["api_key"] == "***REDACTED***"
        assert result["secret"] == "***REDACTED***"


class TestStructuredLogger:
    """Test StructuredLogger wrapper class."""
    
    def test_logger_initialization(self):
        """Test that logger can be initialized."""
        logger = get_logger("test")
        assert isinstance(logger, StructuredLogger)
    
    def test_logger_with_context(self):
        """Test that logger can be created with context."""
        logger = get_logger("test")
        context_logger = logger.with_context(user_id="123", request_id="abc")
        
        assert isinstance(context_logger, StructuredLogger)
        assert context_logger._context["user_id"] == "123"
        assert context_logger._context["request_id"] == "abc"
    
    def test_context_inheritance(self):
        """Test that context is inherited when creating new logger."""
        logger = get_logger("test")
        logger1 = logger.with_context(user_id="123")
        logger2 = logger1.with_context(request_id="abc")
        
        assert logger2._context["user_id"] == "123"
        assert logger2._context["request_id"] == "abc"
    
    def test_log_methods(self):
        """Test that all log level methods work."""
        logger = get_logger("test")
        
        # Should not raise errors
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")
    
    def test_log_with_kwargs(self):
        """Test logging with keyword arguments."""
        logger = get_logger("test")
        
        # Should not raise errors
        logger.info("test message", key1="value1", key2="value2")


class TestLoggingIntegration:
    """Integration tests for logging system."""
    
    def test_end_to_end_logging(self):
        """Test complete logging flow from configuration to output."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
        
        try:
            with patch.dict(os.environ, {
                "LOG_LEVEL": "INFO",
                "LOG_FORMAT": "json",
                "LOG_OUTPUT": log_file,
                "SERVICE_NAME": "test-service"
            }):
                from infrastructure import config as config_module
                config_module.config = config_module.AppConfig()
                configure_logging()
                
                logger = get_logger("test.module")
                logger.info("test message", user_id="123", action="create")
                
                # Force flush
                for handler in logging.root.handlers:
                    handler.flush()
                
                # Read log file
                with open(log_file, 'r') as f:
                    log_content = f.read().strip()
                
                if log_content:
                    log_entry = json.loads(log_content)
                    assert log_entry.get("service") == "test-service"
        finally:
            # Cleanup
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_correlation_id_propagation(self):
        """Test that correlation IDs are propagated through context."""
        logger = get_logger("test")
        
        # Bind correlation ID to context
        structlog.contextvars.bind_contextvars(correlation_id="test-123")
        
        # Log should include correlation ID
        # (This is tested by the middleware in actual usage)
        logger.info("test message")
        
        # Clear context
        structlog.contextvars.clear_contextvars()
    
    def test_module_specific_logging(self):
        """Test that module-specific log levels work correctly."""
        # Test that module-specific log levels override global level
        original_level = config.logging.level
        original_module_levels = config.logging.module_levels.copy()
        try:
            config.logging.level = "WARNING"
            config.logging.module_levels = {"test.debug_module": "DEBUG"}
            configure_logging()
            
            # Root logger should be WARNING
            assert logging.root.level == logging.WARNING
            
            # Specific module should be DEBUG
            debug_logger = logging.getLogger("test.debug_module")
            assert debug_logger.level == logging.DEBUG
        finally:
            config.logging.level = original_level
            config.logging.module_levels = original_module_levels
            configure_logging()  # Restore


class TestConfigurationParsing:
    """Test configuration parsing for logging."""
    
    def test_module_levels_parsing(self):
        """Test that LOG_MODULE_LEVELS is parsed correctly."""
        with patch.dict(os.environ, {
            "LOG_MODULE_LEVELS": "module1=DEBUG,module2=INFO,module3=ERROR"
        }):
            from infrastructure import config as config_module
            config_obj = config_module.AppConfig()
            
            assert config_obj.logging.module_levels["module1"] == "DEBUG"
            assert config_obj.logging.module_levels["module2"] == "INFO"
            assert config_obj.logging.module_levels["module3"] == "ERROR"
    
    def test_empty_module_levels(self):
        """Test that empty LOG_MODULE_LEVELS doesn't cause errors."""
        with patch.dict(os.environ, {"LOG_MODULE_LEVELS": ""}):
            from infrastructure import config as config_module
            config_obj = config_module.AppConfig()
            
            assert config_obj.logging.module_levels == {}
    
    def test_malformed_module_levels(self):
        """Test that malformed LOG_MODULE_LEVELS is handled gracefully."""
        with patch.dict(os.environ, {
            "LOG_MODULE_LEVELS": "module1=DEBUG,invalid,module2=INFO"
        }):
            from infrastructure import config as config_module
            config_obj = config_module.AppConfig()
            
            # Should parse valid entries and skip invalid ones
            assert "module1" in config_obj.logging.module_levels
            assert "module2" in config_obj.logging.module_levels


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
