"""Session management for chat sessions."""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Manages chat sessions including state, history, and context.
    Integrates with the orchestrator to utilize various modules.
    """

    def __init__(self, orchestrator):
        """
        Initialize the session manager with a reference to the orchestrator.

        Args:
            orchestrator: The MessageOrchestrator instance to coordinate with modules
        """
        self.orchestrator = orchestrator
        self.sessions: Dict[str, Dict[str, Any]] = {}

        logger.info("Session manager initialized")

    def create_session(self, websocket=None) -> str:
        """
        Create a new chat session.

        Args:
            websocket: Optional WebSocket connection for this session

        Returns:
            str: The session ID
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "websocket": websocket,
            "history": [],
            "context": {},
            "active": True
        }

        logger.info(f"Created new session: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session by its ID.

        Args:
            session_id: The ID of the session to retrieve

        Returns:
            Optional[Dict]: The session data if found, None otherwise
        """
        return self.sessions.get(session_id)

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session data.

        Args:
            session_id: The ID of the session to update
            updates: Dictionary of updates to apply to the session

        Returns:
            bool: True if session was found and updated, False otherwise
        """
        if session_id in self.sessions:
            self.sessions[session_id].update(updates)
            return True
        return False

    def end_session(self, session_id: str) -> bool:
        """
        End a chat session.

        Args:
            session_id: The ID of the session to end

        Returns:
            bool: True if session was found and ended, False otherwise
        """
        if session_id in self.sessions:
            self.sessions[session_id]["active"] = False
            self.sessions[session_id]["ended_at"] = datetime.utcnow().isoformat()

            # Clean up resources if needed
            if "websocket" in self.sessions[session_id]:
                websocket = self.sessions[session_id]["websocket"]
                if websocket:
                    # Close the connection if it's still open
                    try:
                        # This would be handled by the websocket endpoint in practice
                        pass
                    except Exception as e:
                        logger.warning(f"Error closing websocket for session {session_id}: {e}")

            logger.info(f"Ended session: {session_id}")
            return True
        return False

    def add_to_history(self, session_id: str, message: Dict[str, Any]) -> bool:
        """
        Add a message to a session's history.

        Args:
            session_id: The ID of the session
            message: The message to add to history

        Returns:
            bool: True if message was added successfully, False otherwise
        """
        if session_id in self.sessions:
            self.sessions[session_id]["history"].append(message)
            return True
        return False

    def get_session_history(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get the message history for a session.

        Args:
            session_id: The ID of the session

        Returns:
            Optional[List]: The session history if session exists, None otherwise
        """
        session = self.get_session(session_id)
        if session:
            return session.get("history", [])
        return None

    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the context for a session.

        Args:
            session_id: The ID of the session

        Returns:
            Optional[Dict]: The session context if session exists, None otherwise
        """
        session = self.get_session(session_id)
        if session:
            return session.get("context", {})
        return None

    def update_session_context(self, session_id: str, context_updates: Dict[str, Any]) -> bool:
        """
        Update the context for a session.

        Args:
            session_id: The ID of the session
            context_updates: Dictionary of updates to apply to the session context

        Returns:
            bool: True if context was updated successfully, False otherwise
        """
        if session_id in self.sessions:
            if "context" not in self.sessions[session_id]:
                self.sessions[session_id]["context"] = {}
            self.sessions[session_id]["context"].update(context_updates)
            return True
        return False

    def cleanup_inactive_sessions(self):
        """
        Clean up inactive sessions older than a certain threshold.
        """
        # Implement session cleanup logic here
        pass

# Global session manager instance
session_manager = SessionManager(orchestrator)
