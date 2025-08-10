"""
Centralized configuration management using Pydantic models.

This module provides a unified configuration system that:
- Uses Pydantic for type validation and environment variable loading
- Replaces the duplicate config loading logic in config_utils.py
- Provides proper error handling with logging tracebacks
- Supports both .env files and direct environment variables
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class ModelConfig(BaseModel):
    """Configuration for a single LLM model."""
    model_name: str
    model_url: str
    api_key: str
    description: Optional[str] = None
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7
    # Optional extra HTTP headers (e.g. for providers like OpenRouter)
    extra_headers: Optional[Dict[str, str]] = None


class LLMConfig(BaseModel):
    """Configuration for all LLM models."""
    models: Dict[str, ModelConfig]
    
    @field_validator('models', mode='before')
    @classmethod
    def validate_models(cls, v):
        """Convert dict values to ModelConfig objects."""
        if isinstance(v, dict):
            return {name: ModelConfig(**config) if isinstance(config, dict) else config 
                   for name, config in v.items()}
        return v


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""
    description: Optional[str] = None
    author: Optional[str] = None         # Author of the MCP server
    short_description: Optional[str] = None  # Short description for marketplace display
    help_email: Optional[str] = None     # Contact email for help/support
    groups: List[str] = Field(default_factory=list)
    is_exclusive: bool = False
    enabled: bool = True
    command: Optional[List[str]] = None  # Command to run server (for stdio servers)
    cwd: Optional[str] = None            # Working directory for command
    url: Optional[str] = None            # URL for HTTP servers
    type: str = "stdio"                  # Server type: "stdio" or "http" (deprecated, use transport)
    transport: Optional[str] = None      # Explicit transport: "stdio", "http", "sse" - takes priority over auto-detection


class MCPConfig(BaseModel):
    """Configuration for all MCP servers."""
    servers: Dict[str, MCPServerConfig] = Field(default_factory=dict)
    
    @field_validator('servers', mode='before')
    @classmethod
    def validate_servers(cls, v):
        """Convert dict values to MCPServerConfig objects."""
        if isinstance(v, dict):
            return {name: MCPServerConfig(**config) if isinstance(config, dict) else config 
                   for name, config in v.items()}
        return v


class AppSettings(BaseSettings):
    """Main application settings loaded from environment variables."""
    
    # Application settings
    app_name: str = "Chat UI"
    port: int = 8000
    debug_mode: bool = False
    
    # RAG settings
    mock_rag: bool = False
    rag_mock_url: str = "http://localhost:8001"
    
    # Banner settings
    banner_enabled: bool = False
    mock_banner: bool = False
    banner_mock_url: str = "http://localhost:8002"
    banner_api_key: str = ""
    
    # Agent settings
    agent_mode_available: bool = True
    agent_max_steps: int = 10
    
    # LLM Health Check settings
    llm_health_check_interval: int = 5  # minutes
    
    # MCP Health Check settings  
    mcp_health_check_interval: int = 300  # seconds (5 minutes)
    
    # Admin settings
    admin_group: str = "admin"
    
    # S3 storage settings
    s3_endpoint: str = "http://127.0.0.1:8003"
    s3_use_mock: bool = True
    s3_timeout: int = 30
    
    # Feature flags
    feature_workspaces_enabled: bool = False
    feature_rag_enabled: bool = False
    feature_tools_enabled: bool = False
    feature_marketplace_enabled: bool = False
    feature_files_panel_enabled: bool = False
    feature_chat_history_enabled: bool = False
    
    model_config = {
        "env_file": "../.env", 
        "env_file_encoding": "utf-8", 
        "extra": "ignore",
        "env_prefix": ""
    }


class ConfigManager:
    """Centralized configuration manager with proper error handling."""
    
    def __init__(self):
        self._app_settings: Optional[AppSettings] = None
        self._llm_config: Optional[LLMConfig] = None
        self._mcp_config: Optional[MCPConfig] = None
    
    def _search_paths(self, file_name: str) -> List[Path]:
        """Generate common search paths for a configuration file.
        
        Prioritizes configfilesadmin (admin-managed) over configfiles (default).
        """
        current_dir = Path(__file__).parent
        return [
            current_dir / "configfilesadmin" / file_name,  # Admin-managed configs (highest priority)
            current_dir / "configfiles" / file_name,        # Default configs
            Path(file_name),
            Path(f"../{file_name}"),
            current_dir.parent / file_name,
            current_dir / file_name,
        ]
    
    def _load_file_with_error_handling(self, file_paths: List[Path], file_type: str) -> Optional[Dict[str, Any]]:
        """Load a file with comprehensive error handling and logging."""
        for path in file_paths:
            try:
                if not path.exists():
                    continue
                    
                logger.info(f"Found {file_type} config at: {path.absolute()}")
                
                with open(path, "r", encoding="utf-8") as f:
                    if file_type.lower() == "yaml":
                        data = yaml.safe_load(f)
                    elif file_type.lower() == "json":
                        data = json.load(f)
                    else:
                        raise ValueError(f"Unsupported file type: {file_type}")
                
                if not isinstance(data, dict):
                    logger.error(
                        f"Invalid {file_type} format in {path}: expected dict, got {type(data)}",
                        exc_info=True
                    )
                    continue
                    
                logger.info(f"Successfully loaded {file_type} config from {path}")
                return data
                
            except (yaml.YAMLError, json.JSONDecodeError) as e:
                logger.error(f"{file_type} parsing error in {path}: {e}", exc_info=True)
                continue
            except Exception as e:
                logger.error(f"Unexpected error reading {path}: {e}", exc_info=True)
                continue
        
        logger.warning(f"{file_type} config not found in any of these locations: {[str(p) for p in file_paths]}")
        return None
    
    @property
    def app_settings(self) -> AppSettings:
        """Get application settings (cached)."""
        if self._app_settings is None:
            try:
                self._app_settings = AppSettings()
                logger.info("Application settings loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load application settings: {e}", exc_info=True)
                # Create default settings as fallback
                self._app_settings = AppSettings()
        return self._app_settings
    
    @property
    def llm_config(self) -> LLMConfig:
        """Get LLM configuration (cached)."""
        if self._llm_config is None:
            try:
                file_paths = self._search_paths("llmconfig.yml")
                data = self._load_file_with_error_handling(file_paths, "YAML")
                
                if data:
                    self._llm_config = LLMConfig(**data)
                    logger.info(f"Loaded {len(self._llm_config.models)} models from LLM config")
                else:
                    self._llm_config = LLMConfig(models={})
                    logger.info("Created empty LLM config (no configuration file found)")
                    
            except Exception as e:
                logger.error(f"Failed to parse LLM configuration: {e}", exc_info=True)
                self._llm_config = LLMConfig(models={})
        
        return self._llm_config
    
    @property
    def mcp_config(self) -> MCPConfig:
        """Get MCP configuration (cached)."""
        if self._mcp_config is None:
            try:
                file_paths = self._search_paths("mcp.json")
                data = self._load_file_with_error_handling(file_paths, "JSON")
                
                if data:
                    # Convert flat structure to nested structure for Pydantic
                    servers_data = {"servers": data}
                    self._mcp_config = MCPConfig(**servers_data)
                    logger.info(f"Loaded MCP config with {len(self._mcp_config.servers)} servers: {list(self._mcp_config.servers.keys())}")
                else:
                    self._mcp_config = MCPConfig()
                    logger.info("Created empty MCP config (no configuration file found)")
                    
            except Exception as e:
                logger.error(f"Failed to parse MCP configuration: {e}", exc_info=True)
                self._mcp_config = MCPConfig()
        
        return self._mcp_config
    
    def reload_configs(self) -> None:
        """Reload all configurations from files."""
        self._app_settings = None
        self._llm_config = None
        self._mcp_config = None
        logger.info("Configuration cache cleared, will reload on next access")
    
    def validate_config(self) -> Dict[str, bool]:
        """Validate all configurations and return status."""
        status = {}
        
        try:
            self.app_settings
            status["app_settings"] = True
        except Exception as e:
            logger.error(f"App settings validation failed: {e}", exc_info=True)
            status["app_settings"] = False
        
        try:
            llm_config = self.llm_config
            status["llm_config"] = len(llm_config.models) > 0
            if not status["llm_config"]:
                logger.warning("LLM config is valid but contains no models")
        except Exception as e:
            logger.error(f"LLM config validation failed: {e}", exc_info=True)
            status["llm_config"] = False
        
        try:
            mcp_config = self.mcp_config
            status["mcp_config"] = len(mcp_config.servers) > 0
            if not status["mcp_config"]:
                logger.warning("MCP config is valid but contains no servers")
        except Exception as e:
            logger.error(f"MCP config validation failed: {e}", exc_info=True)
            status["mcp_config"] = False
        
        return status


# Global configuration manager instance
config_manager = ConfigManager()


# Convenience functions for easy access
def get_app_settings() -> AppSettings:
    """Get application settings."""
    return config_manager.app_settings


def get_llm_config() -> LLMConfig:
    """Get LLM configuration."""
    return config_manager.llm_config


def get_mcp_config() -> MCPConfig:
    """Get MCP configuration."""
    return config_manager.mcp_config