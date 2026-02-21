"""
Request DTOs for API endpoints.

These models define the structure and validation for API requests.
Requirements: 8.1 - Separate business logic from API routing
"""

from typing import Optional
from pydantic import BaseModel, Field, validator

from infrastructure.input_validation import (
    ValidationConstants,
    sanitize_text,
    validate_session_id_param,
    validate_fir_number_param,
    ValidationStep,
)


class ProcessRequest(BaseModel):
    """Request model for FIR processing."""
    audio: Optional[bytes] = None
    image: Optional[bytes] = None
    text: Optional[str] = None


class ValidationRequest(BaseModel):
    """Request model for validation step."""
    session_id: str
    approved: bool
    user_input: Optional[str] = None
    
    @validator('session_id')
    def validate_session_id(cls, v):
        return validate_session_id_param(v)
    
    @validator('user_input')
    def sanitize_user_input(cls, v):
        if v is None:
            return v
        if len(v) > ValidationConstants.MAX_USER_INPUT_LENGTH:
            raise ValueError(f"User input too long. Maximum length: {ValidationConstants.MAX_USER_INPUT_LENGTH}")
        return sanitize_text(v, allow_html=False)


class RegenerateRequest(BaseModel):
    """Request model for regenerating a validation step."""
    session_id: str
    step: ValidationStep
    user_input: Optional[str] = None
    
    @validator('session_id')
    def validate_session_id(cls, v):
        return validate_session_id_param(v)
    
    @validator('user_input')
    def sanitize_user_input(cls, v):
        if v is None:
            return v
        if len(v) > ValidationConstants.MAX_USER_INPUT_LENGTH:
            raise ValueError(f"User input too long. Maximum length: {ValidationConstants.MAX_USER_INPUT_LENGTH}")
        return sanitize_text(v, allow_html=False)


class AuthRequest(BaseModel):
    """Request model for FIR authentication."""
    fir_number: str
    auth_key: str
    
    @validator('fir_number')
    def validate_fir_number(cls, v):
        return validate_fir_number_param(v)
    
    @validator('auth_key')
    def validate_auth_key(cls, v):
        if not v or len(v) < 8:
            raise ValueError("Invalid authentication key")
        return v


class CircuitBreakerResetRequest(BaseModel):
    """Request model for resetting circuit breaker."""
    name: str
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v) > 100:
            raise ValueError("Invalid circuit breaker name")
        return v
