import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect

from mcp_client import MCPToolManager
from message_processor import MessageProcessor
from s3_client import s3_client

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
        self.uploaded_files: Dict[str, str] = {}  # filename -> s3_key mapping
        self.file_references: Dict[str, Dict[str, Any]] = {}  # filename -> file metadata
        
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
            logger.info("Received files for session %s: %s", self.session_id, list(message["files"].keys()))
            # Upload files to S3 and update the session's file mapping
            await self.upload_files_to_s3_async(message["files"])
        
        if message.get("agent_mode", False):
            await self.message_processor.handle_agent_mode_message(message)
        else:
            await self.message_processor.handle_chat_message(message)

    async def upload_files_to_s3_async(self, files: Dict[str, str]) -> None:
        """Upload files to S3 and update the session's file mapping"""
        if not files:
            return
            
        try:
            for filename, base64_content in files.items():
                # Determine content type based on filename
                content_type = self._get_content_type(filename)
                
                # Upload to S3
                file_metadata = await s3_client.upload_file(
                    user_email=self.user_email,
                    filename=filename,
                    content_base64=base64_content,
                    content_type=content_type,
                    source_type="user"
                )
                
                # Store S3 key and metadata
                self.uploaded_files[filename] = file_metadata["key"]
                self.file_references[filename] = file_metadata
                
                logger.info(
                    f"File uploaded to S3: {filename} -> {file_metadata['key']} for session {self.session_id}"
                )
            
            # Send updated file list to UI
            await self.send_files_update()
            
        except Exception as exc:
            logger.error(f"Error uploading files to S3 for session {self.session_id}: {exc}")
            await self.send_error(f"Failed to upload files: {str(exc)}")

    async def store_generated_file_in_s3(self, filename: str, content_base64: str, source_tool: str = "system") -> str:
        """Store a tool-generated file in S3 and return the S3 key"""
        try:
            content_type = self._get_content_type(filename)
            
            file_metadata = await s3_client.upload_file(
                user_email=self.user_email,
                filename=filename,
                content_base64=content_base64,
                content_type=content_type,
                tags={"source_tool": source_tool},
                source_type="tool"
            )
            
            # Store in session
            self.uploaded_files[filename] = file_metadata["key"]
            self.file_references[filename] = file_metadata
            
            logger.info(
                f"Generated file stored in S3: {filename} -> {file_metadata['key']} for session {self.session_id}"
            )
            
            # Send updated file list to UI
            await self.send_files_update()
            
            return file_metadata["key"]
            
        except Exception as exc:
            logger.error(f"Error storing generated file in S3: {exc}")
            raise

    def _get_content_type(self, filename: str) -> str:
        """Determine content type based on filename"""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        content_types = {
            'txt': 'text/plain',
            'md': 'text/markdown',
            'json': 'application/json',
            'csv': 'text/csv',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'py': 'text/x-python',
            'js': 'application/javascript',
            'html': 'text/html',
            'css': 'text/css'
        }
        
        return content_types.get(extension, 'application/octet-stream')

    async def get_file_content_by_name(self, filename: str) -> Optional[str]:
        """Get base64 content of a file by filename (for tool access)"""
        try:
            if filename not in self.uploaded_files:
                logger.warning(f"File not found in session: {filename}")
                return None
                
            s3_key = self.uploaded_files[filename]
            file_data = await s3_client.get_file(self.user_email, s3_key)
            
            if file_data:
                return file_data["content_base64"]
            else:
                logger.warning(f"File not found in S3: {s3_key}")
                return None
                
        except Exception as exc:
            logger.error(f"Error getting file content for {filename}: {exc}")
            return None

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
            
            # Get S3 key for the file
            s3_key = self.uploaded_files[filename]
            
            # Retrieve file from S3
            file_data = await s3_client.get_file(self.user_email, s3_key)
            if not file_data:
                await self.send_error(f"File '{filename}' not found in storage")
                return
            
            # Send the file content back to the client
            await self.send_update_to_ui("file_download", {
                "filename": filename,
                "content_base64": file_data["content_base64"]
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
        
        for filename, s3_key in self.uploaded_files.items():
            # Get metadata from file references
            file_metadata = self.file_references.get(filename, {})
            
            # Determine source type from tags or metadata
            tags = file_metadata.get("tags", {})
            source_type = tags.get("source", "uploaded")
            source_tool = tags.get("source_tool", None)
            
            file_info = {
                'filename': filename,
                's3_key': s3_key,
                'size': file_metadata.get("size", 0),
                'type': self._categorize_file_type(filename),
                'source': source_type,
                'source_tool': source_tool,
                'extension': filename.split('.')[-1] if '.' in filename else '',
                'last_modified': file_metadata.get("last_modified"),
                'content_type': file_metadata.get("content_type", "application/octet-stream")
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
