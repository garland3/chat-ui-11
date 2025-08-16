"""Chat service - core business logic for chat operations."""

import json
import logging
import os
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
        """
        self.llm = llm
        self.tool_manager = tool_manager
        self.connection = connection
        self.sessions: Dict[UUID, Session] = {}
        # Central config manager (optional during transition)
        self.config_manager = config_manager
        # Prompt provider abstraction
        self.prompt_provider: Optional[PromptProvider] = (
            PromptProvider(self.config_manager) if self.config_manager else None
        )
        # File manager (S3 abstraction)
        self.file_manager = file_manager

    # ---------------- File Handling Helpers ---------------- #
    async def _ingest_user_files(
        self,
        session: Session,
        user_email: Optional[str],
        files_map: Optional[Dict[str, str]],
        update_callback: Optional[UpdateCallback]
    ) -> None:
        """Upload user-provided base64 files (from WebSocket payload) to storage and update session context.

        Args:
            session: Current chat session
            user_email: Email for ownership / auth
            files_map: { filename: base64_content }
            update_callback: For emitting files_update event
        """
        if not files_map or not self.file_manager or not user_email:
            return
        try:
            session_files_ctx = session.context.setdefault("files", {})
            uploaded_refs: Dict[str, Dict[str, Any]] = {}
            for filename, b64 in files_map.items():
                try:
                    meta = await self.file_manager.upload_file(
                        user_email=user_email,
                        filename=filename,
                        content_base64=b64,
                        source_type="user",
                        tags={"source": "user"}
                    )
                    # Normalize minimal reference stored in session context
                    session_files_ctx[filename] = {
                        "key": meta.get("key"),
                        "content_type": meta.get("content_type"),
                        "size": meta.get("size"),
                        "source": "user",
                        "last_modified": meta.get("last_modified"),
                    }
                    uploaded_refs[filename] = meta
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Failed uploading user file {filename}: {e}")
            if uploaded_refs and update_callback:
                organized = self.file_manager.organize_files_metadata(uploaded_refs)
                await self._safe_notify(update_callback, {
                    "type": "intermediate_update",
                    "update_type": "files_update",
                    "data": organized
                })
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error ingesting user files: {e}", exc_info=True)

    async def _emit_files_update_from_context(
        self,
        session: Session,
        update_callback: Optional[UpdateCallback]
    ) -> None:
        """Emit a files_update event based on current session.context files."""
        if not self.file_manager or not update_callback:
            return
        try:
            # Build temp structure expected by organizer
            file_refs: Dict[str, Dict[str, Any]] = {}
            for fname, ref in session.context.get("files", {}).items():
                # Expand to shape similar to S3 metadata for organizer
                file_refs[fname] = {
                    "key": ref.get("key"),
                    "size": ref.get("size", 0),
                    "content_type": ref.get("content_type", "application/octet-stream"),
                    "last_modified": ref.get("last_modified"),
                    "tags": {"source": ref.get("source", "user")}
                }
            organized = self.file_manager.organize_files_metadata(file_refs)
            await self._safe_notify(update_callback, {
                "type": "intermediate_update",
                "update_type": "files_update",
                "data": organized
            })
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed emitting files update: {e}")

    async def _ingest_tool_files(
        self,
        session: Session,
        tool_result: ToolResult,
        user_email: Optional[str],
        update_callback: Optional[UpdateCallback]
    ) -> None:
        """Persist any files produced by a tool into storage and session context.

        Contract: ToolResult may include parallel arrays returned_file_names & returned_file_contents.
        We only upload when we have both name and matching content entry. If only names are present,
        we skip (tool may have already stored them directly via a future API).
        """
        if not self.file_manager or not user_email:
            return
        if not tool_result.returned_file_names:
            return
        # Safety: avoid huge ingestions; cap number of files per tool invocation
        MAX_FILES = 10
        names = tool_result.returned_file_names[:MAX_FILES]
        contents = tool_result.returned_file_contents[:MAX_FILES]
        if contents and len(contents) != len(names):
            # Mismatched lengths; log and proceed with min length
            logger.warning(
                "ToolResult file arrays length mismatch (names=%d, contents=%d) for tool_call_id=%s", 
                len(names), len(contents), tool_result.tool_call_id
            )
        pair_count = min(len(names), len(contents)) if contents else 0
        session_files_ctx = session.context.setdefault("files", {})
        uploaded_refs: Dict[str, Dict[str, Any]] = {}
        for idx, fname in enumerate(names):
            try:
                if idx < pair_count:
                    b64 = contents[idx]
                    meta = await self.file_manager.upload_file(
                        user_email=user_email,
                        filename=fname,
                        content_base64=b64,
                        source_type="tool",
                        tags={"source": "tool"}
                    )
                    session_files_ctx[fname] = {
                        "key": meta.get("key"),
                        "content_type": meta.get("content_type"),
                        "size": meta.get("size"),
                        "source": "tool",
                        "last_modified": meta.get("last_modified"),
                        "tool_call_id": tool_result.tool_call_id
                    }
                    uploaded_refs[fname] = meta
                else:
                    # Name without content – record reference placeholder only if not existing
                    session_files_ctx.setdefault(fname, {"source": "tool", "incomplete": True})
            except Exception as e:  # noqa: BLE001
                logger.error(f"Failed uploading tool-produced file {fname}: {e}")
        if uploaded_refs and update_callback:
            try:
                organized = self.file_manager.organize_files_metadata(uploaded_refs)
                await self._safe_notify(update_callback, {
                    "type": "intermediate_update",
                    "update_type": "files_update",
                    "data": organized
                })
            except Exception as e:  # noqa: BLE001
                logger.error(f"Failed emitting tool files update: {e}")
    
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
        Handle incoming chat message.
        
        Returns:
            Response dictionary to send to client
        """
        # Log all input arguments with content trimmed to 100 chars
        content_preview = content[:100] + "..." if len(content) > 100 else content
        # Sanitize kwargs: if files present (dict of filename->base64) log only filenames
        try:
            sanitized_kwargs = dict(kwargs)
            if "files" in sanitized_kwargs and isinstance(sanitized_kwargs["files"], dict):
                sanitized_kwargs["files"] = list(sanitized_kwargs["files"].keys())
        except Exception:  # noqa: BLE001 - defensive, never block on logging
            sanitized_kwargs = {k: ("<error sanitizing>") for k in kwargs.keys()}
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
        
        # (Deprecated) inline notify previously used deeper in call stack. Logic now centralized in _safe_notify.
        # Ingest any user-uploaded files (base64) before LLM processing
        await self._ingest_user_files(
            session=session,
            user_email=user_email,
            files_map=kwargs.get("files"),
            update_callback=update_callback
        )
    # Removed persistent files manifest insertion (now using only ephemeral injection per invocation)

        try:
            # Get conversation history for LLM
            messages = session.history.get_messages_for_llm()
            # Always append an ephemeral files manifest (not stored) if files exist
            files_ctx = session.context.get("files", {})
            if files_ctx:
                file_list = "\n".join(f"- {name}" for name in sorted(files_ctx.keys()))
                manifest = (
                    "Available session files:\n"
                    f"{file_list}\n\n"
                    "(You can ask to open or analyze any of these by name. "
                    "Large contents are not fully in this prompt unless user or tools provided excerpts.)"
                )
                messages.append({"role": "system", "content": manifest})
            
            # Determine which LLM method to use
            if agent_mode:
                response = await self._handle_agent_mode(
                    session, model, messages, selected_tools, selected_data_sources, kwargs.get("agent_max_steps", 10)
                )
            elif selected_tools and not only_rag:
                response = await self._handle_tools_mode(
                    session=session,
                    model=model,
                    messages=messages,
                    selected_tools=selected_tools,
                    data_sources=selected_data_sources,
                    user_email=user_email,
                    tool_choice_required=tool_choice_required,
                    update_callback=update_callback
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
    tool_choice_required: bool,
    update_callback: Optional[UpdateCallback] = None
    ) -> Dict[str, Any]:
        """Handle LLM call with tools (and optionally RAG)."""
        try:
            if not self.tool_manager:
                raise ValidationError("Tool manager not configured")
            
            # Get tool schemas
            tools_schema = self.tool_manager.get_tools_schema(selected_tools)
            tool_choice = "required" if tool_choice_required else "auto"
            logger.info(f"Got {len(tools_schema)} tool schemas for selected tools: {selected_tools}, tool_choice: {tool_choice}")
        except Exception as e:
            logger.error(f"Error getting tools schema: {e}", exc_info=True)
            raise ValidationError(f"Failed to get tools schema: {str(e)}")
        
        # Call LLM with tools
        try:
            if data_sources and user_email:
                llm_response = await self.llm.call_with_rag_and_tools(
                    model, messages, data_sources, tools_schema, user_email, tool_choice
                )
                logger.info(f"LLM response received with RAG and tools for user {user_email}, has_tool_calls: {llm_response.has_tool_calls()}")
            else:
                llm_response = await self.llm.call_with_tools(
                    model, messages, tools_schema, tool_choice
                )
                logger.info(f"LLM response received with tools only, has_tool_calls: {llm_response.has_tool_calls()}")
        except Exception as e:
            logger.error(f"Error calling LLM with tools: {e}", exc_info=True)
            raise ValidationError(f"Failed to call LLM with tools: {str(e)}")
        
        # Immediately stream initial content if available
        if llm_response.content and update_callback:
            await self._safe_notify(update_callback, {
                "type": "chat_response",
                "message": llm_response.content,
                "has_pending_tools": llm_response.has_tool_calls()
            })
        
        # Process tool calls if present
        if llm_response.has_tool_calls():
            final_response = await self._handle_tools_with_updates(
                llm_response=llm_response,
                messages=messages,
                model=model,
                session=session,
                update_callback=update_callback
            )
            
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
            final_response = llm_response.content
            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=final_response
            )
            session.history.add_message(assistant_message)
            
            # Send completion notification (no tools path) via callback
            if update_callback:
                await self._safe_notify(update_callback, {"type": "response_complete"})
            
            return {
                "type": MessageType.CHAT_RESPONSE.value,
                "message": final_response
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
    
    async def _handle_tools_with_updates(
        self,
        llm_response,
        messages: List[Dict],
        model: str,
        session: Session,
    update_callback: Optional[UpdateCallback]
    ):
        """Handle tool execution with streaming updates."""
        # Add the assistant message with tool calls to conversation
        messages.append({
            "role": "assistant",
            "content": llm_response.content,
            "tool_calls": llm_response.tool_calls
        })
        
        # Execute tools with real-time updates
        tool_results = []
        for tool_call in llm_response.tool_calls:
            # Always parse / normalize arguments first (outside update_callback branch)
            raw_args = getattr(tool_call.function, "arguments", {})
            if isinstance(raw_args, dict):
                parsed_args = raw_args
            else:
                if raw_args is None or raw_args == "":
                    # Empty string or None => no arguments
                    parsed_args = {}
                else:
                    try:
                        parsed_args = json.loads(raw_args)
                        if not isinstance(parsed_args, dict):
                            parsed_args = {"_value": parsed_args}
                    except Exception:
                        logger.warning(
                            "Failed to parse tool arguments as JSON for %s, using empty dict. Raw: %r",
                            getattr(tool_call.function, "name", "<unknown>"), raw_args
                        )
                        parsed_args = {}
            # Send tool start notification
            if update_callback:
                # Derive server name (everything before last underscore) for display context
                parts = tool_call.function.name.split("_")
                server_name = "_".join(parts[:-1]) if len(parts) > 1 else "unknown"
                # For canvas tool, also emit a canvas_content precursor (content may arrive after execution if needed)
                payload = {
                    "type": "tool_start",
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_call.function.name,
                    "server_name": server_name,
                    "arguments": parsed_args
                }
                await self._safe_notify(update_callback, payload)
            
            try:
                # Convert to ToolCall object and execute
                tool_call_obj = ToolCall(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments=parsed_args
                )
                
                result = await self.tool_manager.execute_tool(
                    tool_call_obj,
                    context={"session_id": session.id, "user_email": session.user_email}
                )
                tool_results.append(result)

                # Ingest any files produced by this tool
                try:
                    await self._ingest_tool_files(
                        session=session,
                        tool_result=result,
                        user_email=session.user_email,
                        update_callback=update_callback
                    )
                except Exception as ingest_err:  # noqa: BLE001
                    logger.error(f"Error ingesting tool files for {tool_call.function.name}: {ingest_err}")
                
                # Send tool completion notification
                if update_callback:
                    complete_payload = {
                        "type": "tool_complete",
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.function.name,
                        "success": result.success,
                        "result": result.content
                    }
                    # If this is the canvas tool, also push a canvas_content event for the UI split
                    if tool_call.function.name == "canvas_canvas":
                        try:
                            # Try to extract original content argument for canvas display
                            content_arg = parsed_args.get("content") if isinstance(parsed_args, dict) else None
                        except Exception:
                            content_arg = None
                        if content_arg:
                            await self._safe_notify(update_callback, {
                                "type": "canvas_content",
                                "content": content_arg
                            })
                    await self._safe_notify(update_callback, complete_payload)
                
            except Exception as e:
                logger.error(f"Error executing tool {tool_call.function.name}: {e}")
                # Send tool error notification
                if update_callback:
                    await self._safe_notify(update_callback, {
                        "type": "tool_error",
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.function.name,
                        "error": str(e)
                    })
                raise
        
        # Add tool results to messages
        for result in tool_results:
            messages.append({
                "role": "tool",
                "content": result.content,
                "tool_call_id": result.tool_call_id
            })
        
        # Check if we need final synthesis
        canvas_tool_calls = [tc for tc in llm_response.tool_calls if tc.function.name == "canvas_canvas"]
        has_only_canvas_tools = len(canvas_tool_calls) == len(llm_response.tool_calls)
        
        if has_only_canvas_tools:
            # Canvas tools don't need follow-up, just return the original content
            final_response = llm_response.content or "Content displayed in canvas."
        else:
            # Rebuild ephemeral manifest if new files were added by tools before synthesis
            if session.context.get("files"):
                file_list = "\n".join(f"- {name}" for name in sorted(session.context["files"].keys()))
                manifest = (
                    "Available session files (updated after tool runs):\n"
                    f"{file_list}\n\n"
                    "(You can ask to open or analyze any of these by name.)"
                )
                messages.append({"role": "system", "content": manifest})
            # Get final synthesis from LLM using dedicated synthesis prompt
            final_response = await self._synthesize_tool_results(model, messages, update_callback)
        
        # Send completion notification
        if update_callback:
            await self._safe_notify(update_callback, {"type": "response_complete"})
        
        return final_response

    async def _synthesize_tool_results(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        update_callback: Optional[UpdateCallback]
    ) -> str:
        """Prepare augmented messages with synthesis prompt and obtain final answer."""
        # Extract latest user question (walk backwards)
        user_question = ""
        for m in reversed(messages):
            if m.get("role") == "user" and m.get("content"):
                user_question = m["content"]
                break
        prompt_text = None
        if self.prompt_provider:
            prompt_text = self.prompt_provider.get_tool_synthesis_prompt(user_question or "the user's last request")

        synthesis_messages = list(messages)
        if prompt_text:
            synthesis_messages.append({
                "role": "system",
                "content": prompt_text
            })
        else:
            logger.info("Proceeding without dedicated tool synthesis prompt (fallback)")

        final_response = await self.llm.call_plain(model, synthesis_messages)

        if final_response and final_response.strip() and update_callback:
            await self._safe_notify(update_callback, {
                "type": "tool_synthesis",
                "message": final_response
            })
        return final_response

    async def _safe_notify(self, cb: UpdateCallback, message: Dict[str, Any]) -> None:
        """Invoke callback safely, logging but suppressing exceptions."""
        try:
            await cb(message)
        except Exception as e:
            logger.warning(f"Update callback failed: {e}")
    
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
        except Exception as e:  # noqa: BLE001
            logger.error(f"Download failed for {filename}: {e}")
            return {
                "type": MessageType.FILE_DOWNLOAD.value,
                "filename": filename,
                "error": str(e)
            }
    
    def get_session(self, session_id: UUID) -> Optional[Session]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def end_session(self, session_id: UUID) -> None:
        """End a session."""
        if session_id in self.sessions:
            self.sessions[session_id].active = False
            logger.info(f"Ended session {session_id}")
