"""
Unit tests for the configuration system.
"""
import os
import pytest
import tempfile
from unittest.mock import patch, mock_open
from pathlib import Path

# Import the config module
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config import ConfigManager, AppSettings, ModelConfig, LLMConfig, MCPServerConfig, MCPConfig


class TestAppSettings:
    """Test AppSettings configuration model."""
    
    def test_app_settings_defaults(self):
        """Test default values for app settings."""
        settings = AppSettings()
        assert settings.app_name == "Chat UI"
        assert settings.port == 8000
        assert settings.debug_mode is False
        
    def test_app_settings_with_values(self):
        """Test app settings with custom values."""
        settings = AppSettings(
            app_name="Test App",
            port=9000,
            debug_mode=True
        )
        assert settings.app_name == "Test App"
        assert settings.port == 9000
        assert settings.debug_mode is True


class TestModelConfig:
    """Test ModelConfig configuration model."""
    
    def test_model_config_creation(self):
        """Test creating a model configuration."""
        config = ModelConfig(
            model_name="gpt-4",
            model_url="https://api.openai.com/v1/chat/completions",
            api_key="test-key"
        )
        assert config.model_name == "gpt-4"
        assert config.model_url == "https://api.openai.com/v1/chat/completions"
        assert config.api_key == "test-key"
        assert config.max_tokens == 1000  # default
        assert config.temperature == 0.7  # default
        
    def test_model_config_with_custom_values(self):
        """Test model config with custom values."""
        config = ModelConfig(
            model_name="claude-3",
            model_url="https://api.anthropic.com/v1/messages",
            api_key="test-key",
            max_tokens=2000,
            temperature=0.9
        )
        assert config.max_tokens == 2000
        assert config.temperature == 0.9


class TestMCPServerConfig:
    """Test MCPServerConfig configuration model."""
    
    def test_mcp_server_config_defaults(self):
        """Test MCP server config defaults."""
        config = MCPServerConfig()
        assert config.description is None
        assert config.groups == []
        assert config.is_exclusive is False
        assert config.enabled is True
        
    def test_mcp_server_config_with_values(self):
        """Test MCP server config with values."""
        config = MCPServerConfig(
            description="Test server",
            groups=["users", "admin"],
            is_exclusive=True,
            enabled=False
        )
        assert config.description == "Test server"
        assert config.groups == ["users", "admin"]
        assert config.is_exclusive is True
        assert config.enabled is False


class TestConfigManager:
    """Test ConfigManager functionality."""
    
    @patch.dict(os.environ, {"DEBUG_MODE": "true", "PORT": "9000"})
    def test_config_manager_env_vars(self):
        """Test config manager with environment variables."""
        # Create a minimal config manager for testing
        with patch('config.Path.exists', return_value=False):
            with patch('config.yaml.safe_load', return_value={"models": {}}):
                with patch('config.json.load', return_value={"servers": {}}):
                    manager = ConfigManager()
                    
                    assert manager.app_settings.debug_mode is True
                    assert manager.app_settings.port == 9000
    
    def test_config_manager_initialization(self):
        """Test config manager initialization."""
        with patch('config.Path.exists', return_value=False):
            with patch('config.yaml.safe_load', return_value={"models": {}}):
                with patch('config.json.load', return_value={"servers": {}}):
                    manager = ConfigManager()
                    
                    assert isinstance(manager.app_settings, AppSettings)
                    assert isinstance(manager.llm_config, LLMConfig)
                    assert isinstance(manager.mcp_config, MCPConfig)