"""Prompt manager to load and render system prompts with minimal coupling."""

import logging
from pathlib import Path
from typing import Optional

from managers.config.config_manager import config_manager

logger = logging.getLogger(__name__)


class PromptManager:
    """Responsible for loading and rendering prompts."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path("..")
        self._cached_default_prompt: Optional[str] = None

    def _resolve_path(self, path_str: str) -> Path:
        path = Path(path_str)
        if not path.is_absolute():
            # Try relative to repo root (two levels up from this file)
            candidate = Path(__file__).resolve().parents[2] / path
            return candidate
        return path

    def load_default_system_prompt(self) -> str:
        """Load the default system prompt content, cached for performance."""
        if self._cached_default_prompt is not None:
            return self._cached_default_prompt

        path_str = config_manager.app_settings.system_prompt_file
        path = self._resolve_path(path_str)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                self._cached_default_prompt = content
                logger.info(f"Loaded system prompt from {path}")
                return content
        except Exception as e:
            logger.error(
                f"Failed to load system prompt from {path}: {e}. Falling back to minimal prompt."
            )
            fallback = "You are a helpful AI assistant."
            self._cached_default_prompt = fallback
            return fallback

    def render_prompt(self, template: str, user_email: Optional[str]) -> str:
        """Render prompt by substituting minimal variables. Uses Python format()."""
        try:
            return template.format(user_email=user_email or "unknown")
        except Exception:
            # If formatting fails due to braces, return raw content
            return template


# Singleton prompt manager for convenience
prompt_manager = PromptManager()
