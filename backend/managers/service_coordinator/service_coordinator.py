"""Service coordinator for orchestrating chat flows - Phase 1A."""

import logging
from typing import Any, Callable, Dict, Optional, Awaitable
from uuid import UUID

from managers.session.session_manager import SessionManager
# Common models will be imported by session manager
from managers.llm.llm_manager import LLMManager

logger = logging.getLogger(__name__)


class ServiceCoordinator:
    """Main coordinator that orchestrates managers for chat flows."""
    
    def __init__(self, session_manager: SessionManager, llm_manager: LLMManager):
        """Initialize service coordinator with required managers."""
        self.session_manager = session_manager
        self.llm_manager = llm_manager
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
        selected_tools: Optional[list] = None,
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
            
            # Call LLM
            llm_response = await self.llm_manager.call_plain(model, session.history, temperature)
            
            # Add assistant response to session
            assistant_message = session.add_assistant_message(llm_response, {
                "model": model,
                "temperature": temperature,
            })
            
            # Update session
            self.session_manager.update_session(session)
            
            # Send final response via callback
            if update_callback:
                callback_message = {
                    "type": "chat_response",
                    "message": llm_response,
                    "model": model,
                    "session_id": str(session_id),
                    "message_id": str(assistant_message.id),
                }
                logger.info(f"Sending response callback for session {session_id}: {len(llm_response)} chars")
                try:
                    await update_callback(callback_message)
                    logger.info(f"Response callback sent successfully for session {session_id}")
                except Exception as callback_error:
                    logger.error(f"Error sending response callback: {callback_error}", exc_info=True)
            
            # logger.info(f"Chat message processed successfully for session {session_id}")
            
            return {
                "type": "chat_response",
                "message": llm_response,
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