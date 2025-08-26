"""
Simplified LLM manager for Phase 1A - basic LLM calling functionality only.
"""

import logging
import os
import json
from typing import Any, Dict, List

from common.models.common_models import ConversationHistory

# Set basic logging before imports
logger = logging.getLogger(__name__)

try:
    import litellm
    from litellm import acompletion

    LITELLM_AVAILABLE = True
    # Configure LiteLLM settings
    litellm.drop_params = True
    os.environ.setdefault("LITELLM_LOG", "INFO")
except ImportError:
    LITELLM_AVAILABLE = False
    logger.warning("LiteLLM not available, using mock responses")


class LLMManager:
    """Simplified LLM manager for Phase 1A - basic chat functionality."""

    def __init__(self, llm_config=None, debug_mode: bool = False):
        """Initialize with optional config dependency injection."""
        self.llm_config = llm_config
        self.debug_mode = debug_mode
        logger.info("LLMManager initialized for Phase 1A")

    def _get_model_config(self, model_name: str):
        """Get model configuration by name."""
        if not self.llm_config:
            raise ValueError("LLM configuration is required but not provided")

        for model_instance in self.llm_config.models:
            if model_instance.model_name == model_name:
                return model_instance

        # Model not found
        available_models = [model.model_name for model in self.llm_config.models]
        logger.info(f"Available models: {available_models}")
        print(f"Available models: {available_models}")
        raise ValueError(f"Model '{model_name}' not found in LLM configuration")

    def _setup_api_key(self, model_config):
        """Set up API key for the model."""
        api_key = os.path.expandvars(model_config.api_key)
        if api_key and not api_key.startswith("${"):
            if "openai" in model_config.model_url:
                os.environ["OPENAI_API_KEY"] = api_key
            elif "anthropic" in model_config.model_url:
                os.environ["ANTHROPIC_API_KEY"] = api_key

    def _get_mock_response(self, messages: List[Dict], with_tools: bool = False):
        """Get mock response when LiteLLM is not available."""
        user_message = messages[-1].get("content", "") if messages else ""
        if with_tools:
            return {
                "content": f"Mock LLM response with tools to: {user_message}",
                "tool_calls": [],
            }
        else:
            return f"Mock LLM response to: {user_message}"

    async def call_plain(
        self,
        model_name: str,
        conversation_history: ConversationHistory,
        temperature: float = 0.7,
    ) -> str:
        """Plain LLM call - simplified for Phase 1A."""

        messages = conversation_history.get_messages_for_llm()
        if not LITELLM_AVAILABLE:
            logger.info("NOT LITELLM_AVAILABLE")
            return self._get_mock_response(messages)

        model_config = self._get_model_config(model_name)
        litellm_model = self._get_litellm_model_name(model_name)

        kwargs = {
            "max_tokens": model_config.max_tokens or 1000,
            "temperature": temperature,
        }

        self._setup_api_key(model_config)

        try:
            logger.info(f"Calling LLM: {litellm_model} with {len(messages)} messages")

            response = await acompletion(
                model=litellm_model, messages=messages, **kwargs
            )

            content = response.choices[0].message.content or ""
            logger.info(f"LLM response received: {len(content)} characters")
            return content

        except Exception as exc:
            logger.error(f"Error calling LLM: {exc}")
            # Fallback to mock response
            return self._get_mock_response(messages)

    def _get_litellm_model_name(self, model_name: str) -> str:
        """Convert internal model name to LiteLLM compatible format."""
        if not self.llm_config:
            return model_name

        # Find the model instance by model_name
        model_config = None
        for model_instance in self.llm_config.models:
            if model_instance.model_name == model_name:
                model_config = model_instance
                break

        if model_config is None:
            return model_name

        model_id = model_config.model_name

        # Map common providers to LiteLLM format
        if "openrouter" in model_config.model_url:
            return f"openrouter/{model_id}"
        elif "openai" in model_config.model_url:
            return f"openai/{model_id}"
        elif "anthropic" in model_config.model_url:
            return f"anthropic/{model_id}"
        else:
            return model_id

    async def call_with_tools(
        self,
        model_name: str,
        conversation_history: ConversationHistory,
        tools: List[Dict[str, Any]],
        tool_choice: str = "auto",
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Call LLM with tools enabled."""

        messages = conversation_history.get_messages_for_llm()
        if not LITELLM_AVAILABLE:
            logger.info("NOT LITELLM_AVAILABLE - returning mock tool response")
            return self._get_mock_response(messages, with_tools=True)

        model_config = self._get_model_config(model_name)
        litellm_model = self._get_litellm_model_name(model_name)

        kwargs = {
            "max_tokens": model_config.max_tokens or 1000,
            "temperature": temperature,
            "tools": tools,
            "tool_choice": tool_choice,
        }

        self._setup_api_key(model_config)

        try:
            logger.info(
                f"Calling LLM with tools: {litellm_model} with {len(messages)} messages and {len(tools)} tools"
            )

            response = await acompletion(
                model=litellm_model, messages=messages, **kwargs
            )

            message = response.choices[0].message
            content = message.content or ""
            tool_calls = []

            # Extract tool calls if present
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tool_call in message.tool_calls:
                    # Parse arguments if they're a JSON string
                    arguments = tool_call.function.arguments
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Failed to parse tool arguments as JSON: {arguments}"
                            )
                            arguments = {}

                    tool_calls.append(
                        {
                            "id": tool_call.id,
                            "name": tool_call.function.name,
                            "arguments": arguments,
                        }
                    )

            logger.info(
                f"LLM response received: {len(content)} characters, {len(tool_calls)} tool calls"
            )
            return {"content": content, "tool_calls": tool_calls}

        except Exception as exc:
            logger.error(f"Error calling LLM with tools: {exc}")
            # Fallback to mock response
            return self._get_mock_response(messages, with_tools=True)
