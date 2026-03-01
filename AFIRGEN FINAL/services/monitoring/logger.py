"""
Structured JSON logging for AWS service interactions.
Excludes PII and includes correlation IDs.
"""

import json
import logging
import re
from typing import Any, Dict, Optional
from datetime import datetime
import uuid


class PIIFilter(logging.Filter):
    """Filter to exclude PII from logs."""
    
    # Patterns for PII detection
    PHONE_PATTERN = re.compile(r'\b\d{10,}\b')
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    AADHAAR_PATTERN = re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b')
    
    # Fields that may contain PII
    PII_FIELDS = [
        'complainant_name',
        'accused_name',
        'phone',
        'email',
        'address',
        'aadhaar',
        'complaint_text',
        'incident_description'
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to remove PII.
        
        Args:
            record: Log record to filter
        
        Returns:
            True to allow record, False to block
        """
        # Redact PII from message
        if hasattr(record, 'msg'):
            record.msg = self._redact_pii(str(record.msg))
        
        # Redact PII from args
        if hasattr(record, 'args') and record.args:
            record.args = tuple(
                self._redact_pii(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        
        return True
    
    def _redact_pii(self, text: str) -> str:
        """Redact PII from text."""
        # Redact phone numbers
        text = self.PHONE_PATTERN.sub('[PHONE_REDACTED]', text)
        
        # Redact emails
        text = self.EMAIL_PATTERN.sub('[EMAIL_REDACTED]', text)
        
        # Redact Aadhaar numbers
        text = self.AADHAAR_PATTERN.sub('[AADHAAR_REDACTED]', text)
        
        return text


class StructuredLogger:
    """
    Structured JSON logger for AWS service interactions.
    Includes correlation IDs and excludes PII.
    """
    
    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        enable_pii_filter: bool = True
    ):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            level: Logging level
            enable_pii_filter: Whether to enable PII filtering
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Add PII filter
        if enable_pii_filter:
            self.logger.addFilter(PIIFilter())
        
        # Configure JSON formatter
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)
        
        self.correlation_id: Optional[str] = None
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for request tracking."""
        self.correlation_id = correlation_id
    
    def generate_correlation_id(self) -> str:
        """Generate new correlation ID."""
        self.correlation_id = str(uuid.uuid4())
        return self.correlation_id
    
    def info(
        self,
        message: str,
        service: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log info message with structured data."""
        self._log(logging.INFO, message, service, operation, **kwargs)
    
    def warning(
        self,
        message: str,
        service: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log warning message with structured data."""
        self._log(logging.WARNING, message, service, operation, **kwargs)
    
    def error(
        self,
        message: str,
        service: Optional[str] = None,
        operation: Optional[str] = None,
        error: Optional[Exception] = None,
        **kwargs
    ) -> None:
        """Log error message with structured data."""
        if error:
            kwargs['error_type'] = type(error).__name__
            kwargs['error_message'] = str(error)
        self._log(logging.ERROR, message, service, operation, **kwargs)
    
    def debug(
        self,
        message: str,
        service: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log debug message with structured data."""
        self._log(logging.DEBUG, message, service, operation, **kwargs)
    
    def _log(
        self,
        level: int,
        message: str,
        service: Optional[str],
        operation: Optional[str],
        **kwargs
    ) -> None:
        """Internal logging method."""
        extra = {
            'correlation_id': self.correlation_id,
            'service': service,
            'operation': operation,
            **kwargs
        }
        
        # Remove None values
        extra = {k: v for k, v in extra.items() if v is not None}
        
        self.logger.log(level, message, extra=extra)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
        
        Returns:
            JSON string
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add extra fields
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
        
        if hasattr(record, 'service'):
            log_data['service'] = record.service
        
        if hasattr(record, 'operation'):
            log_data['operation'] = record.operation
        
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        if hasattr(record, 'session_id'):
            log_data['session_id'] = record.session_id
        
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        
        if hasattr(record, 'status'):
            log_data['status'] = record.status
        
        if hasattr(record, 'error_type'):
            log_data['error_type'] = record.error_type
        
        if hasattr(record, 'error_message'):
            log_data['error_message'] = record.error_message
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


# Global logger instance
_global_logger: Optional[StructuredLogger] = None


def get_logger(name: str = 'afirgen') -> StructuredLogger:
    """
    Get or create global structured logger.
    
    Args:
        name: Logger name
    
    Returns:
        StructuredLogger instance
    """
    global _global_logger
    
    if _global_logger is None:
        _global_logger = StructuredLogger(name)
    
    return _global_logger
