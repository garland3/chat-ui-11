"""Service coordinator for orchestrating chat flows - Phase 1A."""

import logging
from typing import Any, Callable, Dict, List, Optional, Awaitable
from uuid import UUID

from managers.session.session_manager import SessionManager
from managers.prompt.prompt_utils import extract_special_system_prompt

# Common models will be imported by session manager
from managers.llm.llm_manager import LLMManager
from managers.mcp.mcp_manager import MCPManager
from managers.tools.tool_caller import ToolCaller
from managers.agent.tool_call_orchestrator import ToolCallOrchestrator

logger = logging.getLogger(__name__)


class ServiceCoordinator:
    """Main coordinator that orchestrates managers for chat flows."""

    def __init__(
        self,
        session_manager: SessionManager,
        llm_manager: LLMManager,
        mcp_manager: Optional[MCPManager] = None,
        tool_caller: Optional[ToolCaller] = None,
        tool_orchestrator: Optional[ToolCallOrchestrator] = None,
    ):
        """Initialize service coordinator with required managers."""
        self.session_manager = session_manager
        self.llm_manager = llm_manager
        self.mcp_manager = mcp_manager
        self.tool_caller = tool_caller
        self.tool_orchestrator = tool_orchestrator

        logger.info("ServiceCoordinator initialized - Phase 1A")

    async def handle_chat_message(
        self,
        session_id: UUID,
        content: str,
        model: str,
        user_email: Optional[str] = None,
        special_system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        update_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        # Unused parameters for Phase 1A compatibility
        selected_tool_map: Optional[Dict[str, List[str]]] = None,
        selected_prompt_map: Optional[Dict[str, List[str]]] = None,
        selected_data_sources: Optional[list] = None,
        only_rag: bool = False,
        tool_choice_required: bool = False,
        agent_mode: bool = False,
        agent_max_steps: int = 10,
        files: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Handle a chat message - Phase 1A: LLM-only functionality."""
        try:
            # Derive special system prompt if not explicitly provided
            if not special_system_prompt:
                special_system_prompt = extract_special_system_prompt(
                    selected_prompt_map=selected_prompt_map,
                )
                # If nothing extracted and MCP prompts were selected, fetch the first prompt's content
                if (
                    not special_system_prompt
                    and selected_prompt_map
                    and self.mcp_manager
                ):
                    try:
                        # Deterministic iteration over servers
                        for server, prompts in selected_prompt_map.items():
                            if not isinstance(prompts, list) or not prompts:
                                continue
                            prompt_name = prompts[0]
                            if (
                                not isinstance(prompt_name, str)
                                or not prompt_name.strip()
                            ):
                                continue
                            full_name = f"{server}_{prompt_name}"
                            prompt_obj = await self.mcp_manager.get_prompt(
                                full_name, {}
                            )
                            prompt_text = None
                            if isinstance(prompt_obj, str):
                                prompt_text = prompt_obj
                            else:
                                # Attempt FastMCP PromptMessage-like shape: content list with .text
                                content_field = getattr(prompt_obj, "content", None)
                                if isinstance(content_field, list) and content_field:
                                    first = content_field[0]
                                    text = getattr(first, "text", None)
                                    if isinstance(text, str):
                                        prompt_text = text
                            if not prompt_text:
                                prompt_text = str(prompt_obj)
                            if prompt_text:
                                special_system_prompt = prompt_text
                                logger.info(
                                    "Applied MCP system prompt override from %s:%s (len=%d)",
                                    server,
                                    prompt_name,
                                    len(prompt_text),
                                )
                                break
                    except Exception:
                        logger.debug(
                            "MCP prompt retrieval failed; continuing without override",
                            exc_info=True,
                        )

            # Get or create session
            session = self.session_manager.get_or_create_session(
                session_id, user_email, special_system_prompt=special_system_prompt
            )

            # Add user message to session
            session.add_user_message(content)
            logger.info(
                f"Added user message to session {session_id}: {len(content)} chars"
            )

            # Update session in manager
            self.session_manager.update_session(session)

            # call log info, and log the first N=100 chars fo the message, list of seleced tools, agent_model, username, in 1 call
            logger.info(
                f"Session {session_id} - Model: {model}, Temperature: {temperature}, User: {user_email}, Message: {content[:100]}..., Selected Tool Map: {selected_tool_map}, Agent Mode: {agent_mode}, Special Prompt: {bool(special_system_prompt)}"
            )

            # Check if we need to use tools
            if selected_tool_map and self.mcp_manager and self.tool_orchestrator:
                # Use orchestrator for complete tool workflow
                (
                    final_response,
                    tool_results,
                ) = await self.tool_orchestrator.orchestrate_tool_workflow(
                    session=session,
                    session_id=session_id,
                    model=model,
                    temperature=temperature,
                    selected_tool_map=selected_tool_map,
                    user_email=user_email,
                    update_callback=update_callback,
                )

                # Add assistant response to session with tool metadata
                assistant_message = session.add_assistant_message(
                    final_response,
                    {
                        "model": model,
                        "temperature": temperature,
                        "tool_results": [
                            {
                                "id": r.tool_call_id,
                                "content": r.content,
                                "success": r.success,
                            }
                            for r in tool_results
                        ],
                    },
                )

            else:
                # Plain LLM call without tools
                final_response = await self.llm_manager.call_plain(
                    model, session.history, temperature
                )

                # Add assistant response to session
                assistant_message = session.add_assistant_message(
                    final_response,
                    {
                        "model": model,
                        "temperature": temperature,
                    },
                )

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
                logger.info(
                    f"Sending response callback for session {session_id}: {len(final_response)} chars"
                )
                try:
                    await update_callback(callback_message)
                    logger.info(
                        f"Response callback sent successfully for session {session_id}"
                    )
                except Exception as callback_error:
                    logger.error(
                        f"Error sending response callback: {callback_error}",
                        exc_info=True,
                    )

            # logger.info(f"Chat message processed successfully for session {session_id}")

            return {
                "type": "chat_response",
                "message": final_response,
                "model": model,
                "session_id": str(session_id),
            }

        except Exception as e:
            logger.error(
                f"Error handling chat message for session {session_id}: {e}",
                exc_info=True,
            )

            # Send error via callback if available
            if update_callback:
                await update_callback(
                    {
                        "type": "error",
                        "message": f"Error processing chat: {str(e)}",
                        "session_id": str(session_id),
                    }
                )

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
