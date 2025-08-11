"""
Tests for the Config module (10 tests).
"""
import os
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

import pytest

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from modules.config import ConfigManager, AppSettings, LLMConfig, MCPConfig


class TestConfigModule:
    """Test Config module with 10 focused tests."""
    
    def test_config_manager_initialization(self):
        """Test that ConfigManager initializes correctly."""
        manager = ConfigManager()
        assert manager._app_settings is None
        assert manager._llm_config is None
        assert manager._mcp_config is None
    
    def test_app_settings_initialization(self):
        """Test AppSettings initialization works."""
        settings = AppSettings()
        # Check that basic properties exist and have correct types
        assert isinstance(settings.app_name, str)
        assert isinstance(settings.port, int)
        assert isinstance(settings.debug_mode, bool)
        assert isinstance(settings.log_level, str)
    
    def test_app_settings_from_env(self):
        """Test AppSettings loading from environment."""
        env_vars = {"PORT": "9000", "DEBUG_MODE": "true"}
        with patch.dict(os.environ, env_vars, clear=True):
            settings = AppSettings()
            assert settings.port == 9000
            assert settings.debug_mode == True
    
    def test_llm_config_empty(self):
        """Test empty LLM configuration."""
        config = LLMConfig(models={})
        assert len(config.models) == 0
    
    def test_llm_config_with_models(self):
        """Test LLM configuration with models."""
        models_data = {
            "gpt-4": {
                "model_name": "gpt-4",
                "model_url": "https://api.openai.com/v1/chat/completions", 
                "api_key": "test-key"
            }
        }
        config = LLMConfig(models=models_data)
        assert len(config.models) == 1
        assert "gpt-4" in config.models
    
    def test_mcp_config_empty(self):
        """Test empty MCP configuration."""
        config = MCPConfig()
        assert len(config.servers) == 0
    
    def test_mcp_config_with_servers(self):
        """Test MCP configuration with servers."""
        servers_data = {
            "servers": {
                "test-server": {"enabled": True, "groups": ["admin"]}
            }
        }
        config = MCPConfig(**servers_data)
        assert len(config.servers) == 1
        assert "test-server" in config.servers
    
    def test_config_validation(self):
        """Test configuration validation."""
        manager = ConfigManager()
        status = manager.validate_config()
        assert isinstance(status, dict)
        assert "app_settings" in status
        assert "llm_config" in status
        assert "mcp_config" in status
    
    def test_config_reload(self):
        """Test configuration reload clears cache."""
        manager = ConfigManager()
        _ = manager.app_settings  # Cache it
        manager.reload_configs()
        assert manager._app_settings is None
    
    def test_agent_mode_backward_compatibility(self):
        """Test backward compatibility for agent_mode_available."""
        settings = AppSettings()
        assert settings.agent_mode_available == settings.feature_agent_mode_available