"""Session manager for pure state management - Phase 1A."""

import logging
from typing import Dict, Optional
from uuid import UUID

from .session_models import Session

logger = logging.getLogger(__name__)


class SessionManager:
    """Pure session lifecycle and state management."""
    
    def __init__(self):
        """Initialize session manager."""
        self._sessions: Dict[UUID, Session] = {}
        logger.info("SessionManager initialized")
    
    def create_session(self, user_email: Optional[str] = None) -> Session:
        """Create a new session."""
        session = Session(user_email=user_email)
        self._sessions[session.id] = session
        logger.info(f"Created session {session.id} for user {user_email}")
        return session
    
    def get_session(self, session_id: UUID) -> Optional[Session]:
        """Get a session by ID."""
        return self._sessions.get(session_id)
    
    def get_or_create_session(self, session_id: UUID, user_email: Optional[str] = None) -> Session:
        """Get existing session or create new one."""
        session = self.get_session(session_id)
        if session is None:
            session = Session(id=session_id, user_email=user_email)
            self._sessions[session_id] = session
            logger.info(f"Created new session {session_id} for user {user_email}")
        return session
    
    def update_session(self, session: Session) -> None:
        """Update session in storage."""
        session.update_timestamp()
        self._sessions[session.id] = session
        logger.debug(f"Updated session {session.id}")
    
    def delete_session(self, session_id: UUID) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Deleted session {session_id}")
            return True
        return False
    
    def reset_session(self, session_id: UUID) -> Optional[Session]:
        """Reset session history while keeping metadata."""
        session = self.get_session(session_id)
        if session:
            session.history.messages.clear()
            session.context.clear()
            session.update_timestamp()
            self._sessions[session_id] = session
            logger.info(f"Reset session {session_id}")
            return session
        return None
    
    def list_sessions(self, user_email: Optional[str] = None) -> list[Session]:
        """List all sessions, optionally filtered by user."""
        sessions = list(self._sessions.values())
        if user_email:
            sessions = [s for s in sessions if s.user_email == user_email]
        return sessions
    
    def get_session_count(self) -> int:
        """Get total number of sessions."""
        return len(self._sessions)