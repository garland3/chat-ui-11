"""Chat service - core business logic for chat operations."""

import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable
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
from modules.config import ConfigManager
from modules.prompts.prompt_provider import PromptProvider
from interfaces.tools import ToolManagerProtocol
from interfaces.transport import ChatConnectionProtocol

# Import utilities
from .utilities import tool_utils, file_utils, notification_utils, error_utils

logger = logging.getLogger(__name__)

# Type hint for the update callback
UpdateCallback = Callable[[Dict[str, Any]], Awaitable[None]]


class ChatService:
    """
    Core chat service that orchestrates chat operations.
    Transport-agnostic, testable business logic.
    """
    
    def __init__(
        self,
        llm: LLMProtocol,
        tool_manager: Optional[ToolManagerProtocol] = None,
        connection: Optional[ChatConnectionProtocol] = None,
        config_manager: Optional[ConfigManager] = None,
        file_manager: Optional[Any] = None,
    ):
        """
        Initialize chat service with dependencies.
        
        Args:
            llm: LLM protocol implementation
            tool_manager: Optional tool manager
            connection: Optional connection for sending updates
            config_manager: Configuration manager
            file_manager: File manager for S3 operations
        """
        self.llm = llm
        self.tool_manager = tool_manager
        self.connection = connection
        self.sessions: Dict[UUID, Session] = {}
        self.config_manager = config_manager
        self.prompt_provider: Optional[PromptProvider] = (
            PromptProvider(self.config_manager) if self.config_manager else None
        )
        self.file_manager = file_manager

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
        update_callback: Optional[UpdateCallback] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Handle incoming chat message using utilities for clean separation.
        
        Returns:
            Response dictionary to send to client
        """
        # Log input arguments with content trimmed
        content_preview = content[:100] + "..." if len(content) > 100 else content
        sanitized_kwargs = error_utils.sanitize_kwargs_for_logging(kwargs)
        
        logger.info(
            f"handle_chat_message called - session_id: {session_id}, "
            f"content: '{content_preview}', model: {model}, "
            f"selected_tools: {selected_tools}, selected_data_sources: {selected_data_sources}, "
            f"only_rag: {only_rag}, tool_choice_required: {tool_choice_required}, "
            f"user_email: {user_email}, agent_mode: {agent_mode}, "
            f"kwargs: {sanitized_kwargs}"
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
        
        # Handle user file ingestion using utilities
        session.context = await file_utils.handle_session_files(
            session_context=session.context,
            user_email=user_email,
            files_map=kwargs.get("files"),
            file_manager=self.file_manager,
            update_callback=update_callback
        )

        try:
            # Get conversation history and add files manifest
            messages = session.history.get_messages_for_llm()
            files_manifest = file_utils.build_files_manifest(session.context)
            if files_manifest:
                messages.append(files_manifest)
            
            # Route to appropriate execution mode
            if agent_mode:
                response = await self._handle_agent_mode(
                    session, model, messages, selected_tools, selected_data_sources, kwargs.get("agent_max_steps", 10)
                )
            elif selected_tools and not only_rag:
                response = await self._handle_tools_mode_with_utilities(
                    session, model, messages, selected_tools, selected_data_sources,
                    user_email, tool_choice_required, update_callback
                )
            elif selected_data_sources:
                response = await self._handle_rag_mode(
                    session, model, messages, selected_data_sources, user_email
                )
            else:
                response = await self._handle_plain_mode(session, model, messages)
            
            return response
            
        except Exception as e:
            return error_utils.handle_chat_message_error(e, "chat message handling")

    async def _handle_plain_mode(
        self,
        session: Session,
        model: str,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Handle plain LLM call without tools or RAG."""
        response_content = await self.llm.call_plain(model, messages)
        
        # Add assistant message to history
        assistant_message = Message(
            role=MessageRole.ASSISTANT,
            content=response_content
        )
        session.history.add_message(assistant_message)
        
        return notification_utils.create_chat_response(response_content)

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
        
        return notification_utils.create_chat_response(response_content)

    async def _handle_tools_mode_with_utilities(
        self,
        session: Session,
        model: str,
        messages: List[Dict[str, str]],
        selected_tools: List[str],
        data_sources: Optional[List[str]],
        user_email: Optional[str],
        tool_choice_required: bool,
        update_callback: Optional[UpdateCallback] = None
    ) -> Dict[str, Any]:
        """Handle LLM call with tools using utilities - clean and concise."""
        # Get tool schemas safely
        tools_schema = await error_utils.safe_get_tools_schema(self.tool_manager, selected_tools)
        tool_choice = "required" if tool_choice_required else "auto"

        # Call LLM with tools safely
        llm_response = await error_utils.safe_call_llm_with_tools(
            llm_caller=self.llm,
            model=model,
            messages=messages,
            tools_schema=tools_schema,
            data_sources=data_sources,
            user_email=user_email,
            tool_choice=tool_choice
        )

        # Stream initial content if available
        if llm_response.content and update_callback:
            await notification_utils.notify_chat_response(
                message=llm_response.content,
                has_pending_tools=llm_response.has_tool_calls(),
                update_callback=update_callback
            )

        # Handle tool calls if present
        if llm_response.has_tool_calls():
            final_response = await tool_utils.execute_tools_workflow(
                llm_response=llm_response,
                messages=messages,
                model=model,
                session_context=self._build_session_context(session),
                tool_manager=self.tool_manager,
                llm_caller=self.llm,
                prompt_provider=self.prompt_provider,
                update_callback=update_callback
            )
            
            # Update session context with any tool artifacts
            await self._update_session_from_tool_results(session, llm_response, update_callback)
            metadata = {"tools_used": selected_tools}

            # Signal completion to UI (prevents lingering spinner when only tool_synthesis was sent)
            await notification_utils.notify_response_complete(update_callback)
        else:
            final_response = llm_response.content
            metadata = {}
            await notification_utils.notify_response_complete(update_callback)

        # Add to history
        assistant_message = Message(
            role=MessageRole.ASSISTANT,
            content=final_response,
            metadata=metadata
        )
        session.history.add_message(assistant_message)

        return notification_utils.create_chat_response(final_response)

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
            await notification_utils.notify_agent_update(
                update_type="agent_start",
                connection=self.connection,
                max_steps=max_steps
            )
        
        steps = 0
        final_response = None
        
        while steps < max_steps:
            steps += 1
            
            # Send step update
            if self.connection:
                await notification_utils.notify_agent_update(
                    update_type="agent_turn_start",
                    connection=self.connection,
                    step=steps
                )
            
            # Get tool schemas if available
            tools_schema = []
            if selected_tools and self.tool_manager:
                tools_schema = await error_utils.safe_get_tools_schema(self.tool_manager, selected_tools)
            
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
                # Execute tools using utilities
                tool_results = []
                session_context = self._build_session_context(session)
                
                for tool_call in llm_response.tool_calls:
                    result = await tool_utils.execute_single_tool(
                        tool_call=tool_call,
                        session_context=session_context,
                        tool_manager=self.tool_manager,
                        update_callback=None  # No notifications in agent mode
                    )
                    tool_results.append(result)
                
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
                        await notification_utils.notify_agent_update(
                            update_type="agent_tool_call",
                            connection=self.connection,
                            tool_name=tool_call.get("function", {}).get("name"),
                            result=result.content
                        )
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
            await notification_utils.notify_agent_update(
                update_type="agent_completion",
                connection=self.connection,
                steps=steps
            )
        
        return notification_utils.create_chat_response(final_response)

    async def handle_download_file(
        self,
        session_id: UUID,
        filename: str,
        user_email: Optional[str]
    ) -> Dict[str, Any]:
        """Download a file by original filename (within session context)."""
        session = self.sessions.get(session_id)
        if not session or not self.file_manager or not user_email:
            return {
                "type": MessageType.FILE_DOWNLOAD.value,
                "filename": filename,
                "error": "Session or file manager not available"
            }
        ref = session.context.get("files", {}).get(filename)
        if not ref:
            return {
                "type": MessageType.FILE_DOWNLOAD.value,
                "filename": filename,
                "error": "File not found in session"
            }
        try:
            content_b64 = await self.file_manager.get_file_content(
                user_email=user_email,
                filename=filename,
                s3_key=ref.get("key")
            )
            if not content_b64:
                return {
                    "type": MessageType.FILE_DOWNLOAD.value,
                    "filename": filename,
                    "error": "Unable to retrieve file content"
                }
            return {
                "type": MessageType.FILE_DOWNLOAD.value,
                "filename": filename,
                "content_base64": content_b64
            }
        except Exception as e:
            logger.error(f"Download failed for {filename}: {e}")
            return {
                "type": MessageType.FILE_DOWNLOAD.value,
                "filename": filename,
                "error": str(e)
            }
    
    def _build_session_context(self, session: Session) -> Dict[str, Any]:
        """Build session context for utilities."""
        return {
            "session_id": session.id,
            "user_email": session.user_email,
            "files": session.context.get("files", {}),
            **session.context
        }

    async def _update_session_from_tool_results(
        self,
        session: Session,
        llm_response: LLMResponse,
        update_callback: Optional[UpdateCallback]
    ) -> None:
        """Update session context from tool execution results."""
        # This would be called after tool execution to update session state
        # The tool_utils.execute_tools_workflow handles the actual file processing
        # This is a placeholder for any additional session updates needed
        pass

    def get_session(self, session_id: UUID) -> Optional[Session]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def end_session(self, session_id: UUID) -> None:
        """End a session."""
        if session_id in self.sessions:
            self.sessions[session_id].active = False
            logger.info(f"Ended session {session_id}")