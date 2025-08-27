"""
Simplified configuration management for Phase 1A.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
import yaml

from managers.config.config_models import (
    AppSettings,
    LLMConfig,
    LLMInstance,
    MCPConfig,
    MCPServerConfigModel,
)

logger = logging.getLogger(__name__)


class ConfigManager:
    """Simplified configuration manager for Phase 1A."""

    def __init__(self, backend_root: Optional[Path] = None):
        self._backend_root = backend_root or Path(__file__).parent.parent
        self._app_settings: Optional[AppSettings] = None
        self._llm_config: Optional[LLMConfig] = None
        self._mcp_config: Optional[MCPConfig] = None

        # Load environment variables from .env file
        dotenv_path = self._backend_root.parent / ".env"
        load_dotenv(dotenv_path=dotenv_path)
        logger.info(f"Loading .env from {dotenv_path.resolve()}")

    def _search_paths(self, file_name: str) -> List[Path]:
        """Generate common search paths for a configuration file."""
        candidates: List[Path] = [
            Path("../config/overrides") / file_name,
            Path("../config/defaults") / file_name,
            Path(file_name),
            Path(f"../{file_name}"),
        ]

        return candidates

    def _load_file_with_error_handling(
        self, file_paths: List[Path], file_type: str
    ) -> List[LLMInstance]:
        """Load a file with error handling and logging, returning a list of LLMInstances."""
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

                logger.info(f"Successfully loaded {file_type} config from {path}")

                # Convert loaded data to list of LLMInstances
                if isinstance(data, dict) and "models" in data:
                    # Handle dict format with 'models' key
                    models_data = data["models"]
                    if isinstance(models_data, dict):
                        # Convert dict of models to list
                        instances = []
                        for name, config in models_data.items():
                            if isinstance(config, dict):
                                # Create a copy of config and use the key name as identifier if no model_name exists
                                config_copy = config.copy()
                                if "model_name" not in config_copy:
                                    config_copy["model_name"] = name
                                instances.append(LLMInstance(**config_copy))
                            else:
                                instances.append(config)
                        return instances
                    elif isinstance(models_data, list):
                        # Already a list of models
                        return [
                            LLMInstance(**model) if isinstance(model, dict) else model
                            for model in models_data
                        ]
                elif isinstance(data, list):
                    # Handle direct list format
                    return [
                        LLMInstance(**model) if isinstance(model, dict) else model
                        for model in data
                    ]
                else:
                    logger.error(f"Unexpected data format in config file: {type(data)}")
                    return []

            except (yaml.YAMLError, json.JSONDecodeError) as e:
                logger.error(f"{file_type} parsing error in {path}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error reading {path}: {e}")
                continue

        logger.warning(
            f"{file_type} config not found in any of these locations: {[str(p) for p in file_paths]}"
        )
        return []

    @property
    def app_settings(self) -> AppSettings:
        """Get application settings (cached)."""
        if self._app_settings is None:
            try:
                self._app_settings = AppSettings()
                logger.info("Application settings loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load application settings: {e}")
                self._app_settings = AppSettings()
        return self._app_settings

    @property
    def llm_config(self) -> LLMConfig:
        """Get LLM configuration (cached)."""
        if self._llm_config is None:
            try:
                llm_filename = self.app_settings.llm_config_file
                file_paths = self._search_paths(llm_filename)
                llm_instances = self._load_file_with_error_handling(file_paths, "YAML")
                self._llm_config = LLMConfig(models=llm_instances)

                if llm_instances:
                    logger.info(
                        f"Loaded {len(self._llm_config.models)} models from LLM config"
                    )
                else:
                    logger.info(
                        "Created empty LLM config (no configuration file found)"
                    )

            except Exception as e:
                logger.error(f"Failed to parse LLM configuration: {e}")
                self._llm_config = LLMConfig(models=[])

        return self._llm_config

    def get_mcp_config(self) -> MCPConfig:
        """Get MCP configuration (cached)."""
        if self._mcp_config is None:
            try:
                # Look for mcp.json in the standard locations
                file_paths = self._search_paths("mcp.json")

                # Load JSON configuration
                for path in file_paths:
                    if path.exists():
                        try:
                            with open(path, "r", encoding="utf-8") as f:
                                mcp_data = json.load(f)

                            # Handle different MCP config formats
                            if "mcpServers" in mcp_data:
                                # Standard MCP format
                                servers_data = mcp_data["mcpServers"]
                            elif "servers" in mcp_data:
                                # Our format
                                servers_data = mcp_data["servers"]
                            else:
                                # Assume the whole thing is servers
                                servers_data = mcp_data

                            # Convert to our models
                            servers = {}
                            for name, config in servers_data.items():
                                # Handle command as either string or list
                                if "command" in config:
                                    if isinstance(config["command"], str):
                                        config["command"] = [config["command"]]

                                servers[name] = MCPServerConfigModel(**config)

                            self._mcp_config = MCPConfig(servers=servers)
                            logger.info(
                                f"Loaded MCP config from {path} with {len(servers)} servers"
                            )
                            break

                        except Exception as e:
                            logger.error(f"Error parsing MCP config from {path}: {e}")
                            continue

                if self._mcp_config is None:
                    logger.warning(
                        f"MCP config not found in any of these locations: {[str(p) for p in file_paths]}"
                    )
                    self._mcp_config = MCPConfig()

            except Exception as e:
                logger.error(f"Failed to load MCP configuration: {e}")
                self._mcp_config = MCPConfig()

        return self._mcp_config


# Global configuration manager instance
config_manager = ConfigManager()
