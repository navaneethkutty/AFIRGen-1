"""
Unit tests for StructuredLogger.
Tests JSON logging, PII filtering, and correlation IDs.
"""

import pytest
import json
import logging
from unittest.mock import Mock, patch

from services.monitoring.logger import (
    StructuredLogger,
    PIIFilter,
    JSONFormatter,
    get_logger
)


class TestPIIFilter:
    """Test suite for PIIFilter."""
    
    def test_redact_phone_numbers(self):
        """Test phone numbers are redacted."""
        pii_filter = PIIFilter()
        
        text = "Contact: 9876543210"
        redacted = pii_filter._redact_pii(text)
        
        assert "9876543210" not in redacted
        assert "[PHONE_REDACTED]" in redacted
    
    def test_redact_emails(self):
        """Test email addresses are redacted."""
        pii_filter = PIIFilter()
        
        text = "Email: user@example.com"
        redacted = pii_filter._redact_pii(text)
        
        assert "user@example.com" not in redacted
        assert "[EMAIL_REDACTED]" in redacted
    
    def test_redact_aadhaar_numbers(self):
        """Test Aadhaar numbers are redacted."""
        pii_filter = PIIFilter()
        
        text = "Aadhaar: 1234 5678 9012"
        redacted = pii_filter._redact_pii(text)
        
        assert "1234 5678 9012" not in redacted
        assert "[AADHAAR_REDACTED]" in redacted
    
    def test_redact_multiple_pii_types(self):
        """Test multiple PII types are redacted."""
        pii_filter = PIIFilter()
        
        # Use spaced Aadhaar format to avoid phone pattern matching
        text = "Contact: 9876543210, Email: user@example.com, Aadhaar: 1234 5678 9012"
        redacted = pii_filter._redact_pii(text)
        
        assert "9876543210" not in redacted
        assert "user@example.com" not in redacted
        assert "1234 5678 9012" not in redacted
        assert "[PHONE_REDACTED]" in redacted
        assert "[EMAIL_REDACTED]" in redacted
        assert "[AADHAAR_REDACTED]" in redacted
    
    def test_filter_log_record(self):
        """Test filter processes log records."""
        pii_filter = PIIFilter()
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg="Phone: 9876543210",
            args=(),
            exc_info=None
        )
        
        result = pii_filter.filter(record)
        
        assert result is True
        assert "[PHONE_REDACTED]" in record.msg
    
    def test_filter_log_record_with_args(self):
        """Test filter processes log record arguments."""
        pii_filter = PIIFilter()
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg="User info: %s",
            args=("Email: user@example.com",),
            exc_info=None
        )
        
        result = pii_filter.filter(record)
        
        assert result is True
        assert "[EMAIL_REDACTED]" in record.args[0]


