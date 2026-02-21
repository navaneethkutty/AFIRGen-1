"""
Shared constants and enums for the AFIRGen backend system.

This module centralizes constants used across the application:
- Validation limits and thresholds
- File type restrictions
- Regex patterns
- HTTP status codes
- Task priorities
- Cache TTL values

Requirements: 8.5
"""

from enum import Enum
from typing import Set


# ============================================================================
# TEXT VALIDATION CONSTANTS
# ============================================================================

class TextLimits:
    """Text length limits for various inputs."""
    MAX_TEXT_LENGTH: int = 50_000
    MIN_TEXT_LENGTH: int = 10
    MAX_USER_INPUT_LENGTH: int = 10_000
    MAX_FIR_NUMBER_LENGTH: int = 50
    MAX_AUTH_KEY_LENGTH: int = 256
    MIN_AUTH_KEY_LENGTH: int = 8


# ============================================================================
# FILE UPLOAD CONSTANTS
# ============================================================================

class FileLimits:
    """File size and type restrictions."""
    MAX_FILE_SIZE: int = 25 * 1024 * 1024  # 25MB
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB


class AllowedFileTypes:
    """Allowed MIME types and extensions for file uploads."""
    IMAGE_TYPES: Set[str] = {"image/jpeg", "image/png", "image/jpg"}
    AUDIO_TYPES: Set[str] = {"audio/wav", "audio/mpeg", "audio/mp3", "audio/x-wav"}
    EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".wav", ".mp3", ".mpeg"}


# ============================================================================
# REGEX PATTERNS
# ============================================================================

class RegexPatterns:
    """Common regex patterns for validation."""
    UUID: str = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    FIR_NUMBER: str = r'^FIR-[a-f0-9]{8}-\d{14}$'
    ALPHANUMERIC: str = r'^[a-zA-Z0-9_-]+$'
    EMAIL: str = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    URL: str = r'^(https?|ftp)://[^\s/$.?#].[^\s]*$'


# ============================================================================
# HTTP STATUS CODES
# ============================================================================

class HTTPStatus:
    """Common HTTP status codes."""
    # Success
    OK: int = 200
    CREATED: int = 201
    ACCEPTED: int = 202
    NO_CONTENT: int = 204
    
    # Client errors
    BAD_REQUEST: int = 400
    UNAUTHORIZED: int = 401
    FORBIDDEN: int = 403
    NOT_FOUND: int = 404
    METHOD_NOT_ALLOWED: int = 405
    REQUEST_TIMEOUT: int = 408
    CONFLICT: int = 409
    PAYLOAD_TOO_LARGE: int = 413
    UNSUPPORTED_MEDIA_TYPE: int = 415
    UNPROCESSABLE_ENTITY: int = 422
    TOO_MANY_REQUESTS: int = 429
    
    # Server errors
    INTERNAL_SERVER_ERROR: int = 500
    NOT_IMPLEMENTED: int = 501
    BAD_GATEWAY: int = 502
    SERVICE_UNAVAILABLE: int = 503
    GATEWAY_TIMEOUT: int = 504


# ============================================================================
# RETRY AND CIRCUIT BREAKER CONSTANTS
# ============================================================================

class RetryDefaults:
    """Default values for retry handler."""
    MAX_RETRIES: int = 3
    BASE_DELAY: float = 1.0
    MAX_DELAY: float = 60.0
    EXPONENTIAL_BASE: float = 2.0
    JITTER: bool = True


class CircuitBreakerDefaults:
    """Default values for circuit breaker."""
    FAILURE_THRESHOLD: int = 5
    RECOVERY_TIMEOUT: int = 60  # seconds
    HALF_OPEN_MAX_CALLS: int = 3


# ============================================================================
# CACHE TTL VALUES
# ============================================================================

class CacheTTL:
    """Time-to-live values for different cache types (in seconds)."""
    FIR_RECORD: int = 3600  # 1 hour
    VIOLATION_CHECK: int = 1800  # 30 minutes
    KB_QUERY: int = 7200  # 2 hours
    USER_SESSION: int = 86400  # 24 hours
    DASHBOARD_STATS: int = 300  # 5 minutes
    SHORT: int = 60  # 1 minute
    MEDIUM: int = 600  # 10 minutes
    LONG: int = 3600  # 1 hour


# ============================================================================
# PAGINATION CONSTANTS
# ============================================================================

class PaginationDefaults:
    """Default values for pagination."""
    DEFAULT_LIMIT: int = 100
    MAX_LIMIT: int = 1000
    MIN_LIMIT: int = 1
    DEFAULT_OFFSET: int = 0


# ============================================================================
# COMPRESSION CONSTANTS
# ============================================================================

class CompressionDefaults:
    """Default values for response compression."""
    MIN_SIZE: int = 1024  # 1KB
    COMPRESSION_LEVEL: int = 6  # gzip compression level (1-9)


# ============================================================================
# BACKGROUND TASK CONSTANTS
# ============================================================================

class TaskPriority:
    """Priority levels for background tasks."""
    LOW: int = 3
    MEDIUM: int = 5
    HIGH: int = 7
    CRITICAL: int = 9


