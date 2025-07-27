"""
Message processing module containing the core chat message handling logic.

This module contains the MessageProcessor class which handles the most critical
function in the codebase: processing incoming chat messages through the complete
pipeline including RAG, tool validation, LLM calls, and callback coordination.
"""

import logging
import os
from typing import Any, Dict, Optional

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
        
    async def handle_agent_mode_message(self, message: Dict[str, Any]) -> None:
        """
        Agent mode wrapper around handle_chat_message with step loop.
        
        Feeds LLM responses back as input until completion or max steps reached.
        Uses minimal changes approach to reuse all existing logic.
        """
        try:
            from config import config_manager
            app_settings = config_manager.app_settings
            max_steps = min(message.get("agent_max_steps", 5), app_settings.agent_max_steps)
            step_count = 0
            
            logger.info(
                "Starting agent mode for user %s with max %d steps",
                self.session.user_email,
                max_steps
            )
            
            # Initial user message
            current_message = message.copy()
            
            while step_count < max_steps:
                step_count += 1
                
                # Send step update to frontend
                await self._send_agent_step_update(step_count, max_steps, "processing")
                
                # Call existing handle_chat_message but capture response
                response = await self.handle_chat_message(current_message, agent_mode=True)
                
                # Check if agent used completion tool (detected by tool call)
                if self._agent_used_completion_tool(response):
                    logger.info("Agent used completion tool after %d steps", step_count)
                    await self._send_final_agent_response(response, step_count, max_steps)
                    break
                
                if not response:
                    logger.warning("Agent step %d returned empty response", step_count)
                    break
                
                # Check if LLM wants to continue or is done
                if self._is_agent_complete(response):
                    logger.info("Agent completed after %d steps", step_count)
                    await self._send_final_agent_response(response, step_count, max_steps)
                    break
                    
                # Check if we're at max steps
                if step_count >= max_steps:
                    logger.info("Agent reached max steps (%d)", max_steps)
                    await self._send_final_agent_response(
                        f"{response}\n\n[Agent completed after reaching maximum {max_steps} steps]", 
                        step_count, 
                        max_steps
                    )
                    break
                
                # Prepare next iteration - feed response back as "user" input
                current_message = {
                    "content": f"Continue reasoning from your previous response. Previous response: {response}",
                    "model": current_message["model"],
                    "selected_tools": current_message.get("selected_tools", []),
                    "selected_data_sources": current_message.get("selected_data_sources", []),
                    "only_rag": current_message.get("only_rag", True)
                }
                
                logger.info("Agent step %d completed, continuing to step %d", step_count, step_count + 1)
                
        except Exception as exc:
            logger.error("Error in agent mode for %s: %s", self.session.user_email, exc, exc_info=True)
            await self.session._trigger_callbacks("message_error", error=exc)
            try:
                await self.session.send_error(f"Error in agent mode: {exc}")
            except Exception as send_exc:
                logger.error("Failed to send error message for agent mode to user %s: %s", self.session.user_email, send_exc)

    def _agent_used_completion_tool(self, response: str) -> bool:
        """Check if agent used the all_work_is_done tool."""
        if not response:
            return False
        # The response will contain "Agent completion acknowledged:" if the tool was used
        return "Agent completion acknowledged:" in response
    
    def _is_agent_complete(self, response: str) -> bool:
        """Check if agent thinks it's done (fallback method)."""
        if not response:
            return True
            
        completion_indicators = [
            "FINAL_ANSWER:",
            "CONCLUSION:",
            "COMPLETE:",
            "FINAL RESPONSE:",
            "I have completed",
            "The task is finished",
            "Task completed",
            "Analysis complete"
        ]
        response_upper = response.upper()
        return any(indicator in response_upper for indicator in completion_indicators)

    async def _send_agent_step_update(self, current_step: int, max_steps: int, status: str) -> None:
        """Send agent step progress update to frontend."""
        payload = {
            "type": "agent_step_update",
            "current_step": current_step,
            "max_steps": max_steps,
            "status": status,
            "user": self.session.user_email
        }
        await self.session.send_json(payload)

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
        ********************************************************************
        ====================================================================
        IMPORTANT: This is the most critical function in the entire codebase.
        It processes incoming chat messages through the complete pipeline:
        - RAG integration (if applicable)
        - Tool validation
        - LLM calls with tools
        - Callback coordination
        ====================================================================
        ********************************************************************


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
            self.session.selected_prompts = message.get("selected_prompts", [])
            self.session.selected_data_sources = message.get("selected_data_sources", [])
            self.session.only_rag = message.get("only_rag", True)
            self.session.tool_choice_required = message.get("tool_choice_required", False)
            self.session.uploaded_files = message.get("files", {})

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
                logger.info(f"📁 User {self.session.user_email} uploaded {len(self.session.uploaded_files)} files:")
                for filename, file_data in self.session.uploaded_files.items():
                    file_size = len(file_data) if file_data else 0
                    logger.info(f"  - {filename} (size: {file_size} bytes)")
                    
                # Show potential file-related tools that could be used
                available_file_tools = [tool for tool in self.session.selected_tools 
                                       if any(keyword in tool.lower() 
                                             for keyword in ['pdf', 'file', 'document', 'analyze'])]
                if available_file_tools:
                    logger.info(f"📋 Available file processing tools: {available_file_tools}")
                else:
                    logger.warning(f"⚠️  No file processing tools selected despite file upload")
            
            # Log file uploads more clearly
            if self.session.uploaded_files:
                logger.info(f"📁 FILES UPLOADED: {len(self.session.uploaded_files)} files received:")
                for filename in self.session.uploaded_files.keys():
                    logger.info(f"📁   - {filename}")
            else:
                logger.info("📁 No files uploaded in this message")

            if not content or not self.session.model_name:
                raise ValueError("Message content and model name are required.")

            await self.session._trigger_callbacks("before_user_message_added", content=content)

            # Append available files to content if any exist
            enhanced_content = self._build_content_with_files(content)
            
            user_message = {"role": "user", "content": enhanced_content}
            
            # Check if this is the first user message and if we should apply custom system prompts
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
                        agent_mode,  # Pass agent mode flag
                        self.session.tool_choice_required,  # Pass tool choice preference
                        self.session.selected_tools,  # Pass selected tools for filtering
                    )
                    
                await self.session._trigger_callbacks("after_llm_call", llm_response=llm_response)

            assistant_message = {"role": "assistant", "content": llm_response}
            self.session.messages.append(assistant_message)
            await self.session._trigger_callbacks(
                "after_assistant_message_added", assistant_message=assistant_message
            )

            # In agent mode, return response instead of sending to WebSocket
            if agent_mode:
                return llm_response

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
            # Only try to send error if we're not in agent mode and connection is still open
            if not agent_mode:
                try:
                    await self.session.send_error(f"Error processing message: {exc}")
                except Exception as send_exc:
                    logger.error("Failed to send error message for chat processing to user %s: %s", self.session.user_email, send_exc)

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
                False,  # agent_mode
                self.session.tool_choice_required,  # Pass tool choice preference
                self.session.selected_tools,  # Pass selected tools for filtering
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
                False,  # agent_mode
                self.session.tool_choice_required,  # Pass tool choice preference
                self.session.selected_tools,  # Pass selected tools for filtering
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
                False,  # agent_mode
                self.session.tool_choice_required,  # Pass tool choice preference
                self.session.selected_tools,  # Pass selected tools for filtering
            )

    def _build_content_with_files(self, content: str) -> str:
        """Append available files to user prompt if any exist"""
        if not self.session.uploaded_files:
            return content
            
        file_list = "\n".join(f"- {filename}" for filename in self.session.uploaded_files.keys())
        return f"{content}\n\nFiles available:\n\n{file_list}"
    
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