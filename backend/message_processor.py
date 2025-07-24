"""
Message processing module containing the core chat message handling logic.

This module contains the MessageProcessor class which handles the most critical
function in the codebase: processing incoming chat messages through the complete
pipeline including RAG, tool validation, LLM calls, and callback coordination.
"""

import logging
from typing import Any, Dict

from utils import call_llm_with_tools, validate_selected_tools
import rag_client

logger = logging.getLogger(__name__)


class MessageProcessor:
    """
    Handles the core message processing pipeline for chat sessions.
    
    This class contains the most important logic in the entire codebase,
    orchestrating the complete message processing flow including:
    - RAG-only vs integrated processing modes
    - Tool validation and LLM calls  
    - Callback coordination throughout the lifecycle
    - WebSocket message and response handling
    """
    
    def __init__(self, session):
        """
        Initialize the message processor with a reference to the chat session.
        
        Args:
            session: ChatSession instance that owns this processor
        """
        self.session = session
        
    async def handle_chat_message(self, message: Dict[str, Any]) -> None:
        """
        Process a chat message with LLM integration and tool calls.
        
        This is the most critical function in the entire codebase. It orchestrates
        the complete message processing pipeline including RAG integration,
        tool validation, LLM calls, and callback coordination.
        
        Args:
            message: The incoming chat message with content, model, tools, etc.
        """
        try:
            await self.session._trigger_callbacks("before_message_processing", message=message)

            content = message.get("content", "")
            self.session.model_name = message.get("model", "")
            self.session.selected_tools = message.get("selected_tools", [])
            self.session.selected_data_sources = message.get("selected_data_sources", [])
            self.session.only_rag = message.get("only_rag", True)

            logger.info(
                "Received chat message from %s: content='%s...', model='%s', tools=%s, data_sources=%s, only_rag=%s",
                self.session.user_email,
                content[:50],
                self.session.model_name,
                self.session.selected_tools,
                self.session.selected_data_sources,
                self.session.only_rag,
            )

            if not content or not self.session.model_name:
                raise ValueError("Message content and model name are required.")

            await self.session._trigger_callbacks("before_user_message_added", content=content)

            user_message = {"role": "user", "content": content}
            self.session.messages.append(user_message)

            await self.session._trigger_callbacks("after_user_message_added", user_message=user_message)

            # Handle RAG-only mode vs normal processing pipeline
            if self.session.only_rag and self.session.selected_data_sources:
                # RAG-only mode: Skip tool calling and processing, query RAG directly
                logger.info(
                    "Using RAG-only mode for user %s with data sources: %s",
                    self.session.user_email,
                    self.session.selected_data_sources,
                )
                
                await self.session._trigger_callbacks("before_rag_call", messages=self.session.messages)
                llm_response = await self._handle_rag_only_query()
                await self.session._trigger_callbacks("after_rag_call", llm_response=llm_response)
            else:
                # Normal processing pipeline with optional RAG integration
                await self.session._trigger_callbacks("before_validation")
                self.session.validated_servers = await validate_selected_tools(
                    self.session.selected_tools, self.session.user_email, self.session.mcp_manager
                )
                await self.session._trigger_callbacks(
                    "after_validation", validated_servers=self.session.validated_servers
                )

                logger.info(
                    "Calling LLM %s for user %s with %d servers",
                    self.session.model_name,
                    self.session.user_email,
                    len(self.session.validated_servers),
                )

                await self.session._trigger_callbacks("before_llm_call", messages=self.session.messages)
                
                # If data sources are selected, integrate RAG results into the normal pipeline
                if self.session.selected_data_sources:
                    llm_response = await self._handle_rag_integrated_query()
                else:
                    llm_response = await call_llm_with_tools(
                        self.session.model_name,
                        self.session.messages,
                        self.session.validated_servers,
                        self.session.user_email,
                        self.session.websocket,
                        self.session.mcp_manager,
                        self.session,  # Pass session for UI updates
                    )
                    
                await self.session._trigger_callbacks("after_llm_call", llm_response=llm_response)

            assistant_message = {"role": "assistant", "content": llm_response}
            self.session.messages.append(assistant_message)
            await self.session._trigger_callbacks(
                "after_assistant_message_added", assistant_message=assistant_message
            )

            payload = {
                "type": "chat_response",
                "message": llm_response,
                "model": self.session.model_name,
                "user": self.session.user_email,
            }

            await self.session._trigger_callbacks("before_response_send", payload=payload)
            await self.session.send_json(payload)
            await self.session._trigger_callbacks("after_response_send", payload=payload)
            logger.info("LLM response sent to user %s", self.session.user_email)
        except Exception as exc:  # pragma: no cover - unexpected errors
            logger.error("Error handling chat message for %s: %s", self.session.user_email, exc, exc_info=True)
            await self.session._trigger_callbacks("message_error", error=exc)
            await self.session.send_error(f"Error processing message: {exc}")

    async def _handle_rag_only_query(self) -> str:
        """Handle RAG-only queries by querying the first selected data source."""
        if not self.session.selected_data_sources:
            return "No data sources selected for RAG query."
        
        # Use the first selected data source for now
        # In the future, this could be enhanced to query multiple sources
        data_source = self.session.selected_data_sources[0]
        
        try:
            response = await rag_client.rag_client.query_rag(
                self.session.user_email,
                data_source,
                self.session.messages
            )
            return response
        except Exception as exc:
            logger.error(f"Error in RAG-only query for {self.session.user_email}: {exc}")
            return f"Error querying RAG system: {str(exc)}"
    
    async def _handle_rag_integrated_query(self) -> str:
        """Handle queries that integrate RAG with normal LLM processing."""
        if not self.session.selected_data_sources:
            # Fallback to normal LLM call if no data sources
            return await call_llm_with_tools(
                self.session.model_name,
                self.session.messages,
                self.session.validated_servers,
                self.session.user_email,
                self.session.websocket,
                self.session.mcp_manager,
                self.session,  # Pass session for UI updates
            )
        
        # Get RAG context from the first data source
        data_source = self.session.selected_data_sources[0]
        
        try:
            # Query RAG for context
            rag_response = await rag_client.rag_client.query_rag(
                self.session.user_email,
                data_source,
                self.session.messages
            )
            
            # Integrate RAG context into the conversation
            # Add the RAG response as context for the LLM
            messages_with_rag = self.session.messages.copy()
            
            # Add RAG context as a system message
            rag_context_message = {
                "role": "system", 
                "content": f"Retrieved context from {data_source}:\n\n{rag_response}\n\nUse this context to inform your response to the user's query."
            }
            messages_with_rag.insert(-1, rag_context_message)  # Insert before the last user message
            
            # Call LLM with the enriched context
            llm_response = await call_llm_with_tools(
                self.session.model_name,
                messages_with_rag,
                self.session.validated_servers,
                self.session.user_email,
                self.session.websocket,
                self.session.mcp_manager,
                self.session,  # Pass session for UI updates
            )
            
            return llm_response
            
        except Exception as exc:
            logger.error(f"Error in RAG-integrated query for {self.session.user_email}: {exc}")
            # Fallback to normal LLM call on RAG error
            return await call_llm_with_tools(
                self.session.model_name,
                self.session.messages,
                self.session.validated_servers,
                self.session.user_email,
                self.session.websocket,
                self.session.mcp_manager,
                self.session,  # Pass session for UI updates
            )