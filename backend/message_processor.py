"""
Message processing module containing the core chat message handling logic.

This module contains the MessageProcessor class which handles the most critical
function in the codebase: processing incoming chat messages through the complete
pipeline including RAG, tool validation, LLM calls, and callback coordination.
"""

import logging
from typing import Any, Dict, Optional

from llm_processor import LLMProcessor, ProcessingContext
from agent_executor import AgentExecutor, AgentContext
from llm_caller import LLMCaller
from tool_executor import ToolExecutor
from utils import validate_selected_tools

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
        self.processor = LLMProcessor(session)
        
        # Create agent executor components
        llm_caller = LLMCaller()
        tool_executor = ToolExecutor(session.mcp_manager)
        self.agent_executor = AgentExecutor(llm_caller, tool_executor)
        
    async def handle_agent_mode_message(self, message: Dict[str, Any]) -> None:
        """
        Agent mode with clean loop-based execution - no recursion, no artificial prompting.
        
        Delegates to AgentExecutor which uses a loop where the LLM's response
        becomes the input for the next step naturally.
        """
        try:
            logger.info(f"Starting agent mode for user {self.session.user_email}")
            
            # Update session state from message first
            self._update_session_state(message)
            
            # Build processing context
            context = self._build_processing_context(message, agent_mode=True)
            
            # Create agent context
            from config import config_manager
            app_settings = config_manager.app_settings
            
            # Validate tools for agent mode
            validated_servers = await validate_selected_tools(
                context.selected_tools, 
                context.user_email, 
                self.session.mcp_manager
            )
            
            # Get tools data
            tools_data = self.session.mcp_manager.get_tools_for_servers(validated_servers)
            
            # Filter to selected tools if specified
            if context.selected_tools:
                tools_schema = []
                tool_mapping = {}
                selected_tools_set = set(context.selected_tools)
                
                for tool_schema in tools_data["tools"]:
                    tool_function_name = tool_schema["function"]["name"]
                    if tool_function_name in selected_tools_set:
                        tools_schema.append(tool_schema)
                        if tool_function_name in tools_data["mapping"]:
                            tool_mapping[tool_function_name] = tools_data["mapping"][tool_function_name]
            else:
                tools_schema = tools_data["tools"]
                tool_mapping = tools_data["mapping"]
            
            agent_context = AgentContext(
                user_email=context.user_email,
                model_name=context.model_name,
                max_steps=app_settings.agent_max_steps,
                tools_schema=tools_schema,
                tool_mapping=tool_mapping,
                session=context.session,
                messages=context.messages.copy()
            )
            
            # Execute using loop-based AgentExecutor
            agent_result = await self.agent_executor.execute_agent_loop(
                context.content,
                agent_context
            )
            
            # Send final response
            await self._send_final_agent_response(
                agent_result.final_response, 
                agent_result.steps_taken, 
                app_settings.agent_max_steps
            )
            
        except Exception as exc:
            logger.error("Error in agent mode for %s: %s", self.session.user_email, exc, exc_info=True)
            await self.session._trigger_callbacks("message_error", error=exc)
            try:
                await self.session.send_error(f"Error in agent mode: {exc}")
            except Exception as send_exc:
                logger.error("Failed to send error message for agent mode to user %s: %s", self.session.user_email, send_exc)


    async def _send_final_agent_response(self, response: str, steps_taken: int, max_steps: int) -> None:
        """Send final agent response with step summary."""
        payload = {
            "type": "agent_final_response",
            "message": response,
            "steps_taken": steps_taken,
            "max_steps": max_steps,
            "user": self.session.user_email
        }
        
        await self.session._trigger_callbacks("before_response_send", payload=payload)
        await self.session.send_json(payload)
        await self.session._trigger_callbacks("after_response_send", payload=payload)
        logger.info("Agent final response sent to user %s after %d steps", self.session.user_email, steps_taken)

    async def handle_chat_message(self, message: Dict[str, Any], agent_mode: bool = False) -> Optional[str]:
        """
        Simplified chat message handler using the new modular architecture.
        
        Routes to appropriate processor based on message parameters and modes.
        Much cleaner than the old 200+ line monolithic implementation.
        
        Args:
            message: The incoming chat message with content, model, tools, etc.
            agent_mode: Whether this is being called from agent mode
        """
        try:
            await self.session._trigger_callbacks("before_message_processing", message=message)

            # Update session state from message
            self._update_session_state(message)
            
            # Log message details
            self._log_message_details(message)

            # Validate required fields
            content = message.get("content", "")
            if not content or not self.session.model_name:
                logger.error(f"Message validation failed for user {self.session.user_email}: content='{content}', model='{self.session.model_name}'")
                raise ValueError(f"Message content and model name are required. Content: {bool(content)}, Model: {bool(self.session.model_name)}")

            await self.session._trigger_callbacks("before_user_message_added", content=content)

            # Apply custom system prompts if needed
            await self._apply_custom_system_prompts()
            
            # Add user message to conversation BEFORE building context
            content = message.get("content", "")
            enhanced_content = self._build_content_with_files(content)
            self.session.messages.append({"role": "user", "content": enhanced_content})
            await self.session._trigger_callbacks("after_user_message_added", user_message={"role": "user", "content": enhanced_content})

            # Build processing context AFTER adding user message
            context = self._build_processing_context(message, agent_mode)

            # Process the message using new modular architecture
            result = await self.processor.process_message(context)
            
            # Add assistant response to conversation
            assistant_message = {"role": "assistant", "content": result.response}
            self.session.messages.append(assistant_message)
            await self.session._trigger_callbacks("after_assistant_message_added", assistant_message=assistant_message)

            # In agent mode, return response instead of sending to WebSocket
            if agent_mode:
                return result.response

            # Send response to client
            payload = {
                "type": "chat_response",
                "message": result.response,
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
            # Only try to send error if we're not in agent mode and connection is still open
            if not agent_mode:
                try:
                    await self.session.send_error(f"Error processing message: {exc}")
                except Exception as send_exc:
                    logger.error("Failed to send error message for chat processing to user %s: %s", self.session.user_email, send_exc)


    def _build_content_with_files(self, content: str) -> str:
        """Append available files to user prompt if any exist, filtered by file policy"""
        try:
            if not self.session.uploaded_files:
                return content

            # Import file filtering functionality
            from file_config import file_policy

            file_entries = []
            for filename in self.session.uploaded_files.keys():
                try:
                    # Get file metadata from session.file_references
                    file_metadata = self.session.file_references.get(filename, {})
                    file_size = file_metadata.get("size", 0)
                    category = file_policy.get_file_category(filename)
                    size_kb = file_size / 1024
                    
                    # Determine if file should be exposed to LLM based on metadata
                    should_expose = file_policy.should_expose_to_llm(filename, file_size)
                    
                    if should_expose:
                        file_entries.append(f"- {filename} ({category}, {size_kb:.1f}KB)")
                    else:
                        file_entries.append(f"- {filename} ({category}, {size_kb:.1f}KB) [tool-accessible only]")
                        
                except Exception as e:
                    logger.warning(f"Could not analyze file {filename}: {e}")
                    file_entries.append(f"- {filename} [analysis failed]")

            file_list = "\n".join(file_entries)
            return f"{content}\n\nUploaded files available:\n{file_list}\n\nNote: Files marked as [tool-accessible only] can be processed by tools but their content is not directly visible to me. Use the appropriate tools to analyze these files."
        except Exception as exc:
            logger.warning(f"Failed to build content with files list: {exc}")
            return content
    
    async def _get_custom_system_prompt(self) -> str:
        """Get custom system prompt from selected MCP servers that provide prompts."""
        if not self.session.selected_prompts:
            logger.debug(f"No custom prompts selected for user {self.session.user_email}")
            return None
            
        # Parse the selected prompts (format: "server_promptname")
        prompt_servers = []
        selected_prompt_tools = []
        for prompt_name in self.session.selected_prompts:
            logger.debug(f"Checking prompt '{prompt_name}' for user {self.session.user_email}")
            if prompt_name.startswith("prompts_"):
                prompt_servers.append("prompts")
                selected_prompt_tools.append(prompt_name)
                logger.info(f"Found custom prompt: {prompt_name} for user {self.session.user_email}")
        
        if not prompt_servers:
            logger.debug(f"No prompts server prompts found for user {self.session.user_email}")
            return None
        
        logger.info(f"Custom prompts detected for user {self.session.user_email}: {selected_prompt_tools}")
        
        try:
            # Get available prompts from the prompts server
            available_prompts = self.session.mcp_manager.get_available_prompts_for_servers(prompt_servers)
            
            # Only apply the specifically selected prompts
            system_prompts = []
            applied_prompts = []
            
            for selected_prompt in selected_prompt_tools:
                # Extract the prompt name (remove "prompts_" prefix)
                prompt_name = selected_prompt.replace("prompts_", "")
                
                # Check if this prompt is available
                for prompt_info in available_prompts.values():
                    if prompt_info['name'] == prompt_name:
                        try:
                            logger.info(f"Applying selected custom prompt '{prompt_info['name']}' for user {self.session.user_email}")
                            # Get the actual prompt content
                            prompt_result = await self.session.mcp_manager.get_prompt(
                                prompt_info['server'], 
                                prompt_info['name']
                            )
                            if prompt_result and hasattr(prompt_result, 'messages') and prompt_result.messages:
                                # Extract the system message content from user messages
                                for message in prompt_result.messages:
                                    if message.role == "user" and "System:" in message.content.text:
                                        # Extract the system prompt part
                                        content = message.content.text
                                        if "System:" in content and "User:" in content:
                                            system_part = content.split("System:")[1].split("User:")[0].strip()
                                            system_prompts.append(system_part)
                                            applied_prompts.append(prompt_info['name'])
                                            logger.info(f"Successfully loaded custom prompt '{prompt_info['name']}' ({len(system_part)} chars)")
                                            break
                        except Exception as e:
                            logger.warning(f"Could not retrieve prompt {prompt_info['name']}: {e}")
                        break  # Found the prompt, no need to continue looking
            
            if system_prompts:
                # Combine multiple system prompts if present
                combined_prompt = "\n\n".join(system_prompts)
                logger.info(f"Using custom system prompt from {len(system_prompts)} prompt(s): {applied_prompts}")
                return combined_prompt
                
        except Exception as e:
            logger.error(f"Error retrieving custom system prompt: {e}")
            
        return None
    
    def _update_session_state(self, message: Dict[str, Any]) -> None:
        """Update session state from incoming message."""
        prev_model = self.session.model_name
        self.session.model_name = message.get("model", "")
        self.session.selected_tools = message.get("selected_tools", [])
        self.session.selected_prompts = message.get("selected_prompts", [])
        self.session.selected_data_sources = message.get("selected_data_sources", [])
        self.session.only_rag = message.get("only_rag", True)
        self.session.tool_choice_required = message.get("tool_choice_required", False)
        
        logger.debug(f"Session state update for {self.session.user_email}: model '{prev_model}' -> '{self.session.model_name}'")
        
        # Update uploaded files (preserve existing tool-generated files)
        new_files = message.get("files", {})
        if new_files:
            # Only update if files are actually provided to avoid clearing existing files
            for filename, file_data in new_files.items():
                self.session.uploaded_files[filename] = file_data
    
    def _log_message_details(self, message: Dict[str, Any]) -> None:
        """Log incoming message details for debugging."""
        content = message.get("content", "")
        logger.info(
            "------------\n"
            f"Received chat message from {self.session.user_email}: \n"
            f"\tcontent='{content[:50]}...', model='{self.session.model_name}', \n"
            f"\ttools={self.session.selected_tools}, \n"
            f"\tprompts={self.session.selected_prompts}, \n"
            f"\tdata_sources={self.session.selected_data_sources}, \n"
            f"\tonly_rag={self.session.only_rag}, uploaded_files={list(self.session.uploaded_files.keys())}\n"
        )
        
        # Log file upload details for debugging
        if self.session.uploaded_files:
            logger.info(f"User {self.session.user_email} has {len(self.session.uploaded_files)} files:")
            for filename, s3_key in self.session.uploaded_files.items():
                file_metadata = self.session.file_references.get(filename, {})
                file_size = file_metadata.get("size", 0)
                logger.info(f"  - {filename} (size: {file_size} bytes, S3: {s3_key})")
                
            # Show potential file-related tools that could be used
            available_file_tools = [tool for tool in self.session.selected_tools 
                                   if any(keyword in tool.lower() 
                                         for keyword in ['pdf', 'file', 'document', 'analyze'])]
            if available_file_tools:
                logger.info(f"Available file processing tools: {available_file_tools}")
            else:
                logger.warning(f"No file processing tools selected despite file upload")
        else:
            logger.debug("No files uploaded for this user")
    
    def _build_processing_context(self, message: Dict[str, Any], agent_mode: bool = False) -> ProcessingContext:
        """Build processing context from message and session state."""
        content = message.get("content", "")
        
        # Debug: Log exactly what content is being processed
        logger.info(f"Processing context for user {self.session.user_email}:")
        logger.info(f"  Original content: '{content[:100]}{'...' if len(content) > 100 else ''}'")
        logger.info(f"  Messages in context: {len(self.session.messages)}")
        
        return ProcessingContext(
            user_email=self.session.user_email,
            model_name=self.session.model_name,
            content=content,  # Use original content since enhanced content is now in messages
            messages=self.session.messages.copy(),
            selected_tools=self.session.selected_tools,
            selected_data_sources=self.session.selected_data_sources,
            only_rag=self.session.only_rag,
            tool_choice_required=self.session.tool_choice_required,
            session=self.session,
            agent_mode=agent_mode
        )
    
    async def _apply_custom_system_prompts(self) -> None:
        """Apply custom system prompts if this is the first user message."""
        custom_system_prompt = await self._get_custom_system_prompt()
        user_messages_count = len([msg for msg in self.session.messages if msg["role"] == "user"])
        
        if custom_system_prompt and user_messages_count == 0:
            # Replace the default system message with custom system prompt
            if self.session.messages and self.session.messages[0]["role"] == "system":
                self.session.messages[0]["content"] = custom_system_prompt
                logger.info(f"Replaced default system prompt with custom prompt for user {self.session.user_email}")
            else:
                # Add custom system prompt as the first message
                system_message = {"role": "system", "content": custom_system_prompt}
                self.session.messages.insert(0, system_message)
                logger.info(f"Added custom system prompt for user {self.session.user_email}")
            
            # Extract prompt names from selected prompts for detailed logging
            active_prompts = [prompt.replace("prompts_", "") for prompt in self.session.selected_prompts if prompt.startswith("prompts_")]
            logger.info(f"Applied custom system prompt for user {self.session.user_email} - Active prompts: {active_prompts}")
