import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect

from mcp_client import MCPToolManager
from utils import call_llm_with_tools, validate_selected_tools
from rag_client import rag_client

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
        self.messages: List[Dict[str, Any]] = []
        self.model_name: Optional[str] = None
        self.selected_tools: List[str] = []
        self.validated_servers: List[str] = []
        self.selected_data_sources: List[str] = []
        self.only_rag: bool = True  # Default to true as per instructions
        self.session_id: str = id(self)

        logger.info(
            "ChatSession created for user: %s (session: %s)",
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
            await self.send_error("An internal server error occurred.")
            await self._trigger_callbacks("session_error", error=exc)

    async def handle_chat_message(self, message: Dict[str, Any]) -> None:
        """Process a chat message with LLM integration and tool calls."""
        try:
            await self._trigger_callbacks("before_message_processing", message=message)

            content = message.get("content", "")
            self.model_name = message.get("model", "")
            self.selected_tools = message.get("selected_tools", [])
            self.selected_data_sources = message.get("selected_data_sources", [])
            self.only_rag = message.get("only_rag", True)

            logger.info(
                "Received chat message from %s: content='%s...', model='%s', tools=%s, data_sources=%s, only_rag=%s",
                self.user_email,
                content[:50],
                self.model_name,
                self.selected_tools,
                self.selected_data_sources,
                self.only_rag,
            )

            if not content or not self.model_name:
                raise ValueError("Message content and model name are required.")

            await self._trigger_callbacks("before_user_message_added", content=content)

            user_message = {"role": "user", "content": content}
            self.messages.append(user_message)

            await self._trigger_callbacks("after_user_message_added", user_message=user_message)

            # Handle RAG-only mode vs normal processing pipeline
            if self.only_rag and self.selected_data_sources:
                # RAG-only mode: Skip tool calling and processing, query RAG directly
                logger.info(
                    "Using RAG-only mode for user %s with data sources: %s",
                    self.user_email,
                    self.selected_data_sources,
                )
                
                await self._trigger_callbacks("before_rag_call", messages=self.messages)
                llm_response = await self._handle_rag_only_query()
                await self._trigger_callbacks("after_rag_call", llm_response=llm_response)
            else:
                # Normal processing pipeline with optional RAG integration
                await self._trigger_callbacks("before_validation")
                self.validated_servers = await validate_selected_tools(
                    self.selected_tools, self.user_email, self.mcp_manager
                )
                await self._trigger_callbacks(
                    "after_validation", validated_servers=self.validated_servers
                )

                logger.info(
                    "Calling LLM %s for user %s with %d servers",
                    self.model_name,
                    self.user_email,
                    len(self.validated_servers),
                )

                await self._trigger_callbacks("before_llm_call", messages=self.messages)
                
                # If data sources are selected, integrate RAG results into the normal pipeline
                if self.selected_data_sources:
                    llm_response = await self._handle_rag_integrated_query()
                else:
                    llm_response = await call_llm_with_tools(
                        self.model_name,
                        self.messages,
                        self.validated_servers,
                        self.user_email,
                        self.websocket,
                        self.mcp_manager,
                    )
                    
                await self._trigger_callbacks("after_llm_call", llm_response=llm_response)

            assistant_message = {"role": "assistant", "content": llm_response}
            self.messages.append(assistant_message)
            await self._trigger_callbacks(
                "after_assistant_message_added", assistant_message=assistant_message
            )

            payload = {
                "type": "chat_response",
                "message": llm_response,
                "model": self.model_name,
                "user": self.user_email,
            }

            await self._trigger_callbacks("before_response_send", payload=payload)
            await self.send_json(payload)
            await self._trigger_callbacks("after_response_send", payload=payload)
            logger.info("LLM response sent to user %s", self.user_email)
        except Exception as exc:  # pragma: no cover - unexpected errors
            logger.error("Error handling chat message for %s: %s", self.user_email, exc, exc_info=True)
            await self._trigger_callbacks("message_error", error=exc)
            await self.send_error(f"Error processing message: {exc}")

    async def send_json(self, data: Dict[str, Any]) -> None:
        await self.websocket.send_text(json.dumps(data))

    async def send_error(self, error_message: str) -> None:
        await self.send_json({"type": "error", "message": error_message})
    
    async def _handle_rag_only_query(self) -> str:
        """Handle RAG-only queries by querying the first selected data source."""
        if not self.selected_data_sources:
            return "No data sources selected for RAG query."
        
        # Use the first selected data source for now
        # In the future, this could be enhanced to query multiple sources
        data_source = self.selected_data_sources[0]
        
        try:
            response = await rag_client.query_rag(
                self.user_email,
                data_source,
                self.messages
            )
            return response
        except Exception as exc:
            logger.error(f"Error in RAG-only query for {self.user_email}: {exc}")
            return f"Error querying RAG system: {str(exc)}"
    
    async def _handle_rag_integrated_query(self) -> str:
        """Handle queries that integrate RAG with normal LLM processing."""
        if not self.selected_data_sources:
            # Fallback to normal LLM call if no data sources
            return await call_llm_with_tools(
                self.model_name,
                self.messages,
                self.validated_servers,
                self.user_email,
                self.websocket,
                self.mcp_manager,
            )
        
        # Get RAG context from the first data source
        data_source = self.selected_data_sources[0]
        
        try:
            # Query RAG for context
            rag_response = await rag_client.query_rag(
                self.user_email,
                data_source,
                self.messages
            )
            
            # Integrate RAG context into the conversation
            # Add the RAG response as context for the LLM
            messages_with_rag = self.messages.copy()
            
            # Add RAG context as a system message
            rag_context_message = {
                "role": "system", 
                "content": f"Retrieved context from {data_source}:\n\n{rag_response}\n\nUse this context to inform your response to the user's query."
            }
            messages_with_rag.insert(-1, rag_context_message)  # Insert before the last user message
            
            # Call LLM with the enriched context
            llm_response = await call_llm_with_tools(
                self.model_name,
                messages_with_rag,
                self.validated_servers,
                self.user_email,
                self.websocket,
                self.mcp_manager,
            )
            
            return llm_response
            
        except Exception as exc:
            logger.error(f"Error in RAG-integrated query for {self.user_email}: {exc}")
            # Fallback to normal LLM call on RAG error
            return await call_llm_with_tools(
                self.model_name,
                self.messages,
                self.validated_servers,
                self.user_email,
                self.websocket,
                self.mcp_manager,
            )


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
