"""Tests for the config manager."""

import pytest
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from managers.config.config_manager import ConfigManager


def test_config_manager_finds_llm_config():
    """Test that config manager can find and load the LLM config file."""
    config_manager = ConfigManager()
    
    # Test that LLM config is loaded successfully
    llm_config = config_manager.llm_config
    
    # Should have models loaded (not empty)
    assert len(llm_config.models) > 0, "LLM config should contain models"
    
    # Verify we can access the models dict
    assert isinstance(llm_config.models, dict), "Models should be a dictionary"


def test_config_manager_search_paths():
    """Test that config manager generates correct search paths."""
    config_manager = ConfigManager()
    
    search_paths = config_manager._search_paths("llmconfig.yml")
    
    # Convert to strings for easier comparison
    path_strings = [str(p) for p in search_paths]
    
    # Should include the expected relative paths
    assert "../config/overrides/llmconfig.yml" in path_strings
    assert "../config/defaults/llmconfig.yml" in path_strings
    assert "llmconfig.yml" in path_strings
    assert "../llmconfig.yml" in path_strings


def test_config_manager_app_settings():
    """Test that config manager loads app settings."""
    config_manager = ConfigManager()
    
    app_settings = config_manager.app_settings
    
    # Should have loaded without error
    assert app_settings is not None
    assert hasattr(app_settings, 'llm_config_file')