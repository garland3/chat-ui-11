"""
Simplified LLM manager for Phase 1A - basic LLM calling functionality only.
"""

import logging
import os
from typing import Any, Dict, List

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
    
    async def call_plain(self, model_name: str, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Plain LLM call - simplified for Phase 1A."""
        
        if not LITELLM_AVAILABLE:
            # Mock response for Phase 1A when LiteLLM is not available
            user_message = messages[-1].get("content", "") if messages else ""
            return f"Mock LLM response to: {user_message}"
        
        # Check that we have required configuration
        if not self.llm_config:
            raise ValueError("LLM configuration is required but not provided")
        
        if model_name not in self.llm_config.models:
            # print the found models
            logger.info(f"Available models: {list(self.llm_config.models.keys())}")
            print(f"Available models: {list(self.llm_config.models.keys())}")
            raise ValueError(f"Model '{model_name}' not found in LLM configuration")
        
        model_config = self.llm_config.models[model_name]
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
        if not self.llm_config or model_name not in self.llm_config.models:
            return model_name
        
        model_config = self.llm_config.models[model_name]
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
