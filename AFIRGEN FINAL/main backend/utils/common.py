"""
Common utility functions for the AFIRGen backend system.

This module provides reusable utility functions for common operations:
- String manipulation
- Date/time operations
- Data structure operations
- Hashing and encoding
- ID generation

Requirements: 8.5
"""

import hashlib
import uuid
import base64
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypeVar, Callable
import json


T = TypeVar('T')


# ============================================================================
# STRING UTILITIES
# ============================================================================

def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string to maximum length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to append if truncated (default: "...")
        
    Returns:
        Truncated string
        
    Requirements: 8.5
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text (collapse multiple spaces to single space).
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
        
    Requirements: 8.5
    """
    import re
    return re.sub(r'\s+', ' ', text).strip()


def to_snake_case(text: str) -> str:
    """
    Convert string to snake_case.
    
    Args:
        text: Text to convert
        
    Returns:
        Snake case string
        
    Requirements: 8.5
    """
    import re
    # Insert underscore before uppercase letters
    text = re.sub(r'(?<!^)(?=[A-Z])', '_', text)
    # Convert to lowercase
    return text.lower()


def to_camel_case(text: str) -> str:
    """
    Convert string to camelCase.
    
    Args:
        text: Text to convert (snake_case or kebab-case)
        
    Returns:
        Camel case string
        
    Requirements: 8.5
    """
    components = text.replace('-', '_').split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def mask_sensitive_data(text: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data, showing only last N characters.
    
    Args:
        text: Text to mask
        visible_chars: Number of characters to show at the end
        
    Returns:
        Masked string
        
    Requirements: 8.5
    """
    if len(text) <= visible_chars:
        return '*' * len(text)
    
    return '*' * (len(text) - visible_chars) + text[-visible_chars:]


# ============================================================================
# DATE/TIME UTILITIES
# ============================================================================

def get_current_timestamp() -> datetime:
    """
    Get current UTC timestamp.
    
    Returns:
        Current datetime in UTC
        
    Requirements: 8.5
    """
    return datetime.now(timezone.utc)


def format_timestamp(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime to string.
    
    Args:
        dt: Datetime to format
        format_str: Format string (default: ISO-like format)
        
    Returns:
        Formatted datetime string
        
    Requirements: 8.5
    """
    return dt.strftime(format_str)


def parse_timestamp(timestamp_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Parse timestamp string to datetime.
    
    Args:
        timestamp_str: Timestamp string to parse
        format_str: Format string
        
    Returns:
        Parsed datetime
        
    Requirements: 8.5
    """
    return datetime.strptime(timestamp_str, format_str)


def timestamp_to_iso(dt: datetime) -> str:
    """
    Convert datetime to ISO 8601 format string.
    
    Args:
        dt: Datetime to convert
        
    Returns:
        ISO 8601 formatted string
        
    Requirements: 8.5
    """
    return dt.isoformat()


def iso_to_timestamp(iso_str: str) -> datetime:
    """
    Parse ISO 8601 format string to datetime.
    
    Args:
        iso_str: ISO 8601 formatted string
        
    Returns:
        Parsed datetime
        
    Requirements: 8.5
    """
    return datetime.fromisoformat(iso_str.replace('Z', '+00:00'))


# ============================================================================
# HASHING AND ENCODING UTILITIES
# ============================================================================

def generate_hash(data: str, algorithm: str = "sha256") -> str:
    """
    Generate hash of data.
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm (default: sha256)
        
    Returns:
        Hex digest of hash
        
    Requirements: 8.5
    """
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data.encode('utf-8'))
    return hash_obj.hexdigest()


def generate_md5(data: str) -> str:
    """
    Generate MD5 hash of data.
    
    Args:
        data: Data to hash
        
    Returns:
        MD5 hex digest
        
    Requirements: 8.5
    """
    return hashlib.md5(data.encode('utf-8')).hexdigest()


def generate_sha256(data: str) -> str:
    """
    Generate SHA256 hash of data.
    
    Args:
        data: Data to hash
        
    Returns:
        SHA256 hex digest
        
    Requirements: 8.5
    """
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def encode_base64(data: str) -> str:
    """
    Encode string to base64.
    
    Args:
        data: String to encode
        
    Returns:
        Base64 encoded string
        
    Requirements: 8.5
    """
    return base64.b64encode(data.encode('utf-8')).decode('utf-8')


def decode_base64(encoded: str) -> str:
    """
    Decode base64 string.
    
    Args:
        encoded: Base64 encoded string
        
    Returns:
        Decoded string
        
    Requirements: 8.5
    """
    return base64.b64decode(encoded.encode('utf-8')).decode('utf-8')


# ============================================================================
# ID GENERATION UTILITIES
# ============================================================================

def generate_uuid() -> str:
    """
    Generate a new UUID v4.
    
    Returns:
        UUID string
        
    Requirements: 8.5
    """
    return str(uuid.uuid4())


