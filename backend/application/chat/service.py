"""Chat service - core business logic for chat operations."""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from domain.errors import SessionError, ValidationError
from domain.messages.models import (
    ConversationHistory,
    Message,
    MessageRole,
    MessageType,
    ToolCall,
    ToolResult
)
from domain.sessions.models import Session
from interfaces.llm import LLMProtocol, LLMResponse
from interfaces.tools import ToolManagerProtocol
from interfaces.transport import ChatConnectionProtocol

logger = logging.getLogger(__name__)


class ChatService:
    """
    Core chat service that orchestrates chat operations.
    Transport-agnostic, testable business logic.
    """
    
    def __init__(
        self,
        llm: LLMProtocol,
        tool_manager: Optional[ToolManagerProtocol] = None,
        connection: Optional[ChatConnectionProtocol] = None
    ):
        """
        Initialize chat service with dependencies.
        
        Args:
            llm: LLM protocol implementation
            tool_manager: Optional tool manager
            connection: Optional connection for sending updates
        """
        self.llm = llm
        self.tool_manager = tool_manager
        self.connection = connection
        self.sessions: Dict[UUID, Session] = {}
    
    async def create_session(
        self,
        session_id: UUID,
        user_email: Optional[str] = None
    ) -> Session:
        """Create a new chat session."""
        session = Session(id=session_id, user_email=user_email)
        self.sessions[session_id] = session
        logger.info(f"Created session {session_id} for user {user_email}")
        return session
    
    async def handle_chat_message(
        self,
        session_id: UUID,
        content: str,
        model: str,
        selected_tools: Optional[List[str]] = None,
        selected_data_sources: Optional[List[str]] = None,
        only_rag: bool = False,
        tool_choice_required: bool = False,
        user_email: Optional[str] = None,
        agent_mode: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Handle incoming chat message.
        
        Returns:
            Response dictionary to send to client
        """
        # Log all input arguments with content trimmed to 100 chars
        content_preview = content[:100] + "..." if len(content) > 100 else content
        logger.info(
            f"handle_chat_message called - session_id: {session_id}, "
            f"content: '{content_preview}', model: {model}, "
            f"selected_tools: {selected_tools}, selected_data_sources: {selected_data_sources}, "
            f"only_rag: {only_rag}, tool_choice_required: {tool_choice_required}, "
            f"user_email: {user_email}, agent_mode: {agent_mode}, "
            f"kwargs: {kwargs}"
        )
        # Get or create session
        session = self.sessions.get(session_id)
        if not session:
            session = await self.create_session(session_id, user_email)
        
        # Add user message to history
        user_message = Message(
            role=MessageRole.USER,
            content=content,
            metadata={"model": model}
        )
        session.history.add_message(user_message)
        session.update_timestamp()
        
        try:
            # Get conversation history for LLM
            messages = session.history.get_messages_for_llm()
            
            # Determine which LLM method to use
            if agent_mode:
                response = await self._handle_agent_mode(
                    session, model, messages, selected_tools, selected_data_sources, kwargs.get("agent_max_steps", 10)
                )
            elif selected_tools and not only_rag:
                response = await self._handle_tools_mode(
                    session, model, messages, selected_tools, selected_data_sources, user_email, tool_choice_required
                )
            elif selected_data_sources:
                response = await self._handle_rag_mode(
                    session, model, messages, selected_data_sources, user_email
                )
            else:
                response = await self._handle_plain_mode(session, model, messages)
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling chat message: {e}", exc_info=True)
            return {
                "type": MessageType.ERROR.value,
                "message": str(e)
            }
    
    async def _handle_plain_mode(
        self,
        session: Session,
        model: str,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Handle plain LLM call without tools or RAG."""
        # Note: The actual implementation of call_plain is in backend/modules/llm/caller.py
        # The self.llm instance is an LLMCaller object injected via AppFactory
        response_content = await self.llm.call_plain(model, messages)
        
        # Add assistant message to history
        assistant_message = Message(
            role=MessageRole.ASSISTANT,
            content=response_content
        )
        session.history.add_message(assistant_message)
        
        return {
            "type": MessageType.CHAT_RESPONSE.value,
            "message": response_content
        }
    
    async def _handle_rag_mode(
        self,
        session: Session,
        model: str,
        messages: List[Dict[str, str]],
        data_sources: List[str],
        user_email: str
    ) -> Dict[str, Any]:
        """Handle LLM call with RAG integration."""
        response_content = await self.llm.call_with_rag(
            model, messages, data_sources, user_email
        )
        
        # Add assistant message to history
        assistant_message = Message(
            role=MessageRole.ASSISTANT,
            content=response_content,
            metadata={"data_sources": data_sources}
        )
        session.history.add_message(assistant_message)
        
        return {
            "type": MessageType.CHAT_RESPONSE.value,
            "message": response_content
        }
    
    async def _handle_tools_mode(
        self,
        session: Session,
        model: str,
        messages: List[Dict[str, str]],
        selected_tools: List[str],
        data_sources: Optional[List[str]],
        user_email: Optional[str],
        tool_choice_required: bool
    ) -> Dict[str, Any]:
        """Handle LLM call with tools (and optionally RAG)."""
        try:
            if not self.tool_manager:
                raise ValidationError("Tool manager not configured")
            
            # Get tool schemas
            logger.info(f"Getting tools schema for selected tools: {selected_tools}")
            tools_schema = self.tool_manager.get_tools_schema(selected_tools)
            tool_choice = "required" if tool_choice_required else "auto"
            
            logger.info(f"Got {len(tools_schema)} tool schemas, tool_choice: {tool_choice}")
        except Exception as e:
            logger.error(f"Error getting tools schema: {e}", exc_info=True)
            raise ValidationError(f"Failed to get tools schema: {str(e)}")
        
        # Call LLM with tools
        try:
            if data_sources and user_email:
                logger.info(f"Calling LLM with RAG and tools for user {user_email}")
                llm_response = await self.llm.call_with_rag_and_tools(
                    model, messages, data_sources, tools_schema, user_email, tool_choice
                )
            else:
                logger.info(f"Calling LLM with tools only")
                llm_response = await self.llm.call_with_tools(
                    model, messages, tools_schema, tool_choice
                )
            
            logger.info(f"LLM response received, has_tool_calls: {llm_response.has_tool_calls()}")
        except Exception as e:
            logger.error(f"Error calling LLM with tools: {e}", exc_info=True)
            raise ValidationError(f"Failed to call LLM with tools: {str(e)}")
        
        # Process tool calls if present
        if llm_response.has_tool_calls():
            try:
                logger.info(f"Executing {len(llm_response.tool_calls)} tool calls")
                tool_results = await self._execute_tool_calls(
                    llm_response.tool_calls, session
                )
                logger.info(f"Tool execution completed, got {len(tool_results)} results")
            except Exception as e:
                logger.error(f"Error executing tool calls: {e}", exc_info=True)
                raise ValidationError(f"Failed to execute tool calls: {str(e)}")
            
            # Add tool results to messages and call LLM again
            # First add the assistant message with both content and tool calls
            messages.append({
                "role": "assistant",
                "content": llm_response.content,  # Preserve original content
                "tool_calls": llm_response.tool_calls
            })
            
            # Then add tool results
            for result in tool_results:
                messages.append({
                    "role": "tool",
                    "content": result.content,
                    "tool_call_id": result.tool_call_id
                })
            
            # Check if any tool calls were canvas tools (no follow-up needed)
            canvas_tool_calls = [tc for tc in llm_response.tool_calls if tc.name == "canvas_canvas"]
            has_only_canvas_tools = len(canvas_tool_calls) == len(llm_response.tool_calls)
            
            if has_only_canvas_tools:
                # Canvas tools don't need follow-up, just return the original content
                final_response = llm_response.content or "Content displayed in canvas."
            else:
                # Get final response after tool execution for non-canvas tools
                final_response = await self.llm.call_plain(model, messages)
            
            # Add to history
            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=final_response,
                metadata={"tools_used": selected_tools}
            )
            session.history.add_message(assistant_message)
            
            return {
                "type": MessageType.CHAT_RESPONSE.value,
                "message": final_response
            }
        else:
            # No tool calls, just return the response
            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=llm_response.content
            )
            session.history.add_message(assistant_message)
            
            return {
                "type": MessageType.CHAT_RESPONSE.value,
                "message": llm_response.content
            }
    
    async def _handle_agent_mode(
        self,
        session: Session,
        model: str,
        messages: List[Dict[str, str]],
        selected_tools: Optional[List[str]],
        data_sources: Optional[List[str]],
        max_steps: int
    ) -> Dict[str, Any]:
        """Handle agent mode with iterative tool use."""
        # Send agent start update
        if self.connection:
            await self.connection.send_json({
                "type": MessageType.AGENT_UPDATE.value,
                "update_type": "agent_start",
                "max_steps": max_steps
            })
        
        steps = 0
        final_response = None
        
        while steps < max_steps:
            steps += 1
            
            # Send step update
            if self.connection:
                await self.connection.send_json({
                    "type": MessageType.AGENT_UPDATE.value,
                    "update_type": "agent_turn_start",
                    "step": steps
                })
            
            # Get tool schemas if available
            tools_schema = []
            if selected_tools and self.tool_manager:
                tools_schema = self.tool_manager.get_tools_schema(selected_tools)
            
            # Call LLM
            if data_sources and session.user_email:
                llm_response = await self.llm.call_with_rag_and_tools(
                    model, messages, data_sources, tools_schema, session.user_email, "auto"
                )
            elif tools_schema:
                llm_response = await self.llm.call_with_tools(
                    model, messages, tools_schema, "auto"
                )
            else:
                content = await self.llm.call_plain(model, messages)
                llm_response = LLMResponse(content=content)
            
            # Check if we have tool calls
            if llm_response.has_tool_calls():
                # Execute tools
                tool_results = await self._execute_tool_calls(
                    llm_response.tool_calls, session
                )
                
                # Add to messages
                for tool_call, result in zip(llm_response.tool_calls, tool_results):
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "content": result.content,
                        "tool_call_id": result.tool_call_id
                    })
                    
                    # Send tool call update
                    if self.connection:
                        await self.connection.send_json({
                            "type": MessageType.AGENT_UPDATE.value,
                            "update_type": "agent_tool_call",
                            "tool_name": tool_call.get("function", {}).get("name"),
                            "result": result.content
                        })
            else:
                # No more tool calls, we have the final response
                final_response = llm_response.content
                break
        
        if not final_response:
            # Reached max steps, get final response
            final_response = await self.llm.call_plain(model, messages)
        
        # Add to history
        assistant_message = Message(
            role=MessageRole.ASSISTANT,
            content=final_response,
            metadata={"agent_mode": True, "steps": steps}
        )
        session.history.add_message(assistant_message)
        
        # Send completion update
        if self.connection:
            await self.connection.send_json({
                "type": MessageType.AGENT_UPDATE.value,
                "update_type": "agent_completion",
                "steps": steps
            })
        
        return {
            "type": MessageType.CHAT_RESPONSE.value,
            "message": final_response
        }
    
    async def _execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        session: Session
    ) -> List[ToolResult]:
        """Execute tool calls and return results."""
        if not self.tool_manager:
            raise ValidationError("Tool manager not configured")
        
        results = []
        for tool_call_dict in tool_calls:
            tool_call = ToolCall(
                id=tool_call_dict.get("id", ""),
                name=tool_call_dict.get("function", {}).get("name", ""),
                arguments=tool_call_dict.get("function", {}).get("arguments", {})
            )
            
            # Parse arguments if they're a string
            if isinstance(tool_call.arguments, str):
                import json
                try:
                    tool_call.arguments = json.loads(tool_call.arguments)
                except json.JSONDecodeError:
                    tool_call.arguments = {}
            
            result = await self.tool_manager.execute_tool(
                tool_call,
                context={"session_id": session.id, "user_email": session.user_email}
            )
            results.append(result)
            
            # Send tool result update if connection available
            if self.connection:
                await self.connection.send_json({
                    "type": MessageType.INTERMEDIATE_UPDATE.value,
                    "update_type": "tool_result",
                    "tool_name": tool_call.name,
                    "result": result.content
                })
        
        return results
    
    async def handle_download_file(
        self,
        session_id: UUID,
        filename: str
    ) -> Dict[str, Any]:
        """Handle file download request."""
        # This would integrate with file storage
        # For now, return a placeholder response
        return {
            "type": MessageType.FILE_DOWNLOAD.value,
            "filename": filename,
            "content": "File download not yet implemented"
        }
    
    def get_session(self, session_id: UUID) -> Optional[Session]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def end_session(self, session_id: UUID) -> None:
        """End a session."""
        if session_id in self.sessions:
            self.sessions[session_id].active = False
            logger.info(f"Ended session {session_id}")
