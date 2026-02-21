"""
Validation utilities for the AFIRGen backend system.

This module provides reusable validation functions for common operations:
- Text sanitization and validation
- File upload validation
- ID and format validation
- Query parameter validation

Requirements: 8.5
"""

import re
import string
from typing import Optional, List, Set, Any
from pathlib import Path


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def sanitize_text(text: str, allow_html: bool = False) -> str:
    """
    Sanitize text input to prevent XSS and injection attacks.
    
    Args:
        text: Input text to sanitize
        allow_html: If False, escape HTML characters
    
    Returns:
        Sanitized text
        
    Raises:
        ValidationError: If text contains dangerous patterns
        
    Requirements: 8.5
    """
    if not text:
        return ""
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove non-printable characters except newlines and tabs
    text = ''.join(ch for ch in text if ch in string.printable or ch in '\n\t')
    
    # Check for dangerous patterns
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # Event handlers like onclick=
        r'<iframe',
        r'<object',
        r'<embed',
        r'eval\s*\(',
        r'expression\s*\(',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValidationError(f"Input contains potentially dangerous content: {pattern}")
    
    # Escape HTML if not allowed
    if not allow_html:
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        text = text.replace('"', '&quot;').replace("'", '&#x27;')
    
    return text.strip()


def validate_text_length(
    text: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    field_name: str = "text"
) -> None:
    """
    Validate text length constraints.
    
    Args:
        text: Text to validate
        min_length: Minimum allowed length (None for no minimum)
        max_length: Maximum allowed length (None for no maximum)
        field_name: Name of the field for error messages
        
    Raises:
        ValidationError: If text length is invalid
        
    Requirements: 8.5
    """
    if min_length is not None and len(text) < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} characters long"
        )
    
    if max_length is not None and len(text) > max_length:
        raise ValidationError(
            f"{field_name} must not exceed {max_length} characters"
        )


def validate_uuid(uuid_str: str, field_name: str = "UUID") -> str:
    """
    Validate UUID format.
    
    Args:
        uuid_str: UUID string to validate
        field_name: Name of the field for error messages
        
    Returns:
        Lowercase UUID string
        
    Raises:
        ValidationError: If UUID format is invalid
        
    Requirements: 8.5
    """
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    
    if not re.match(uuid_pattern, uuid_str, re.IGNORECASE):
        raise ValidationError(f"Invalid {field_name} format")
    
    return uuid_str.lower()


def validate_fir_number(fir_number: str) -> str:
    """
    Validate FIR number format.
    
    Args:
        fir_number: FIR number to validate
        
    Returns:
        Validated FIR number
        
    Raises:
        ValidationError: If FIR number format is invalid
        
    Requirements: 8.5
    """
    fir_pattern = r'^FIR-[a-f0-9]{8}-\d{14}$'
    
    if not re.match(fir_pattern, fir_number):
        raise ValidationError("Invalid FIR number format")
    
    return fir_number


def validate_alphanumeric(value: str, field_name: str = "value") -> str:
    """
    Validate alphanumeric format (letters, numbers, underscore, hyphen).
    
    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        
    Returns:
        Validated value
        
    Raises:
        ValidationError: If format is invalid
        
    Requirements: 8.5
    """
    pattern = r'^[a-zA-Z0-9_-]+$'
    
    if not re.match(pattern, value):
        raise ValidationError(
            f"{field_name} must contain only letters, numbers, underscores, and hyphens"
        )
    
    return value


def validate_file_extension(filename: str, allowed_extensions: Set[str]) -> None:
    """
    Validate file extension.
    
    Args:
        filename: Filename to validate
        allowed_extensions: Set of allowed extensions (e.g., {'.jpg', '.png'})
        
    Raises:
        ValidationError: If extension is not allowed
        
    Requirements: 8.5
    """
    if not filename:
        raise ValidationError("Invalid filename")
    
    ext = Path(filename).suffix.lower()
    
    if ext not in allowed_extensions:
        raise ValidationError(
            f"Unsupported file extension: {ext}. "
            f"Allowed: {', '.join(sorted(allowed_extensions))}"
        )


def validate_mime_type(mime_type: str, allowed_types: Set[str]) -> None:
    """
    Validate MIME type.
    
    Args:
        mime_type: MIME type to validate
        allowed_types: Set of allowed MIME types
        
    Raises:
        ValidationError: If MIME type is not allowed
        
    Requirements: 8.5
    """
    if mime_type not in allowed_types:
        raise ValidationError(
            f"Unsupported content type: {mime_type}. "
            f"Allowed: {', '.join(sorted(allowed_types))}"
        )


