"""
Session Service - Business logic for session management.

This service handles session lifecycle and state management,
separated from API routing logic.

Requirements: 8.1 - Separate business logic from API routing
"""

import asyncio
from typing import Optional, Dict
from datetime import datetime

from models.domain.session import SessionStatus
from infrastructure.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class SessionService:
    """
    Service for managing FIR processing sessions.
    
    Encapsulates business logic for session operations.
    """
    
    def __init__(self, session_manager):
        """
        Initialize SessionService.
        
        Args:
            session_manager: PersistentSessionManager instance for session persistence
        """
        self.session_manager = session_manager
    
    async def get_session_status(self, session_id: str) -> Dict:
        """
        Get session status with minimal data for performance.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with session status information
            
        Raises:
            ValueError: If session not found
        """
        # Use async to avoid blocking
        session = await asyncio.to_thread(self.session_manager.get_session, session_id)
        
        if not session:
            raise ValueError("Session not found or expired")
        
        # Return minimal data for faster serialization
        return {
            "session_id": session_id,
            "status": session["status"],
            "current_step": session["state"].get("current_validation_step"),
            "awaiting_validation": session["state"].get("awaiting_validation", False),
            "created_at": session["created_at"].isoformat(),
            "last_activity": session["last_activity"].isoformat()
        }
    
    async def create_session(self, session_id: str, initial_state: Dict) -> None:
        """
        Create a new session.
        
        Args:
            session_id: Session identifier
            initial_state: Initial session state
        """
        await asyncio.to_thread(
            self.session_manager.create_session,
            session_id,
            initial_state
        )
        logger.info(f"Session created: {session_id}")
    
    async def update_session(self, session_id: str, updates: Dict) -> bool:
        """
        Update session state.
        
        Args:
            session_id: Session identifier
            updates: Dictionary of updates to apply
            
        Returns:
            True if successful, False otherwise
        """
        success = await asyncio.to_thread(
            self.session_manager.update_session,
            session_id,
            updates
        )
        
        if success:
            logger.debug(f"Session updated: {session_id}")
        else:
            logger.warning(f"Failed to update session: {session_id}")
        
        return success
    
    async def set_session_status(self, session_id: str, status: SessionStatus) -> bool:
        """
        Set session status.
        
        Args:
            session_id: Session identifier
            status: New session status
            
        Returns:
            True if successful, False otherwise
        """
        success = await asyncio.to_thread(
            self.session_manager.set_session_status,
            session_id,
            status
        )
        
        if success:
            logger.info(f"Session status updated: {session_id} -> {status}")
        else:
            logger.warning(f"Failed to update session status: {session_id}")
        
        return success
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get full session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data dictionary or None if not found
        """
        return await asyncio.to_thread(
            self.session_manager.get_session,
            session_id
        )
