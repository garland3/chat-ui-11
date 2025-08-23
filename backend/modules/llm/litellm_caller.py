"""
LiteLLM-based LLM calling interface that handles all modes of LLM interaction.

This module provides a clean interface for calling LLMs using LiteLLM in different modes:
- Plain LLM calls (no tools)
- LLM calls with RAG integration
- LLM calls with tool support
- LLM calls with both RAG and tools

LiteLLM provides unified access to multiple LLM providers with automatic
fallbacks, cost tracking, and provider-specific optimizations.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass

# Set LiteLLM logging level before import to prevent verbose import messages
try:
    from modules.config import config_manager
    litellm_log_level = config_manager.app_settings.litellm_log_level
    os.environ["LITELLM_LOG"] = litellm_log_level.upper()
except Exception:
    # Fallback to INFO if config not available
    os.environ["LITELLM_LOG"] = "INFO"

import litellm
from litellm import completion, acompletion
from .models import LLMResponse

logger = logging.getLogger(__name__)

# Configure LiteLLM settings
litellm.drop_params = True  # Drop unsupported params instead of erroring


class LiteLLMCaller:
    """Clean interface for all LLM calling patterns using LiteLLM."""
    
    def __init__(self, llm_config=None, debug_mode: bool = False):
        """Initialize with optional config dependency injection."""
        # log the log level to info. 
      
        if llm_config is None:
            from modules.config import config_manager
            self.llm_config = config_manager.llm_config
            # Get LiteLLM log level from config
            litellm_log_level = config_manager.app_settings.litellm_log_level
        else:
            self.llm_config = llm_config
            # Fallback to INFO if no config manager available
            litellm_log_level = "INFO"
        logger.info(f"Initializing LiteLLMCaller with litellm_log_level={litellm_log_level}")
        # log the settings config level
        # logger.info(f"LiteLLM settings: {self.llm_config}")   

        # Update LiteLLM logging if debug_mode overrides config
        if debug_mode:
            os.environ["LITELLM_LOG"] = "DEBUG"
            litellm_logger = logging.getLogger("LiteLLM")
            litellm_logger.setLevel(logging.DEBUG)
        
        # Note: LiteLLM log level is already set at import time from config
            
        # Remove deprecated verbose setting
        # litellm.set_verbose = debug_mode  # This is deprecated
    
    def _get_litellm_model_name(self, model_name: str) -> str:
        """Convert internal model name to LiteLLM compatible format."""
        if model_name not in self.llm_config.models:
            raise ValueError(f"Model {model_name} not found in configuration")
        
        model_config = self.llm_config.models[model_name]
        model_id = model_config.model_name
        
        # Map common providers to LiteLLM format
        if "openrouter" in model_config.model_url:
            return f"openrouter/{model_id}"
        elif "openai" in model_config.model_url:
            return f"openai/{model_id}"
        elif "anthropic" in model_config.model_url:
            return f"anthropic/{model_id}"
        elif "google" in model_config.model_url:
            return f"google/{model_id}"
        else:
            # For custom endpoints, use the model_id directly
            return model_id
    
    def _get_model_kwargs(self, model_name: str, temperature: Optional[float] = None) -> Dict[str, Any]:
        """Get LiteLLM kwargs for a specific model."""
        if model_name not in self.llm_config.models:
            raise ValueError(f"Model {model_name} not found in configuration")
        
        model_config = self.llm_config.models[model_name]
        kwargs = {
            "max_tokens": model_config.max_tokens or 1000,
        }
        
        # Use provided temperature or fall back to config temperature
        if temperature is not None:
            kwargs["temperature"] = temperature
        else:
            kwargs["temperature"] = model_config.temperature or 0.7
        
        # Set API key
        api_key = os.path.expandvars(model_config.api_key)
        if api_key and not api_key.startswith("${"):
            if "openrouter" in model_config.model_url:
                kwargs["api_key"] = api_key
                # LiteLLM will automatically set the correct env var
                os.environ["OPENROUTER_API_KEY"] = api_key
            elif "openai" in model_config.model_url:
                os.environ["OPENAI_API_KEY"] = api_key
            elif "anthropic" in model_config.model_url:
                os.environ["ANTHROPIC_API_KEY"] = api_key
            elif "google" in model_config.model_url:
                os.environ["GOOGLE_API_KEY"] = api_key
        
        # Set custom API base for non-standard endpoints
        if hasattr(model_config, 'model_url') and model_config.model_url:
            if not any(provider in model_config.model_url for provider in ["openrouter", "api.openai.com", "api.anthropic.com"]):
                kwargs["api_base"] = model_config.model_url
        
        return kwargs

    def _log_pre_llm_call(self, messages, model_name, tools_schema=None, tool_choice=None):
        """Log LLM call input with truncated message content."""
        truncated_messages = []
        for msg in messages:
            content = str(msg.get('content', ''))
            truncated_content = content[:500] + "..." if len(content) > 500 else content
            truncated_messages.append({
                "role": msg.get("role"),
                "content": truncated_content,
                "has_tool_calls": bool(msg.get("tool_calls"))
            })
        
        tool_names = []
        if tools_schema:
            tool_names = [t.get("function", {}).get("name") for t in tools_schema if t.get("function")]
            # Debug: Log the full tools_schema to understand what's being filtered
            # logger.info("TOOLS_SCHEMA_DEBUG: Received %d tools in schema: %s", 
            #            len(tools_schema), [t.get("function", {}).get("name") for t in tools_schema])
        
        logger.info("LLM_CALL_INPUT: model=%s, messages=%d, tools_required=%s, tools=%s, content=%s", 
                    model_name, len(messages), 
                    tool_choice == "required", 
                    tool_names, truncated_messages)

    def _log_post_llm_response(self, response, model_name):
        """Log LLM response with truncated content and tool call details."""
        message = response.choices[0].message
        content = getattr(message, 'content', '') or ""
        tool_calls = getattr(message, 'tool_calls', None)
        
        truncated_content = content[:500] + "..." if len(content) > 500 else content
        tool_names = []
        tool_args_summary = []
        
        if tool_calls:
            for tc in tool_calls:
                if hasattr(tc, 'function'):
                    tool_names.append(tc.function.name)
                    args = getattr(tc.function, 'arguments', {})
                    if isinstance(args, str):
                        args_str = args[:200] + "..." if len(args) > 200 else args
                    else:
                        args_str = str(args)[:200]
                    tool_args_summary.append(f"{tc.function.name}({args_str})")
        
        # Combine all logging information into a single log message
        log_message = f"LLM_CALL_OUTPUT: model={model_name}, content_length={len(content)}, tool_calls={tool_names}"
        log_message += f"\nLLM_CALL_CONTENT: {truncated_content}"
        if tool_args_summary:
            log_message += f"\nLLM_CALL_TOOLS: {tool_args_summary}"
        
        logger.info(log_message)

    async def call_plain(self, model_name: str, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Plain LLM call - no tools, no RAG."""
        litellm_model = self._get_litellm_model_name(model_name)
        model_kwargs = self._get_model_kwargs(model_name, temperature)
        
        try:
            self._log_pre_llm_call(messages, model_name)
            
            response = await acompletion(
                model=litellm_model,
                messages=messages,
                **model_kwargs
            )
            
            self._log_post_llm_response(response, model_name)
            content = response.choices[0].message.content or ""
            return content
            
        except Exception as exc:
            logger.error("Error calling LLM: %s", exc, exc_info=True)
            raise Exception(f"Failed to call LLM: {exc}")

    async def call_plain_streaming(
        self, 
        model_name: str, 
        messages: List[Dict[str, str]], 
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        temperature: float = 0.7
    ) -> str:
        """Plain LLM call with streaming support - content is sent to callback as it arrives."""
        litellm_model = self._get_litellm_model_name(model_name)
        model_kwargs = self._get_model_kwargs(model_name, temperature)
        
        try:
            self._log_pre_llm_call(messages, model_name)
            
            # Enable streaming
            model_kwargs["stream"] = True
            
            response = await acompletion(
                model=litellm_model,
                messages=messages,
                **model_kwargs
            )
            
            content_parts = []
            
            # Stream the response
            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content_parts.append(delta.content)
                        if stream_callback:
                            await stream_callback(delta.content)
            
            full_content = "".join(content_parts)
            logger.info("LLM_CALL_OUTPUT: model=%s, content_length=%d, streaming=true", model_name, len(full_content))
            logger.info("LLM_STREAMING_CONTENT: %s", full_content[:500] + "..." if len(full_content) > 500 else full_content)
            return full_content
            
        except Exception as exc:
            logger.error("Error in streaming LLM call: %s", exc, exc_info=True)
            # Fallback to non-streaming if streaming fails
            logger.info("Falling back to non-streaming call")
            return await self.call_plain(model_name, messages, temperature)
    
    async def call_with_rag(
        self, 
        model_name: str, 
        messages: List[Dict[str, str]], 
        data_sources: List[str],
        user_email: str,
        rag_client=None,
        temperature: float = 0.7,
    ) -> str:
        """LLM call with RAG integration."""
        if not data_sources:
            return await self.call_plain(model_name, messages, temperature=temperature)
        
        # Import RAG client if not provided
        if rag_client is None:
            from modules.rag import rag_client as default_rag_client
            rag_client = default_rag_client
        
        # Use the first selected data source
        data_source = data_sources[0]
        
        try:
            # Query RAG for context
            rag_response = await rag_client.query_rag(
                user_email,
                data_source,
                messages
            )
            
            # Integrate RAG context into messages
            messages_with_rag = messages.copy()
            rag_context_message = {
                "role": "system", 
                "content": f"Retrieved context from {data_source}:\n\n{rag_response.content}\n\nUse this context to inform your response."
            }
            messages_with_rag.insert(-1, rag_context_message)
            
            # Call LLM with enriched context
            llm_response = await self.call_plain(model_name, messages_with_rag, temperature=temperature)
            
            # Append metadata if available
            if rag_response.metadata:
                metadata_summary = self._format_rag_metadata(rag_response.metadata)
                llm_response += f"\n\n---\n**RAG Sources & Processing Info:**\n{metadata_summary}"
            
            return llm_response
            
        except Exception as exc:
            logger.error(f"Error in RAG-integrated query: {exc}")
            # Fallback to plain LLM call
            return await self.call_plain(model_name, messages, temperature=temperature)
    
    async def call_with_tools(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        tools_schema: List[Dict],
        tool_choice: str = "auto",
        temperature: float = 0.7,
    ) -> LLMResponse:
        """LLM call with tool support using LiteLLM."""
        if not tools_schema:
            content = await self.call_plain(model_name, messages, temperature=temperature)
            return LLMResponse(content=content, model_used=model_name)

        litellm_model = self._get_litellm_model_name(model_name)
        model_kwargs = self._get_model_kwargs(model_name, temperature)
        
        # Handle tool_choice parameter - some providers don't support "required"
        final_tool_choice = tool_choice
        if tool_choice == "required":
            # Try with "required" first, fallback to "auto" if unsupported
            final_tool_choice = "auto"
            logger.info(f"Using tool_choice='auto' instead of 'required' for better compatibility")

        try:
            self._log_pre_llm_call(messages, model_name, tools_schema, final_tool_choice)
            
            response = await acompletion(
                model=litellm_model,
                messages=messages,
                tools=tools_schema,
                tool_choice=final_tool_choice,
                **model_kwargs
            )
            
            self._log_post_llm_response(response, model_name)
            message = response.choices[0].message
            return LLMResponse(
                content=getattr(message, 'content', None) or "",
                tool_calls=getattr(message, 'tool_calls', None),
                model_used=model_name
            )
            
        except Exception as exc:
            # If we used "required" and it failed, try again with "auto"
            if tool_choice == "required" and final_tool_choice == "required":
                logger.warning(f"Tool choice 'required' failed, retrying with 'auto': {exc}")
                try:
                    response = await acompletion(
                        model=litellm_model,
                        messages=messages,
                        tools=tools_schema,
                        tool_choice="auto",
                        **model_kwargs
                    )
                    
                    self._log_post_llm_response(response, model_name)
                    message = response.choices[0].message
                    return LLMResponse(
                        content=getattr(message, 'content', None) or "",
                        tool_calls=getattr(message, 'tool_calls', None),
                        model_used=model_name
                    )
                except Exception as retry_exc:
                    logger.error("Retry with tool_choice='auto' also failed: %s", retry_exc, exc_info=True)
                    raise Exception(f"Failed to call LLM with tools: {retry_exc}")
            
            logger.error("Error calling LLM with tools: %s", exc, exc_info=True)
            raise Exception(f"Failed to call LLM with tools: {exc}")
    
    async def call_with_rag_and_tools(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        data_sources: List[str],
        tools_schema: List[Dict],
        user_email: str,
        tool_choice: str = "auto",
        rag_client=None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Full integration: RAG + Tools."""
        if not data_sources:
            return await self.call_with_tools(model_name, messages, tools_schema, tool_choice, temperature=temperature)
        
        # Import RAG client if not provided
        if rag_client is None:
            from modules.rag import rag_client as default_rag_client
            rag_client = default_rag_client
        
        # Use the first selected data source
        data_source = data_sources[0]
        
        try:
            # Query RAG for context
            rag_response = await rag_client.query_rag(
                user_email,
                data_source,
                messages
            )
            
            # Integrate RAG context into messages
            messages_with_rag = messages.copy()
            rag_context_message = {
                "role": "system", 
                "content": f"Retrieved context from {data_source}:\n\n{rag_response.content}\n\nUse this context to inform your response."
            }
            messages_with_rag.insert(-1, rag_context_message)
            
            # Call LLM with enriched context and tools
            logger.info("LLM_CALL_WITH_RAG: model=%s, data_source=%s, enriched_messages=%d", 
                       model_name, data_source, len(messages_with_rag))
            llm_response = await self.call_with_tools(model_name, messages_with_rag, tools_schema, tool_choice, temperature=temperature)
            
            # Append metadata to content if available and no tool calls
            if rag_response.metadata and not llm_response.has_tool_calls():
                metadata_summary = self._format_rag_metadata(rag_response.metadata)
                llm_response.content += f"\n\n---\n**RAG Sources & Processing Info:**\n{metadata_summary}"
            
            return llm_response
            
        except Exception as exc:
            logger.error(f"Error in RAG+tools integrated query: {exc}")
            # Fallback to tools-only call
            return await self.call_with_tools(model_name, messages, tools_schema, tool_choice, temperature=temperature)
    
    def _format_rag_metadata(self, metadata) -> str:
        """Format RAG metadata into a user-friendly summary."""
        # Import here to avoid circular imports
        try:
            from modules.rag.models import RAGMetadata
            if not isinstance(metadata, RAGMetadata):
                return "Metadata unavailable"
        except ImportError:
            return "Metadata unavailable"
        
        summary_parts = []
        summary_parts.append(f" **Data Source:** {metadata.data_source_name}")
        summary_parts.append(f" **Processing Time:** {metadata.query_processing_time_ms}ms")
        
        if metadata.documents_found:
            summary_parts.append(f" **Documents Found:** {len(metadata.documents_found)} (searched {metadata.total_documents_searched})")
            
            for i, doc in enumerate(metadata.documents_found[:3]):
                confidence_percent = int(doc.confidence_score * 100)
                summary_parts.append(f"  • {doc.source} ({confidence_percent}% relevance, {doc.content_type})")
            
            if len(metadata.documents_found) > 3:
                remaining = len(metadata.documents_found) - 3
                summary_parts.append(f"  • ... and {remaining} more document(s)")
        
        summary_parts.append(f" **Retrieval Method:** {metadata.retrieval_method}")
        return "\n".join(summary_parts)
