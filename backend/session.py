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
        self.selected_prompts: List[str] = []
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
                elif message.get("type") == "download_file":
                    await self.handle_download_request(message)
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
        ********************************************************************
        ====================================================================

        IMPORTANT: This method is the core of the ChatSession logic.
        It processes incoming chat messages, handles tool calls, and manages
        the interaction with the LLM and MCP tools.

        ====================================================================
        ********************************************************************
        Process a chat message with LLM integration and tool calls.
        
        Routes to agent mode or normal processing based on message parameters.
        This method delegates to the MessageProcessor which contains the most
        critical logic in the entire codebase.
        """
        # Update uploaded files if provided
        if "files" in message:
            # logging the files for debugging
            logger.info("Received files for session %s: %s", self.session_id, message["files"])
            # Update the session's file mapping and send UI update
            await self.update_files_async(message["files"])
        
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
        # log all File names and length of the base 64 to the log, use fstring, offset with \t
        logger.info("Current files in session %s:", self.session_id)
        if not self.uploaded_files:
            logger.info("\tNo files uploaded yet.")
        else:
            # use fstring. 
            for filename, base64_data in self.uploaded_files.items():
                logger.info(f"\t{filename}: {len(base64_data)} bytes")

    async def update_files_async(self, files: Dict[str, str]) -> None:
        """Update the session's file mapping and send UI update"""
        self.update_files(files)
        await self.send_files_update()

    async def handle_download_request(self, message: Dict[str, Any]) -> None:
        """Handle file download requests from the client."""
        try:
            filename = message.get("filename")
            if not filename:
                await self.send_error("No filename provided for download")
                return
            
            if filename not in self.uploaded_files:
                await self.send_error(f"File '{filename}' not found in session")
                return
            
            # Send the file content back to the client
            await self.send_update_to_ui("file_download", {
                "filename": filename,
                "content_base64": self.uploaded_files[filename]
            })
            
            logger.info(f"Sent file download for '{filename}' to user {self.user_email}")
            
        except Exception as exc:
            logger.error("Error handling download request: %s", exc)
            await self.send_error("Failed to process download request")

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

    def _categorize_file_type(self, filename: str) -> str:
        """Categorize file based on extension."""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        code_extensions = {'py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css', 'java', 'cpp', 'c', 'rs', 'go', 'php', 'rb', 'swift'}
        image_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'svg', 'webp'}
        data_extensions = {'csv', 'json', 'xlsx', 'xls', 'xml'}
        document_extensions = {'pdf', 'doc', 'docx', 'txt', 'md', 'rtf'}
        
        if extension in code_extensions:
            return 'code'
        elif extension in image_extensions:
            return 'image'
        elif extension in data_extensions:
            return 'data'
        elif extension in document_extensions:
            return 'document'
        else:
            return 'other'

    def _get_file_metadata(self) -> Dict[str, Any]:
        """Get metadata for all files in the session."""
        files_metadata = []
        
        for filename, base64_content in self.uploaded_files.items():
            # Determine if file was uploaded or generated
            # Files with tool prefixes are generated (except for data files which keep original names)
            is_generated = '_' in filename and not filename.endswith(('.csv', '.json', '.txt', '.xlsx'))
            source_tool = filename.split('_')[0] if is_generated else None
            
            file_info = {
                'filename': filename,
                'size': len(base64_content),
                'type': self._categorize_file_type(filename),
                'source': 'generated' if is_generated else 'uploaded',
                'source_tool': source_tool,
                'extension': filename.split('.')[-1] if '.' in filename else ''
            }
            files_metadata.append(file_info)
        
        # Group by category
        categorized = {
            'code': [f for f in files_metadata if f['type'] == 'code'],
            'image': [f for f in files_metadata if f['type'] == 'image'], 
            'data': [f for f in files_metadata if f['type'] == 'data'],
            'document': [f for f in files_metadata if f['type'] == 'document'],
            'other': [f for f in files_metadata if f['type'] == 'other']
        }
        
        return {
            'total_files': len(files_metadata),
            'files': files_metadata,
            'categories': categorized
        }

    async def send_files_update(self) -> None:
        """Send updated file list to the UI."""
        try:
            files_metadata = self._get_file_metadata()
            await self.send_update_to_ui("files_update", files_metadata)
        except Exception as exc:
            logger.error("Error sending files update to UI for user %s: %s", self.user_email, exc)


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
