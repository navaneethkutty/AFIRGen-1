"""
Structured logging setup using structlog.

This module configures structured logging with JSON output, correlation ID tracking,
and sensitive data redaction.
"""

import structlog
import logging
import sys
from typing import Any, Dict, Optional
from .config import config


def redact_sensitive_fields(logger, method_name, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Processor to redact sensitive fields from log entries."""
    sensitive_fields = config.logging.sensitive_fields
    
    for key in list(event_dict.keys()):
        # Check if key matches any sensitive field pattern
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_fields):
            event_dict[key] = "***REDACTED***"
        
        # Recursively redact nested dictionaries
        if isinstance(event_dict[key], dict):
            event_dict[key] = _redact_dict(event_dict[key], sensitive_fields)
    
    return event_dict


def _redact_dict(data: Dict[str, Any], sensitive_fields: list) -> Dict[str, Any]:
    """Recursively redact sensitive fields in nested dictionaries."""
    redacted = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_fields):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = _redact_dict(value, sensitive_fields)
        else:
            redacted[key] = value
    return redacted


def add_service_name(logger, method_name, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add service name to all log entries."""
    event_dict["service"] = config.logging.service_name
    return event_dict


def rename_event_to_message(logger, method_name, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Rename 'event' field to 'message' for consistency with design spec."""
    if "event" in event_dict:
        event_dict["message"] = event_dict.pop("event")
    return event_dict


def configure_logging():
    """Configure structlog with JSON formatting and processors."""
    
    # Determine output stream based on configuration
    output_stream = None
    file_handler = None
    
    if config.logging.output_destination == "stderr":
        output_stream = sys.stderr
    elif config.logging.output_destination == "stdout":
        output_stream = sys.stdout
    else:
        # Check if it's a file path (contains path separators or ends with .log)
        if ("/" in config.logging.output_destination or 
            "\\" in config.logging.output_destination or 
            config.logging.output_destination.endswith(".log")):
            # File path specified
            file_handler = logging.FileHandler(config.logging.output_destination)
        else:
            # Default to stdout if unrecognized
            output_stream = sys.stdout
    
    # Determine if we should use JSON or console output
    if config.logging.format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            add_service_name,
            redact_sensitive_fields,
            rename_event_to_message,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.logging.level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add appropriate handler based on output destination
    if file_handler:
        handler = file_handler
    elif output_stream:
        handler = logging.StreamHandler(output_stream)
    else:
        handler = logging.StreamHandler(sys.stdout)
    
    handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(handler)
    
    # Configure per-module log levels
    for module_name, level in config.logging.module_levels.items():
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(getattr(logging, level, logging.INFO))


class StructuredLogger:
    """Wrapper for structlog with additional context management."""
    
    def __init__(self, name: Optional[str] = None):
        """Initialize structured logger."""
        self.logger = structlog.get_logger(name)
        self._context = {}
    
    def with_context(self, **context) -> "StructuredLogger":
        """Create a new logger instance with additional context."""
        new_logger = StructuredLogger()
        new_logger.logger = self.logger
        new_logger._context = {**self._context, **context}
        return new_logger
    
    def with_correlation_id(self, correlation_id: str) -> "StructuredLogger":
        """Create a new logger instance with correlation ID context.
        
        This is a convenience method for adding correlation IDs to logs.
        
        Args:
            correlation_id: The correlation ID to add to all log entries
            
        Returns:
            A new StructuredLogger instance with the correlation ID in context
        """
        return self.with_context(correlation_id=correlation_id)
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal logging method that merges context."""
        log_method = getattr(self.logger, level)
        log_method(message, **{**self._context, **kwargs})
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log("debug", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log("error", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log("critical", message, **kwargs)


# Initialize logging on module import
configure_logging()


def get_logger(name: Optional[str] = None) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)