class TaskDefaults:
    """Default values for background tasks."""
    DEFAULT_PRIORITY: int = TaskPriority.MEDIUM
    MAX_RETRIES: int = 3
    TASK_TIME_LIMIT: int = 3600  # 1 hour
    TASK_SOFT_TIME_LIMIT: int = 3300  # 55 minutes


# ============================================================================
# MONITORING AND ALERTING CONSTANTS
# ============================================================================

class AlertThresholds:
    """Default alert thresholds for monitoring."""
    # CPU thresholds (percentage)
    CPU_WARNING: float = 70.0
    CPU_CRITICAL: float = 90.0
    
    # Memory thresholds (percentage)
    MEMORY_WARNING: float = 75.0
    MEMORY_CRITICAL: float = 90.0
    
    # Response time thresholds (seconds)
    RESPONSE_TIME_WARNING: float = 2.0
    RESPONSE_TIME_CRITICAL: float = 5.0
    
    # Error rate thresholds (percentage)
    ERROR_RATE_WARNING: float = 5.0
    ERROR_RATE_CRITICAL: float = 10.0
    
    # Cache hit rate threshold (percentage)
    CACHE_HIT_RATE_MIN: float = 80.0


class MetricsDefaults:
    """Default values for metrics collection."""
    COLLECTION_INTERVAL: int = 60  # seconds
    DEDUPLICATION_WINDOW: int = 300  # 5 minutes


# ============================================================================
# DATABASE CONSTANTS
# ============================================================================

class DatabaseDefaults:
    """Default values for database operations."""
    CONNECTION_POOL_SIZE: int = 10
    MAX_OVERFLOW: int = 20
    POOL_TIMEOUT: int = 30  # seconds
    POOL_RECYCLE: int = 3600  # 1 hour
    QUERY_TIMEOUT: int = 30  # seconds


# ============================================================================
# VALIDATION STEP ENUM
# ============================================================================

class ValidationStep(str, Enum):
    """Validation steps in the FIR generation workflow."""
    TRANSCRIPT_REVIEW = "transcript_review"
    SUMMARY_REVIEW = "summary_review"
    VIOLATIONS_REVIEW = "violations_review"
    FIR_NARRATIVE_REVIEW = "fir_narrative_review"
    FINAL_REVIEW = "final_review"


# ============================================================================
# TASK STATUS ENUM
# ============================================================================

class TaskStatus(str, Enum):
    """Status values for background tasks."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


# ============================================================================
# CIRCUIT BREAKER STATE ENUM
# ============================================================================

class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


# ============================================================================
# LOG LEVEL ENUM
# ============================================================================

class LogLevel(str, Enum):
    """Log level values."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ============================================================================
# ERROR CODES
# ============================================================================

class ErrorCode(str, Enum):
    """Standard error codes for API responses."""
    # Validation errors
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    
    # Authentication/Authorization errors
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    # Service errors
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    
    # Rate limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # File upload errors
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    
    # Internal errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    TIMEOUT = "TIMEOUT"


# ============================================================================
# SENSITIVE FIELD NAMES
# ============================================================================

class SensitiveFields:
    """Field names that should be redacted in logs."""
    FIELDS: Set[str] = {
        "password",
        "token",
        "api_key",
        "secret",
        "authorization",
        "credit_card",
        "ssn",
        "phone",
        "email",
        "auth_key",
        "access_token",
        "refresh_token",
    }


# ============================================================================
# CIRCUIT BREAKER NAMES
# ============================================================================

class CircuitBreakerNames:
    """Standard circuit breaker names."""
    MODEL_SERVER = "model_server"
    ASR_OCR_SERVER = "asr_ocr_server"
    DATABASE = "database"
    REDIS = "redis"
    
    @classmethod
    def all(cls) -> Set[str]:
        """Get all circuit breaker names."""
        return {
            cls.MODEL_SERVER,
            cls.ASR_OCR_SERVER,
            cls.DATABASE,
            cls.REDIS,
        }


# ============================================================================
# CONTENT TYPE CONSTANTS
# ============================================================================

class ContentType:
    """Common content type values."""
    JSON = "application/json"
    HTML = "text/html"
    TEXT = "text/plain"
    XML = "application/xml"
    FORM_URLENCODED = "application/x-www-form-urlencoded"
    MULTIPART_FORM = "multipart/form-data"
    OCTET_STREAM = "application/octet-stream"


# ============================================================================
# HEADER NAMES
# ============================================================================

class HeaderNames:
    """Common HTTP header names."""
    CONTENT_TYPE = "Content-Type"
    CONTENT_LENGTH = "Content-Length"
    CONTENT_ENCODING = "Content-Encoding"
    CACHE_CONTROL = "Cache-Control"
    ETAG = "ETag"
    IF_NONE_MATCH = "If-None-Match"
    AUTHORIZATION = "Authorization"
    CORRELATION_ID = "X-Correlation-ID"
    REQUEST_ID = "X-Request-ID"
    FORWARDED_FOR = "X-Forwarded-For"
    USER_AGENT = "User-Agent"
    ACCEPT = "Accept"
    ACCEPT_ENCODING = "Accept-Encoding"
