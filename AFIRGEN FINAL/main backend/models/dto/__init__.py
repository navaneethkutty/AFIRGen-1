"""
Data Transfer Objects (DTOs) for AFIRGen backend.

DTOs are used for API request/response serialization and validation.
"""

from .requests import (
    ProcessRequest,
    ValidationRequest,
    RegenerateRequest,
    AuthRequest,
    CircuitBreakerResetRequest,
)
from .responses import (
    FIRResp,
    ValidationResponse,
    AuthResponse,
    ErrorResponse,
)

__all__ = [
    # Requests
    "ProcessRequest",
    "ValidationRequest",
    "RegenerateRequest",
    "AuthRequest",
    "CircuitBreakerResetRequest",
    # Responses
    "FIRResp",
    "ValidationResponse",
    "AuthResponse",
    "ErrorResponse",
]