class TestJSONFormatter:
    """Test suite for JSONFormatter."""
    
    def test_format_basic_record(self):
        """Test formatting basic log record."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data['level'] == 'INFO'
        assert data['logger'] == 'test'
        assert data['message'] == 'Test message'
        assert 'timestamp' in data
    
    def test_format_with_correlation_id(self):
        """Test formatting with correlation ID."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.correlation_id = "test-correlation-id"
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data['correlation_id'] == "test-correlation-id"
    
    def test_format_with_service_and_operation(self):
        """Test formatting with service and operation."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.service = "Bedrock"
        record.operation = "generate_fir"
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data['service'] == "Bedrock"
        assert data['operation'] == "generate_fir"
    
    def test_format_with_error_info(self):
        """Test formatting with error information."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name='test',
            level=logging.ERROR,
            pathname='',
            lineno=0,
            msg="Error occurred",
            args=(),
            exc_info=None
        )
        record.error_type = "ValueError"
        record.error_message = "Invalid input"
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data['error_type'] == "ValueError"
        assert data['error_message'] == "Invalid input"
    
    def test_format_with_all_fields(self):
        """Test formatting with all optional fields."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.correlation_id = "corr-123"
        record.service = "Bedrock"
        record.operation = "generate"
        record.user_id = "user-456"
        record.session_id = "session-789"
        record.duration_ms = 1500
        record.status = "success"
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data['correlation_id'] == "corr-123"
        assert data['service'] == "Bedrock"
        assert data['operation'] == "generate"
        assert data['user_id'] == "user-456"
        assert data['session_id'] == "session-789"
        assert data['duration_ms'] == 1500
        assert data['status'] == "success"


class TestStructuredLogger:
    """Test suite for StructuredLogger."""
    
    def test_initialization(self):
        """Test logger initializes correctly."""
        logger = StructuredLogger('test', level=logging.DEBUG, enable_pii_filter=True)
        
        assert logger.logger.name == 'test'
        assert logger.logger.level == logging.DEBUG
        assert logger.correlation_id is None
    
    def test_set_correlation_id(self):
        """Test setting correlation ID."""
        logger = StructuredLogger('test')
        
        logger.set_correlation_id("test-id-123")
        
        assert logger.correlation_id == "test-id-123"
    
    def test_generate_correlation_id(self):
        """Test generating correlation ID."""
        logger = StructuredLogger('test')
        
        corr_id = logger.generate_correlation_id()
        
        assert corr_id is not None
        assert logger.correlation_id == corr_id
        assert len(corr_id) > 0
    
    def test_info_logging(self):
        """Test info level logging."""
        logger = StructuredLogger('test', enable_pii_filter=False)
        
        with patch.object(logger.logger, 'log') as mock_log:
            logger.info("Test message", service="Bedrock", operation="test")
            
            mock_log.assert_called_once()
            args = mock_log.call_args
            assert args[0][0] == logging.INFO
            assert args[0][1] == "Test message"
            assert 'service' in args[1]['extra']
            assert args[1]['extra']['service'] == "Bedrock"
    
    def test_warning_logging(self):
        """Test warning level logging."""
        logger = StructuredLogger('test', enable_pii_filter=False)
        
        with patch.object(logger.logger, 'log') as mock_log:
            logger.warning("Warning message", service="Transcribe")
            
            mock_log.assert_called_once()
            args = mock_log.call_args
            assert args[0][0] == logging.WARNING
    
    def test_error_logging(self):
        """Test error level logging."""
        logger = StructuredLogger('test', enable_pii_filter=False)
        
        error = ValueError("Test error")
        
        with patch.object(logger.logger, 'log') as mock_log:
            logger.error("Error occurred", service="Bedrock", error=error)
            
            mock_log.assert_called_once()
            args = mock_log.call_args
            assert args[0][0] == logging.ERROR
            assert 'error_type' in args[1]['extra']
            assert args[1]['extra']['error_type'] == "ValueError"
            assert args[1]['extra']['error_message'] == "Test error"
    
    def test_debug_logging(self):
        """Test debug level logging."""
        logger = StructuredLogger('test', level=logging.DEBUG, enable_pii_filter=False)
        
        with patch.object(logger.logger, 'log') as mock_log:
            logger.debug("Debug message", operation="test_op")
            
            mock_log.assert_called_once()
            args = mock_log.call_args
            assert args[0][0] == logging.DEBUG
    
    def test_logging_with_correlation_id(self):
        """Test logging includes correlation ID."""
        logger = StructuredLogger('test', enable_pii_filter=False)
        logger.set_correlation_id("corr-123")
        
        with patch.object(logger.logger, 'log') as mock_log:
            logger.info("Test message")
            
            args = mock_log.call_args
            assert args[1]['extra']['correlation_id'] == "corr-123"
    
    def test_logging_with_custom_fields(self):
        """Test logging with custom fields."""
        logger = StructuredLogger('test', enable_pii_filter=False)
        
        with patch.object(logger.logger, 'log') as mock_log:
            logger.info(
                "Test message",
                service="Bedrock",
                operation="generate",
                user_id="user-123",
                duration_ms=1500
            )
            
            args = mock_log.call_args
            extra = args[1]['extra']
            assert extra['service'] == "Bedrock"
            assert extra['operation'] == "generate"
            assert extra['user_id'] == "user-123"
            assert extra['duration_ms'] == 1500
    
    def test_logging_filters_none_values(self):
        """Test logging filters out None values."""
        logger = StructuredLogger('test', enable_pii_filter=False)
        
        with patch.object(logger.logger, 'log') as mock_log:
            logger.info("Test message", service=None, operation="test")
            
            args = mock_log.call_args
            extra = args[1]['extra']
            assert 'service' not in extra
            assert extra['operation'] == "test"
    
    def test_pii_filter_enabled_by_default(self):
        """Test PII filter is enabled by default."""
        logger = StructuredLogger('test')
        
        # Check if PII filter is in the logger's filters
        filters = logger.logger.filters
        assert any(isinstance(f, PIIFilter) for f in filters)
    
    def test_pii_filter_can_be_disabled(self):
        """Test PII filter can be disabled."""
        # Create a fresh logger with unique name to avoid filter accumulation
        import uuid
        unique_name = f'test_{uuid.uuid4().hex[:8]}'
        logger = StructuredLogger(unique_name, enable_pii_filter=False)
        
        # Check if PII filter is NOT in the logger's filters
        # Note: The logger may have other filters, so we just check PIIFilter specifically
        pii_filters = [f for f in logger.logger.filters if isinstance(f, PIIFilter)]
        assert len(pii_filters) == 0


class TestGetLogger:
    """Test suite for get_logger function."""
    
    def test_get_logger_creates_instance(self):
        """Test get_logger creates logger instance."""
        # Reset global logger
        import services.monitoring.logger as logger_module
        logger_module._global_logger = None
        
        logger = get_logger('test')
        
        assert logger is not None
        assert isinstance(logger, StructuredLogger)
    
    def test_get_logger_returns_same_instance(self):
        """Test get_logger returns same instance on multiple calls."""
        # Reset global logger
        import services.monitoring.logger as logger_module
        logger_module._global_logger = None
        
        logger1 = get_logger('test1')
        logger2 = get_logger('test2')
        
        assert logger1 is logger2
    
    def test_get_logger_default_name(self):
        """Test get_logger uses default name."""
        # Reset global logger
        import services.monitoring.logger as logger_module
        logger_module._global_logger = None
        
        logger = get_logger()
        
        assert logger.logger.name == 'afirgen'
