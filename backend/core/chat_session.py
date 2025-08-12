"""Chat session class."""

import logging
from typing import Any, Dict

from fastapi import WebSocket

from core.orchestrator import orchestrator

logger = logging.getLogger(__name__)

class ChatSession:
    """
    Represents a single chat session.
    """

    def __init__(self, session_id: str, websocket: WebSocket):
        """
        Initialize a new chat session.

        Args:
            session_id: The ID of the session.
            websocket: The WebSocket connection for this session.
        """
        self.session_id = session_id
        self.websocket = websocket
        self.history = []
        self.context = {}

    async def handle_message(self, message: Dict[str, Any]):
        """
        Handle an incoming message from the client.

        Args:
            message: The message received from the client.
        """
        message_type = message.get("type")
        if message_type == "chat":
            content = message.get("content")
            self.history.append({"role": "user", "content": content})
            
            # Get LLM caller from orchestrator
            llm_caller = orchestrator.get_llm_caller()

            # Get model from message
            model_name = message.get("model")
            if not model_name:
                await self.send_message({"type": "error", "message": "No model specified in the message."})
                return

            # Call the LLM with the conversation history
            response = await llm_caller.call_plain(model_name, self.history)
            
            # Add assistant response to history
            self.history.append({"role": "assistant", "content": response})
            
            # Send response to client
            await self.send_message({"type": "chat_response", "message": response})
        else:
            logger.warning(f"Unknown message type: {message_type}")

    async def send_message(self, message: Dict[str, Any]):
        """
        Send a message to the client through the WebSocket.

        Args:
            message: The message to send to the client.
        """
        await self.websocket.send_json(message)

    # end session
    async def end_session(self, id: str):
        """
        End the chat session.

        Args:
            id: The ID of the session to end.
        """
        if self.session_id == id:
            await self.websocket.close()