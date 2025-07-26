import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect

from mcp_client import MCPToolManager
from message_processor import MessageProcessor

logger = logging.getLogger(__name__)


class ChatSession:
    """Manage state and logic for a single WebSocket connection."""

    def __init__(
        self,
        websocket: WebSocket,
        user_email: str,
        mcp_manager: MCPToolManager,
        callbacks: Dict[str, List[Callable]],
    ) -> None:
        self.websocket = websocket
        self.user_email = user_email
        self.mcp_manager = mcp_manager
        self._callbacks = callbacks
        
        # Initialize messages with system prompt
        from prompt_utils import load_system_prompt
        system_content = load_system_prompt(user_email)
        self.messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": system_content,
            }
        ]
        self.model_name: Optional[str] = None
        self.selected_tools: List[str] = []
        self.validated_servers: List[str] = []
        self.selected_data_sources: List[str] = []
        self.only_rag: bool = True  # Default to true as per instructions
        self.tool_choice_required: bool = False  # Tool choice mode: False = auto, True = required
        self.session_id: str = id(self)
        self.uploaded_files: Dict[str, str] = {}  # filename -> base64 mapping
        
        # Initialize message processor
        self.message_processor = MessageProcessor(self)

        logger.info(
            "ChatSession created for user: %s (session: %s) with system prompt loaded",
            self.user_email,
            self.session_id,
        )

    async def _trigger_callbacks(self, event: str, **kwargs) -> None:
        """Run all callbacks registered for an event."""
        if event in self._callbacks:
            try:
                await asyncio.gather(*(cb(self, **kwargs) for cb in self._callbacks[event]))
            except Exception as exc:  # pragma: no cover - callback errors
                logger.error("Error in callback for event '%s': %s", event, exc, exc_info=True)

    async def run(self) -> None:
        """Receive and handle messages from the client."""
        try:
            await self._trigger_callbacks("session_started")

            while True:
                data = await self.websocket.receive_text()
                message = json.loads(data)

                if message.get("type") == "chat":
                    await self.handle_chat_message(message)
                else:
                    await self.send_error(f"Unknown message type: {message.get('type')}")
        except WebSocketDisconnect:
            logger.info("WebSocket connection closed for user: %s", self.user_email)
            await self._trigger_callbacks("session_ended")
        except Exception as exc:  # pragma: no cover - unexpected errors
            logger.error("Error in ChatSession for %s: %s", self.user_email, exc, exc_info=True)
            # Only try to send error if connection is still open
            try:
                if self.websocket.client_state.name != "DISCONNECTED":
                    await self.send_error("An internal server error occurred.")
            except Exception as send_exc:
                logger.error("Failed to send error message to user %s: %s", self.user_email, send_exc)
            await self._trigger_callbacks("session_error", error=exc)

    async def handle_chat_message(self, message: Dict[str, Any]) -> None:
        """
        Process a chat message with LLM integration and tool calls.
        
        Routes to agent mode or normal processing based on message parameters.
        This method delegates to the MessageProcessor which contains the most
        critical logic in the entire codebase.
        """
        # Update uploaded files if provided
        if "files" in message:
            self.update_files(message["files"])
        
        if message.get("agent_mode", False):
            await self.message_processor.handle_agent_mode_message(message)
        else:
            await self.message_processor.handle_chat_message(message)

    def update_files(self, files: Dict[str, str]) -> None:
        """Update the session's file mapping"""
        if files:
            self.uploaded_files.update(files)
            logger.info(
                "Updated files for session %s: %s", 
                self.session_id, 
                list(files.keys())
            )

    async def send_json(self, data: Dict[str, Any]) -> None:
        """Send JSON data to the WebSocket if connection is still open."""
        try:
            if self.websocket.client_state.name != "DISCONNECTED":
                await self.websocket.send_text(json.dumps(data))
            else:
                logger.warning("Attempted to send to disconnected WebSocket for user %s", self.user_email)
        except Exception as exc:
            logger.error("Error sending JSON to WebSocket for user %s: %s", self.user_email, exc)

    async def send_error(self, error_message: str) -> None:
        """Send error message to the WebSocket if connection is still open."""
        try:
            await self.send_json({"type": "error", "message": error_message})
        except Exception as exc:
            logger.error("Error sending error message to user %s: %s", self.user_email, exc)
    
    async def send_update_to_ui(self, update_type: str, data: Dict[str, Any]) -> None:
        """
        Send intermediate updates to the UI during message processing.
        
        Args:
            update_type: Type of update (tool_call, tool_result, etc.)
            data: Update data to send to the frontend
        """
        try:
            payload = {
                "type": "intermediate_update",
                "update_type": update_type,
                "data": data,
                "user": self.user_email
            }
            await self.send_json(payload)
            logger.info(f"Sent {update_type} update to user {self.user_email}")
        except Exception as exc:
            logger.error("Error sending update to UI for user %s: %s", self.user_email, exc)


class SessionManager:
    """Manage the lifecycle of all active ChatSession instances."""

    def __init__(self, mcp_manager: MCPToolManager) -> None:
        self.active_sessions: Dict[WebSocket, ChatSession] = {}
        self.callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.mcp_manager = mcp_manager

    def register_callback(self, event: str, func: Callable) -> None:
        """Register a callback function for a specific event."""
        self.callbacks[event].append(func)
        logger.info("Registered callback for event '%s': %s", event, func.__name__)

    def unregister_callback(self, event: str, func: Callable) -> None:
        """Remove a previously registered callback."""
        if event in self.callbacks and func in self.callbacks[event]:
            self.callbacks[event].remove(func)
            logger.info("Unregistered callback for event '%s': %s", event, func.__name__)

    async def connect(self, websocket: WebSocket, user_email: str) -> None:
        """Create and run a new ChatSession."""
        await websocket.accept()
        session = ChatSession(websocket, user_email, self.mcp_manager, self.callbacks)
        self.active_sessions[websocket] = session
        logger.info("Session started for %s, total active: %d", user_email, len(self.active_sessions))
        await session.run()

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a session after disconnection."""
        if websocket in self.active_sessions:
            session = self.active_sessions[websocket]
            del self.active_sessions[websocket]
            logger.info(
                "Session removed for %s, remaining active: %d",
                session.user_email,
                len(self.active_sessions),
            )

    def get_session_count(self) -> int:
        """Return the number of active sessions."""
        return len(self.active_sessions)

    def get_sessions_for_user(self, user_email: str) -> List[ChatSession]:
        """Return all active sessions for a specific user."""
        return [s for s in self.active_sessions.values() if s.user_email == user_email]
