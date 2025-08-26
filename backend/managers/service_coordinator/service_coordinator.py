"""Service coordinator for orchestrating chat flows - Phase 1A."""

import logging
from typing import Any, Callable, Dict, List, Optional, Awaitable
from uuid import UUID

from managers.session.session_manager import SessionManager
# Common models will be imported by session manager
from managers.llm.llm_manager import LLMManager
from managers.mcp.mcp_manager import MCPManager
from managers.tools.tool_caller import ToolCaller
from managers.tools.tool_models import ToolCall
from managers.auth.auth_manager import is_user_in_group

logger = logging.getLogger(__name__)


class ServiceCoordinator:
    """Main coordinator that orchestrates managers for chat flows."""
    
    def __init__(self, session_manager: SessionManager, llm_manager: LLMManager, mcp_manager: Optional[MCPManager] = None, tool_caller: Optional[ToolCaller] = None):
        """Initialize service coordinator with required managers."""
        self.session_manager = session_manager
        self.llm_manager = llm_manager
        self.mcp_manager = mcp_manager
        self.tool_caller = tool_caller
        logger.info("ServiceCoordinator initialized - Phase 1A")
    
    async def handle_chat_message(
        self,
        session_id: UUID,
        content: str,
        model: str,
        user_email: Optional[str] = None,
        temperature: float = 0.7,
        update_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        # Unused parameters for Phase 1A compatibility
    selected_tool_map: Optional[Dict[str, List[str]]] = None,
        selected_prompts: Optional[list] = None,
        selected_data_sources: Optional[list] = None,
        only_rag: bool = False,
        tool_choice_required: bool = False,
        agent_mode: bool = False,
        agent_max_steps: int = 10,
        files: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Handle a chat message - Phase 1A: LLM-only functionality."""
        try:
            # Get or create session
            session = self.session_manager.get_or_create_session(session_id, user_email)
            
            # Add user message to session
            user_message = session.add_user_message(content)
            logger.info(f"Added user message to session {session_id}: {len(content)} chars")
            
            # Update session in manager
            self.session_manager.update_session(session)
            
            # call log info, and log the first N=100 chars fo the message, list of seleced tools, agent_model, username, in 1 call 
            logger.info(f"Session {session_id} - Model: {model}, Temperature: {temperature}, User: {user_email}, Message: {content[:100]}..., Selected Tool Map: {selected_tool_map}, Agent Mode: {agent_mode}")
            
            # Check if we need to use tools
            if selected_tool_map and self.mcp_manager and self.tool_caller:
                # Get authorized and filtered tools using dependency injection
                filtered_tools = self.tool_caller.get_authorized_tools_for_user(
                    username=user_email or "",
                    selected_tool_map=selected_tool_map,
                    is_user_in_group=is_user_in_group,
                )
                logger.info(f"User {user_email} is authorized for tools (schemas count): {len(filtered_tools)}")
                
                logger.info(f"Using {len(filtered_tools)} tools for LLM call")
                
                # Call LLM with tools
                llm_response_data = await self.llm_manager.call_with_tools(
                    model, session.history, filtered_tools, "auto", temperature
                )
                
                llm_content = llm_response_data.get("content", "")
                tool_calls = llm_response_data.get("tool_calls", [])
                
                # Execute tool calls if any
                tool_results = []
                if tool_calls:
                    # logger.info(f"Executing {len(tool_calls)} tool calls")
                    
                    for tool_call_data in tool_calls:
                        tool_call = ToolCall(
                            id=tool_call_data["id"],
                            name=tool_call_data["name"],
                            arguments=tool_call_data["arguments"]
                        )
                        logging.info(f"Executing tool call: {tool_call.name} with args {tool_call.arguments}")
                        result = await self.tool_caller.execute_tool(tool_call)
                        
                        tool_results.append(result)
                        
                        # Add tool result to session history
                        session.add_tool_message(tool_call.name, result.content, tool_call.id)
                
                # Add assistant response to session
                assistant_message = session.add_assistant_message(llm_content, {
                    "model": model,
                    "temperature": temperature,
                    "tool_calls": tool_calls,
                    "tool_results": [{"id": r.tool_call_id, "content": r.content, "success": r.success} for r in tool_results]
                })
                
                final_response = llm_content
                if tool_results:
                    # If there were tool results, make a final call to get response
                    N_chars_per_message = 100
                    # print the message to the llm, for each message truncate. put in logging.info. 
                    truncated_messages = [message.content[:N_chars_per_message] for message in session.history.messages]
                    logging.info(f"Truncated messages for LLM call: {truncated_messages}")
                    final_llm_response = await self.llm_manager.call_plain(model, session.history, temperature)
                    final_response = final_llm_response
                    assistant_message = session.add_assistant_message(final_response, {
                        "model": model,
                        "temperature": temperature,
                    })
                
            else:
                # Plain LLM call without tools
                final_response = await self.llm_manager.call_plain(model, session.history, temperature)
                
                # Add assistant response to session
                assistant_message = session.add_assistant_message(final_response, {
                    "model": model,
                    "temperature": temperature,
                })
            
            # Update session
            self.session_manager.update_session(session)
            
            # Send final response via callback
            if update_callback:
                callback_message = {
                    "type": "chat_response",
                    "message": final_response,
                    "model": model,
                    "session_id": str(session_id),
                    "message_id": str(assistant_message.id),
                }
                logger.info(f"Sending response callback for session {session_id}: {len(final_response)} chars")
                try:
                    await update_callback(callback_message)
                    logger.info(f"Response callback sent successfully for session {session_id}")
                except Exception as callback_error:
                    logger.error(f"Error sending response callback: {callback_error}", exc_info=True)
            
            # logger.info(f"Chat message processed successfully for session {session_id}")
            
            return {
                "type": "chat_response",
                "message": final_response,
                "model": model,
                "session_id": str(session_id),
            }
            
        except Exception as e:
            logger.error(f"Error handling chat message for session {session_id}: {e}", exc_info=True)
            
            # Send error via callback if available
            if update_callback:
                await update_callback({
                    "type": "error",
                    "message": f"Error processing chat: {str(e)}",
                    "session_id": str(session_id),
                })
            
            return {
                "type": "error",
                "message": f"Error processing chat: {str(e)}",
                "session_id": str(session_id),
            }
    
    async def handle_reset_session(
        self,
        session_id: UUID,
        user_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle session reset."""
        try:
            session = self.session_manager.reset_session(session_id)
            if session:
                logger.info(f"Session {session_id} reset successfully")
                return {
                    "type": "session_reset",
                    "session_id": str(session_id),
                    "message": "Session reset successfully",
                }
            else:
                return {
                    "type": "error",
                    "message": "Session not found",
                    "session_id": str(session_id),
                }
        except Exception as e:
            logger.error(f"Error resetting session {session_id}: {e}", exc_info=True)
            return {
                "type": "error",
                "message": f"Error resetting session: {str(e)}",
                "session_id": str(session_id),
            }
    
    async def handle_download_file(
        self,
        session_id: UUID,
        filename: str,
        user_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle file download - placeholder for Phase 1A."""
        logger.info(f"File download requested for session {session_id}: {filename}")
        return {
            "type": "error",
            "message": "File download not implemented in Phase 1A",
            "session_id": str(session_id),
        }
    
    def end_session(self, session_id: UUID) -> None:
        """End a session (cleanup on disconnect)."""
        # For Phase 1A, we keep sessions in memory
        # In future phases, this might save to persistence
        logger.info(f"Session {session_id} ended")
        pass