def validate_file_size(size: int, max_size: int) -> None:
    """
    Validate file size.
    
    Args:
        size: File size in bytes
        max_size: Maximum allowed size in bytes
        
    Raises:
        ValidationError: If file is too large
        
    Requirements: 8.5
    """
    if size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise ValidationError(f"File too large. Maximum size: {max_mb:.1f}MB")


def validate_positive_integer(
    value: int,
    field_name: str = "value",
    min_value: int = 1
) -> int:
    """
    Validate positive integer.
    
    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        min_value: Minimum allowed value (default: 1)
        
    Returns:
        Validated value
        
    Raises:
        ValidationError: If value is invalid
        
    Requirements: 8.5
    """
    if value < min_value:
        raise ValidationError(f"{field_name} must be at least {min_value}")
    
    return value


def validate_non_negative_integer(
    value: int,
    field_name: str = "value"
) -> int:
    """
    Validate non-negative integer.
    
    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        
    Returns:
        Validated value
        
    Raises:
        ValidationError: If value is negative
        
    Requirements: 8.5
    """
    if value < 0:
        raise ValidationError(f"{field_name} cannot be negative")
    
    return value


def validate_range(
    value: float,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    field_name: str = "value"
) -> float:
    """
    Validate numeric range.
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value (None for no minimum)
        max_value: Maximum allowed value (None for no maximum)
        field_name: Name of the field for error messages
        
    Returns:
        Validated value
        
    Raises:
        ValidationError: If value is out of range
        
    Requirements: 8.5
    """
    if min_value is not None and value < min_value:
        raise ValidationError(f"{field_name} must be at least {min_value}")
    
    if max_value is not None and value > max_value:
        raise ValidationError(f"{field_name} must not exceed {max_value}")
    
    return value


def validate_enum_value(
    value: str,
    allowed_values: Set[str],
    field_name: str = "value"
) -> str:
    """
    Validate enum value.
    
    Args:
        value: Value to validate
        allowed_values: Set of allowed values
        field_name: Name of the field for error messages
        
    Returns:
        Validated value
        
    Raises:
        ValidationError: If value is not in allowed set
        
    Requirements: 8.5
    """
    if value not in allowed_values:
        raise ValidationError(
            f"Invalid {field_name}. Allowed values: {', '.join(sorted(allowed_values))}"
        )
    
    return value


def validate_json_depth(data: Any, max_depth: int = 10, current_depth: int = 0) -> None:
    """
    Validate JSON nesting depth to prevent DoS attacks.
    
    Args:
        data: JSON data to validate
        max_depth: Maximum allowed nesting depth
        current_depth: Current depth (used in recursion)
    
    Raises:
        ValidationError: If nesting is too deep
        
    Requirements: 8.5
    """
    if current_depth > max_depth:
        raise ValidationError(f"JSON nesting too deep. Maximum depth: {max_depth}")
    
    if isinstance(data, dict):
        for value in data.values():
            validate_json_depth(value, max_depth, current_depth + 1)
    elif isinstance(data, list):
        for item in data:
            validate_json_depth(item, max_depth, current_depth + 1)


def validate_email(email: str) -> str:
    """
    Validate email format (basic validation).
    
    Args:
        email: Email address to validate
        
    Returns:
        Validated email address
        
    Raises:
        ValidationError: If email format is invalid
        
    Requirements: 8.5
    """
    # Basic email pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        raise ValidationError("Invalid email format")
    
    return email.lower()


def validate_url(url: str, allowed_schemes: Optional[Set[str]] = None) -> str:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        allowed_schemes: Set of allowed URL schemes (default: {'http', 'https'})
        
    Returns:
        Validated URL
        
    Raises:
        ValidationError: If URL format is invalid
        
    Requirements: 8.5
    """
    if allowed_schemes is None:
        allowed_schemes = {'http', 'https'}
    
    # Basic URL pattern
    url_pattern = r'^(https?|ftp)://[^\s/$.?#].[^\s]*$'
    
    if not re.match(url_pattern, url, re.IGNORECASE):
        raise ValidationError("Invalid URL format")
    
    # Check scheme
    scheme = url.split('://')[0].lower()
    if scheme not in allowed_schemes:
        raise ValidationError(
            f"Invalid URL scheme: {scheme}. "
            f"Allowed: {', '.join(sorted(allowed_schemes))}"
        )
    
    return url
