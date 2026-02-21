"""
Response DTOs for API endpoints.

These models define the structure for API responses.
Requirements: 8.1 - Separate business logic from API routing
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from infrastructure.input_validation import ValidationStep


class FIRResp(BaseModel):
    """Response model for FIR processing."""
    success: bool
    session_id: str
    steps: List[str] = Field(default_factory=list)
    error: str = ""
    requires_validation: bool = False
    current_step: Optional[ValidationStep] = None
    content_for_validation: Optional[Dict[str, Any]] = None


class ValidationResponse(BaseModel):
    """Response model for validation step."""
    success: bool
    session_id: str
    current_step: Optional[ValidationStep] = None
    content: Optional[Dict[str, Any]] = None
    message: str = ""
    requires_validation: bool = True
    completed: bool = False


class AuthResponse(BaseModel):
    """Response model for FIR authentication."""
    success: bool
    message: str
    fir_number: str


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    detail: Optional[str] = None
    correlation_id: Optional[str] = None