def generate_correlation_id() -> str:
    """
    Generate a correlation ID for request tracking.
    
    Returns:
        Correlation ID (UUID v4)
        
    Requirements: 8.5
    """
    return generate_uuid()


def generate_fir_number() -> str:
    """
    Generate a FIR number in the format: FIR-{8_hex_chars}-{14_digit_timestamp}.
    
    Returns:
        FIR number string
        
    Requirements: 8.5
    """
    # Generate 8 random hex characters
    random_hex = uuid.uuid4().hex[:8]
    
    # Generate 14-digit timestamp (YYYYMMDDHHmmss)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    
    return f"FIR-{random_hex}-{timestamp}"


# ============================================================================
# DATA STRUCTURE UTILITIES
# ============================================================================

def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
        
    Returns:
        Merged dictionary
        
    Requirements: 8.5
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    Flatten nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator for nested keys
        
    Returns:
        Flattened dictionary
        
    Requirements: 8.5
    """
    items: List[tuple] = []
    
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    
    return dict(items)


def chunk_list(lst: List[T], chunk_size: int) -> List[List[T]]:
    """
    Split list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
        
    Requirements: 8.5
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def remove_none_values(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove keys with None values from dictionary.
    
    Args:
        d: Dictionary to clean
        
    Returns:
        Dictionary without None values
        
    Requirements: 8.5
    """
    return {k: v for k, v in d.items() if v is not None}


def get_nested_value(d: Dict[str, Any], path: str, default: Any = None, sep: str = '.') -> Any:
    """
    Get value from nested dictionary using dot notation.
    
    Args:
        d: Dictionary to search
        path: Dot-separated path (e.g., "user.profile.name")
        default: Default value if path not found
        sep: Separator for path components
        
    Returns:
        Value at path or default
        
    Requirements: 8.5
    """
    keys = path.split(sep)
    value = d
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value


def set_nested_value(d: Dict[str, Any], path: str, value: Any, sep: str = '.') -> None:
    """
    Set value in nested dictionary using dot notation.
    
    Args:
        d: Dictionary to modify
        path: Dot-separated path (e.g., "user.profile.name")
        value: Value to set
        sep: Separator for path components
        
    Requirements: 8.5
    """
    keys = path.split(sep)
    current = d
    
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value


# ============================================================================
# JSON UTILITIES
# ============================================================================

def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string, returning default on error.
    
    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON or default
        
    Requirements: 8.5
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    Safely serialize object to JSON, returning default on error.
    
    Args:
        obj: Object to serialize
        default: Default value if serialization fails
        
    Returns:
        JSON string or default
        
    Requirements: 8.5
    """
    try:
        return json.dumps(obj)
    except (TypeError, ValueError):
        return default


def pretty_json(obj: Any, indent: int = 2) -> str:
    """
    Format object as pretty-printed JSON.
    
    Args:
        obj: Object to format
        indent: Indentation level
        
    Returns:
        Pretty-printed JSON string
        
    Requirements: 8.5
    """
    return json.dumps(obj, indent=indent, sort_keys=True)


# ============================================================================
# RETRY UTILITIES
# ============================================================================

def retry_on_exception(
    func: Callable[..., T],
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,)
) -> Optional[T]:
    """
    Simple retry wrapper for functions.
    
    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Function result or None if all attempts fail
        
    Requirements: 8.5
    """
    import time
    
    for attempt in range(max_attempts):
        try:
            return func()
        except exceptions as e:
            if attempt == max_attempts - 1:
                return None
            time.sleep(delay)
    
    return None


# ============================================================================
# COMPARISON UTILITIES
# ============================================================================

def safe_compare(a: Any, b: Any, default: bool = False) -> bool:
    """
    Safely compare two values, returning default if comparison fails.
    
    Args:
        a: First value
        b: Second value
        default: Default value if comparison fails
        
    Returns:
        Comparison result or default
        
    Requirements: 8.5
    """
    try:
        result: bool = (a == b)
        return result
    except (TypeError, ValueError):
        return default


def is_empty(value: Any) -> bool:
    """
    Check if value is empty (None, empty string, empty list, etc.).
    
    Args:
        value: Value to check
        
    Returns:
        True if value is empty, False otherwise
        
    Requirements: 8.5
    """
    if value is None:
        return True
    
    if isinstance(value, (str, list, dict, tuple, set)):
        return len(value) == 0
    
    return False


# ============================================================================
# CONVERSION UTILITIES
# ============================================================================

def to_bool(value: Any, default: bool = False) -> bool:
    """
    Convert value to boolean.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Boolean value
        
    Requirements: 8.5
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    
    if isinstance(value, (int, float)):
        return value != 0
    
    return default


def to_int(value: Any, default: int = 0) -> int:
    """
    Convert value to integer.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value
        
    Requirements: 8.5
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    """
    Convert value to float.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value
        
    Requirements: 8.5
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
