"""Pydantic models for configuration - Phase 1A."""

from typing import Dict, Optional, List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class LLMInstance(BaseModel):
    """Configuration for a single LLM instance."""
    model_name: str
    model_url: str
    api_key: str
    description: Optional[str] = None
    max_tokens: Optional[int] = 10000
    temperature: Optional[float] = 0.7
    extra_headers: Optional[Dict[str, str]] = None


class LLMConfig(BaseModel):
    """Configuration for all LLM models."""
    models: List[LLMInstance]
    
    # The validate_models method is no longer needed as we are expecting a list directly.
    # If the config file structure changes to a list of models, this method would need to be removed or adapted.
    # For now, we'll remove it as the request is to change LLMConfig to hold a list.
    # @classmethod
    # def validate_models(cls, v):
    #     """Convert dict values to ModelConfig objects."""
    #     if isinstance(v, dict):
    #         return {name: ModelConfig(**config) if isinstance(config, dict) else config 
    #                for name, config in v.items()}
    #     return v


class AppSettings(BaseSettings):
    """Main application settings loaded from environment variables."""
    
    app_name: str = "Chat UI"
    port: int = 8000
    debug_mode: bool = False
    log_level: str = "INFO"
    litellm_log_level: str = "INFO"
    
    # Config file names
    llm_config_file: str = Field(default="llmconfig.yml", validation_alias="LLM_CONFIG_FILE")
    
    model_config = {
        "env_file": "../.env", 
        "env_file_encoding": "utf-8", 
        "extra": "ignore",
        "env_prefix": "",
    }
