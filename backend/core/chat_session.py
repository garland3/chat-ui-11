"""
Chat session shim for backward compatibility.

This is a temporary shim that delegates to the new ChatService.
It will be removed once all references are updated.
"""

import logging
from typing import Any, Dict
from uuid import UUID

from fastapi import WebSocket

from infrastructure.app_factory import app_factory
from infrastructure.transport.websocket_connection_adapter import WebSocketConnectionAdapter

logger = logging.getLogger(__name__)


class ChatSession:
    """
    Legacy chat session class that delegates to ChatService.
    This is a temporary shim for backward compatibility.
    """

    def __init__(self, uuid: UUID, websocket: WebSocket):
        """
        Initialize a chat session shim.

        Args:
            uuid: The session UUID.
            websocket: The WebSocket connection for this session.
        """
        self.session_id = uuid
        self.websocket = websocket
        
        # Create connection adapter
        self.connection_adapter = WebSocketConnectionAdapter(websocket)
        
        # Create chat service with connection
        self.chat_service = app_factory.create_chat_service(self.connection_adapter)
        
        logger.info(f"Created chat session shim for session {uuid}")

    async def handle_message(self, message: Dict[str, Any]):
        """
        Handle an incoming message from the client.

        Args:
            message: The message received from the client.
        """
        message_type = message.get("type")
        
        if message_type == "chat":
            # Extract parameters from message
            response = await self.chat_service.handle_chat_message(
                session_id=self.session_id,
                content=message.get("content", ""),
                model=message.get("model", ""),
                selected_tools=message.get("selected_tools"),
                selected_data_sources=message.get("selected_data_sources"),
                only_rag=message.get("only_rag", False),
                tool_choice_required=message.get("tool_choice_required", False),
                user_email=message.get("user"),
                agent_mode=message.get("agent_mode", False),
                agent_max_steps=message.get("agent_max_steps", 10)
            )
            
            # Send response
            await self.send_message(response)
            
        elif message_type == "download_file":
            # Handle file download
            response = await self.chat_service.handle_download_file(
                session_id=self.session_id,
                filename=message.get("filename", "")
            )
            await self.send_message(response)
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
            await self.send_message({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            })

    async def send_message(self, message: Dict[str, Any]):
        """
        Send a message to the client through the WebSocket.

        Args:
            message: The message to send to the client.
        """
        await self.websocket.send_json(message)

    async def end_session(self):
        """End the chat session."""
        self.chat_service.end_session(self.session_id)
        await self.websocket.close()
