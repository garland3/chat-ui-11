"""Configuration management handler for admin operations.

Handles all configuration-related operations including file I/O,
validation, and path resolution.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

import yaml
from fastapi import HTTPException

from managers.config.config_manager import config_manager

logger = logging.getLogger(__name__)


class ConfigHandler:
    """Handles configuration file operations for admin interface."""
    
    @staticmethod
    def _project_root() -> Path:
        """Get the project root directory."""
        # backend/managers/admin/config_handler.py -> project root is 4 levels up
        return Path(__file__).resolve().parents[4]

    @staticmethod
    def _config_base_dir() -> Path:
        """Get the base directory for configuration overrides."""
        base = Path(os.getenv("APP_CONFIG_OVERRIDES", "config/overrides"))
        if not base.is_absolute():
            base = ConfigHandler._project_root() / base
        base.mkdir(parents=True, exist_ok=True)
        return base

    @staticmethod
    def _defaults_dir() -> Path:
        """Get the defaults directory for configuration templates."""
        defaults = Path(os.getenv("APP_CONFIG_DEFAULTS", "config/defaults"))
        if not defaults.is_absolute():
            defaults = ConfigHandler._project_root() / defaults
        defaults.mkdir(parents=True, exist_ok=True)
        return defaults

    @classmethod
    def setup_config_overrides(cls) -> None:
        """Ensure editable overrides directory exists; seed from defaults if empty."""
        overrides_root = cls._config_base_dir()
        if any(overrides_root.iterdir()):
            return

        logger.info("Seeding empty overrides directory")
        for file_path in cls._defaults_dir().glob("*"):
            if file_path.is_file():
                dest = overrides_root / file_path.name
                try:
                    dest.write_bytes(file_path.read_bytes())
                    logger.info(f"Copied seed config {file_path} -> {dest}")
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Failed seeding {file_path}: {e}")

    @classmethod
    def get_admin_config_path(cls, filename: str) -> Path:
        """Resolve a config file path inside overrides, honoring known filenames.

        Uses AppSettings for known fields when available (e.g., LLM config file).
        """
        # Only LLM config filename is currently customizable in AppSettings
        if filename == "llmconfig.yml":
            filename = config_manager.app_settings.llm_config_file or filename
        # mcp.json, messages.txt, help-config.json fall back to defaults
        return cls._config_base_dir() / filename

    @staticmethod
    def get_file_content(file_path: Path) -> str:
        """Read file content with proper error handling."""
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File {file_path.name} not found")
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error reading file {file_path}: {e}")
            raise HTTPException(status_code=500, detail=f"Error reading file: {e}")

    @staticmethod
    def write_file_content(file_path: Path, content: str, file_type: str = "text") -> None:
        """Write file content with validation and atomic operations."""
        try:
            # Validate content based on file type
            if file_type == "json":
                json.loads(content)
            elif file_type == "yaml":
                yaml.safe_load(content)

            # Atomic write operation
            tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
            tmp_path.write_text(content, encoding="utf-8")
            if os.name == "nt" and file_path.exists():  # Windows atomic rename safety
                file_path.unlink()
            tmp_path.replace(file_path)
            logger.info(f"Updated config file {file_path}")
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid {file_type.upper()}: {e}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error writing file {file_path}: {e}")
            raise HTTPException(status_code=500, detail=f"Error writing file: {e}")

    @classmethod
    def get_banner_messages(cls) -> tuple[list[str], Path, float]:
        """Get banner messages from file."""
        cls.setup_config_overrides()
        messages_file = cls.get_admin_config_path("messages.txt")
        if not messages_file.exists():
            messages_file.write_text(
                "System status: All services operational\n", encoding="utf-8"
            )
        content = cls.get_file_content(messages_file)
        messages = [ln.strip() for ln in content.splitlines() if ln.strip()]
        return messages, messages_file, messages_file.stat().st_mtime

    @classmethod
    def update_banner_messages(cls, messages: list[str]) -> None:
        """Update banner messages in file."""
        cls.setup_config_overrides()
        messages_file = cls.get_admin_config_path("messages.txt")
        content = ("\n".join(messages) + "\n") if messages else ""
        cls.write_file_content(messages_file, content)

    @classmethod
    def get_mcp_config(cls) -> tuple[str, dict, Path, float]:
        """Get MCP configuration from file."""
        cls.setup_config_overrides()
        mcp_file = cls.get_admin_config_path("mcp.json")
        content = cls.get_file_content(mcp_file)
        parsed = json.loads(content)
        return content, parsed, mcp_file, mcp_file.stat().st_mtime

    @classmethod
    def update_mcp_config(cls, content: str) -> None:
        """Update MCP configuration file."""
        cls.setup_config_overrides()
        mcp_file = cls.get_admin_config_path("mcp.json")
        cls.write_file_content(mcp_file, content, "json")

    @classmethod
    def get_llm_config(cls) -> tuple[str, dict, Path, float]:
        """Get LLM configuration from file."""
        cls.setup_config_overrides()
        llm_file = cls.get_admin_config_path("llmconfig.yml")
        content = cls.get_file_content(llm_file)
        parsed = yaml.safe_load(content)
        return content, parsed, llm_file, llm_file.stat().st_mtime

    @classmethod
    def update_llm_config(cls, content: str) -> None:
        """Update LLM configuration file."""
        cls.setup_config_overrides()
        llm_file = cls.get_admin_config_path("llmconfig.yml")
        cls.write_file_content(llm_file, content, "yaml")

    @staticmethod
    def get_all_configs_view() -> Dict[str, Any]:
        """Get all configuration values for admin viewing with masking."""
        app_settings = config_manager.app_settings
        llm_config = config_manager.llm_config
        mcp_config = config_manager.get_mcp_config()

        # App settings dict - mask common secrets
        app_settings_dict = app_settings.model_dump()
        sensitive_fields = ["api_key", "secret", "password", "token", "access_key"]
        for key, value in list(app_settings_dict.items()):
            if any(s in key.lower() for s in sensitive_fields):
                if isinstance(value, str) and value:
                    app_settings_dict[key] = "***MASKED***"

        # LLM config - list of models; mask api_key per model
        llm_config_dict: Dict[str, Any] = {"models": []}
        for model in llm_config.models:
            model_dict = model.model_dump()
            if model_dict.get("api_key"):
                model_dict["api_key"] = "***MASKED***"
            llm_config_dict["models"].append(model_dict)

        # MCP config to dict
        mcp_config_dict = mcp_config.model_dump()

        # Simple validation flags for UI
        config_validation = {
            "app_settings": True,  # Settings object is always present
            "llm_config": len(llm_config.models) > 0,
            "mcp_config": len(mcp_config.servers) > 0,
        }

        return {
            "app_settings": app_settings_dict,
            "llm_config": llm_config_dict,
            "mcp_config": mcp_config_dict,
            "config_validation": config_validation,
        }