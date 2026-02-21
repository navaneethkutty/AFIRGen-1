"""
FIR API routes.

This module contains all FIR-related API endpoints separated from business logic.
Requirements: 8.1 - Separate business logic from API routing
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from datetime import datetime

from models.dto.requests import ProcessRequest, ValidationRequest, RegenerateRequest, AuthRequest
from models.dto.responses import FIRResp, ValidationResponse, AuthResponse
from services.session_service import SessionService
from infrastructure.input_validation import (
    ValidationConstants,
    sanitize_text,
    validate_file_upload,
    ValidationStep,
    validate_session_id_param,
    validate_fir_number_param,
)
from infrastructure.xray_tracing import trace_subsegment, add_trace_annotation
from infrastructure.logging import get_logger
from api.dependencies import get_session_service

# Initialize logger
log = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["fir"])


@router.post("/process", response_model=FIRResp)
@trace_subsegment("process_fir_request")
async def process_endpoint(
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    text: Optional[str] = None,
    session_service: SessionService = Depends(get_session_service),
):
    """
    Start FIR processing with enhanced validation and error handling.
    
    Business logic is delegated to SessionService (injected via dependency).
    """
    # Add X-Ray annotations
    add_trace_annotation("endpoint", "/process")
    add_trace_annotation("has_audio", bool(audio))
    add_trace_annotation("has_image", bool(image))
    add_trace_annotation("has_text", bool(text))
    
    # Validate that at least one input is provided
    if not any([audio, image, text]):
        add_trace_annotation("error", "no_input")
        raise HTTPException(
            status_code=400,
            detail="No input provided. Please provide audio, image, or text."
        )
    
    # Validate only one input type is provided
    input_count = sum([bool(audio), bool(image), bool(text)])
    if input_count > 1:
        raise HTTPException(
            status_code=400,
            detail="Please provide only one input type (audio, image, or text)"
        )
    
    # Validate file uploads
    if audio:
        validate_file_upload(audio, ValidationConstants.ALLOWED_AUDIO_TYPES)
    
    if image:
        validate_file_upload(image, ValidationConstants.ALLOWED_IMAGE_TYPES)
    
    # Validate and sanitize text input
    if text:
        if len(text) < ValidationConstants.MIN_TEXT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Text input too short. Minimum length: {ValidationConstants.MIN_TEXT_LENGTH} characters"
            )
        
        if len(text) > ValidationConstants.MAX_TEXT_LENGTH:
            raise HTTPException(
                status_code=413,
                detail=f"Text input too long. Maximum length: {ValidationConstants.MAX_TEXT_LENGTH} characters"
            )
        
        # Sanitize text input
        text = sanitize_text(text, allow_html=False)
    
    try:
        # Delegate to service layer
        result = await session_service.process_input(
            audio=audio,
            image=image,
            text=text
        )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=ValidationResponse)
async def validate_step(
    validation_req: ValidationRequest,
    session_service: SessionService = Depends(get_session_service),
):
    """
    Enhanced validation with better timeout handling and input validation.
    
    Business logic is delegated to SessionService (injected via dependency).
    """
    try:
        result = await session_service.validate_step(
            session_id=validation_req.session_id,
            approved=validation_req.approved,
            user_input=validation_req.user_input
        )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Validation error: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")


@router.get("/session/{session_id}/status")
async def get_session_status(
    session_id: str,
    session_service: SessionService = Depends(get_session_service),
):
    """Get session status with validated session ID (injected via dependency)."""
    # Validate session_id parameter
    session_id = validate_session_id_param(session_id)
    
    try:
        status = await session_service.get_session_status(session_id)
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrieving session status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session status")


@router.post("/regenerate/{session_id}")
async def regenerate_step(
    session_id: str,
    step: ValidationStep,
    user_input: Optional[str] = None,
    session_service: SessionService = Depends(get_session_service),
):
    """Regenerate a validation step with validated inputs (injected via dependency)."""
    # Validate session_id parameter
    session_id = validate_session_id_param(session_id)
    
    # Validate and sanitize user input
    if user_input:
        if len(user_input) > ValidationConstants.MAX_USER_INPUT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"User input too long. Maximum length: {ValidationConstants.MAX_USER_INPUT_LENGTH} characters"
            )
        user_input = sanitize_text(user_input, allow_html=False)
    
    try:
        result = await session_service.regenerate_step(
            session_id=session_id,
            step=step,
            user_input=user_input
        )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Regeneration error: {e}")
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {e}")


@router.post("/authenticate", response_model=AuthResponse)
async def authenticate_fir(
    auth_req: AuthRequest,
    session_service: SessionService = Depends(get_session_service),
):
    """Authenticate and finalize FIR with validated inputs (injected via dependency)."""
    try:
        result = await session_service.authenticate_and_finalize(
            fir_number=auth_req.fir_number,
            auth_key=auth_req.auth_key
        )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Authentication error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.get("/fir/{fir_number}")
async def get_fir_status(
    fir_number: str,
    session_service: SessionService = Depends(get_session_service),
):
    """Get FIR status with validated FIR number (injected via dependency)."""
    # Validate FIR number parameter
    fir_number = validate_fir_number_param(fir_number)
    
    try:
        status = await session_service.get_fir_status(fir_number)
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrieving FIR: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve FIR")


@router.get("/fir/{fir_number}/content")
async def get_fir_content(
    fir_number: str,
    session_service: SessionService = Depends(get_session_service),
):
    """Get full FIR content with validated FIR number (injected via dependency)."""
    # Validate FIR number parameter
    fir_number = validate_fir_number_param(fir_number)
    
    try:
        content = await session_service.get_fir_content(fir_number)
        return content
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrieving FIR content: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve FIR content")
