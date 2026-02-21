"""
Session domain model.

Represents a user session during FIR generation process.
"""

from enum import Enum
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


class SessionStatus(str, Enum):
    """Session status enumeration"""
    PROCESSING = "processing"
    AWAITING_VALIDATION = "awaiting_validation"
    COMPLETED = "completed"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class SessionData:
    """
    Session data model.
    
    Represents the complete state of a user session including
    FIR generation progress and validation history.
    """
    session_id: str
    state: Dict[str, Any]
    status: SessionStatus
    created_at: datetime
    last_activity: datetime
    validation_history: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session data to dictionary"""
        return {
            "session_id": self.session_id,
            "state": self.state,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "validation_history": self.validation_history,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionData":
        """Create session data from dictionary"""
        return cls(
            session_id=data["session_id"],
            state=data["state"],
            status=SessionStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            validation_history=data.get("validation_history", []),
        )
