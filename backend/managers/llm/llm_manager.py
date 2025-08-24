"""
Simplified LLM manager for Phase 1A - basic LLM calling functionality only.
"""

import logging
import os
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
    
    async def call_plain(self, model_name: str, conversation_history: ConversationHistory, temperature: float = 0.7) -> str:
        """Plain LLM call - simplified for Phase 1A."""
        
        messages = conversation_history.get_messages_for_llm()
        if not LITELLM_AVAILABLE:
            logger.info("NOT LITELLM_AVAILABLE")
            # Mock response for Phase 1A when LiteLLM is not available
            user_message = messages[-1].get("content", "") if messages else ""
            return f"Mock LLM response to: {user_message}"
        
        # Check that we have required configuration
        if not self.llm_config:
            raise ValueError("LLM configuration is required but not provided")
        
        # Find the model instance by model_name
        model_config = None
        for model_instance in self.llm_config.models:
            if model_instance.model_name == model_name:
                model_config = model_instance
                break
        
        if model_config is None:
            # print the found models
            available_models = [model.model_name for model in self.llm_config.models]
            logger.info(f"Available models: {available_models}")
            print(f"Available models: {available_models}")
            raise ValueError(f"Model '{model_name}' not found in LLM configuration")
        litellm_model = self._get_litellm_model_name(model_name)
        kwargs = {
            "max_tokens": model_config.max_tokens or 1000,
            "temperature": temperature,
        }
        # Set API key
        api_key = os.path.expandvars(model_config.api_key)
        if api_key and not api_key.startswith("${"):
            if "openai" in model_config.model_url:
                os.environ["OPENAI_API_KEY"] = api_key
            elif "anthropic" in model_config.model_url:
                os.environ["ANTHROPIC_API_KEY"] = api_key
        
        try:
            logger.info(f"Calling LLM: {litellm_model} with {len(messages)} messages")
             # Get conversation history for LLM
            response = await acompletion(
                model=litellm_model,
                messages=messages,
                **kwargs
            )
            
            content = response.choices[0].message.content or ""
            logger.info(f"LLM response received: {len(content)} characters")
            return content
            
        except Exception as exc:
            logger.error(f"Error calling LLM: {exc}")
            # Fallback to mock response
            user_message = messages[-1].get("content", "") if messages else ""
            return f"Error calling LLM, fallback response to: {user_message}"
    
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
