"""
Simplified configuration management for Phase 1A.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .config_models import AppSettings, LLMConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """Simplified configuration manager for Phase 1A."""
    
    def __init__(self, backend_root: Optional[Path] = None):
        self._backend_root = backend_root or Path(__file__).parent.parent
        self._app_settings: Optional[AppSettings] = None
        self._llm_config: Optional[LLMConfig] = None
    
    def _search_paths(self, file_name: str) -> List[Path]:
        """Generate common search paths for a configuration file."""
        project_root = self._backend_root.parent
        
        candidates: List[Path] = [
            project_root / "config" / "overrides" / file_name,
            project_root / "config" / "defaults" / file_name,
            Path(file_name),
            Path(f"../{file_name}"),
            project_root / file_name,
            self._backend_root / file_name,
        ]
        
        return candidates
    
    def _load_file_with_error_handling(self, file_paths: List[Path], file_type: str) -> Optional[Dict[str, Any]]:
        """Load a file with error handling and logging."""
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
                    logger.error(f"Invalid {file_type} format in {path}: expected dict, got {type(data)}")
                    continue
                    
                logger.info(f"Successfully loaded {file_type} config from {path}")
                return data
                
            except (yaml.YAMLError, json.JSONDecodeError) as e:
                logger.error(f"{file_type} parsing error in {path}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error reading {path}: {e}")
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
                data = self._load_file_with_error_handling(file_paths, "YAML")
                
                if data:
                    self._llm_config = LLMConfig(**data)
                    logger.info(f"Loaded {len(self._llm_config.models)} models from LLM config")
                else:
                    self._llm_config = LLMConfig(models={})
                    logger.info("Created empty LLM config (no configuration file found)")
                    
            except Exception as e:
                logger.error(f"Failed to parse LLM configuration: {e}")
                self._llm_config = LLMConfig(models={})
        
        return self._llm_config


# Global configuration manager instance
config_manager = ConfigManager()