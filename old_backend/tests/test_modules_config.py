"""
Comprehensive tests for the Config module.
"""
import os
import sys
import tempfile
import json
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from modules.config import (
    ConfigManager, 
    AppSettings, 
    LLMConfig, 
    MCPConfig, 
    ModelConfig,
    MCPServerConfig,
    config_manager,
    get_app_settings,
    get_llm_config,
    get_mcp_config
)


class TestConfigManager:
    """Test ConfigManager class."""
    
    def test_config_manager_initialization(self):
        """Test that ConfigManager initializes correctly."""
        manager = ConfigManager()
        assert manager._app_settings is None
        assert manager._llm_config is None
        assert manager._mcp_config is None
    
    def test_config_manager_with_custom_root(self):
        """Test ConfigManager with custom backend root."""
        custom_root = Path("/tmp/test_backend")
        manager = ConfigManager(backend_root=custom_root)
        assert manager._backend_root == custom_root
    
    def test_search_paths(self):
        """Test configuration file search path generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend_root = Path(tmpdir)
            manager = ConfigManager(backend_root=backend_root)
            
            search_paths = manager._search_paths("test.yml")
            
            # Should include admin and regular config paths
            assert any("configfilesadmin" in str(path) for path in search_paths)
            assert any("configfiles" in str(path) for path in search_paths)
    
    def test_load_file_with_error_handling_yaml(self):
        """Test YAML file loading with error handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "test.yml"
            test_data = {"models": {"test-model": {"model_name": "test"}}}
            
            with open(yaml_file, 'w') as f:
                yaml.dump(test_data, f)
            
            backend_root = Path(tmpdir).parent
            manager = ConfigManager(backend_root=backend_root)
            
            result = manager._load_file_with_error_handling([yaml_file], "YAML")
            assert result == test_data
    
    def test_load_file_with_error_handling_json(self):
        """Test JSON file loading with error handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "test.json"
            test_data = {"server1": {"enabled": True}}
            
            with open(json_file, 'w') as f:
                json.dump(test_data, f)
            
            backend_root = Path(tmpdir).parent
            manager = ConfigManager(backend_root=backend_root)
            
            result = manager._load_file_with_error_handling([json_file], "JSON")
            assert result == test_data
    
    def test_load_file_nonexistent(self):
        """Test loading non-existent file returns None."""
        manager = ConfigManager()
        result = manager._load_file_with_error_handling([Path("/nonexistent/file.yml")], "YAML")
        assert result is None
    
    def test_load_file_invalid_format(self):
        """Test loading file with invalid format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_file = Path(tmpdir) / "invalid.yml"
            
            # Write invalid YAML
            with open(invalid_file, 'w') as f:
                f.write("invalid: yaml: content: [")
            
            backend_root = Path(tmpdir).parent
            manager = ConfigManager(backend_root=backend_root)
            
            result = manager._load_file_with_error_handling([invalid_file], "YAML")
            assert result is None
    
    def test_app_settings_property(self):
        """Test app_settings property returns AppSettings instance."""
        manager = ConfigManager()
        settings = manager.app_settings
        assert isinstance(settings, AppSettings)
    
    def test_app_settings_cached(self):
        """Test that app_settings is cached."""
        manager = ConfigManager()
        settings1 = manager.app_settings
        settings2 = manager.app_settings
        assert settings1 is settings2
    
    def test_llm_config_empty(self):
        """Test LLM config with no configuration file."""
        manager = ConfigManager()
        llm_config = manager.llm_config
        assert isinstance(llm_config, LLMConfig)
        assert len(llm_config.models) == 0
    
    def test_mcp_config_empty(self):
        """Test MCP config with no configuration file."""
        manager = ConfigManager()
        mcp_config = manager.mcp_config
        assert isinstance(mcp_config, MCPConfig)
        assert len(mcp_config.servers) == 0


class TestAppSettings:
    """Test AppSettings class."""
    
    def test_app_settings_defaults(self):
        """Test AppSettings default values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = AppSettings()
            assert settings.app_name == "Chat UI"
            assert settings.port == 8000
            assert settings.debug_mode == False
            assert settings.log_level == "INFO"
    
    def test_app_settings_from_env(self):
        """Test AppSettings loading from environment variables."""
        env_vars = {
            "APP_NAME": "Test Chat",
            "PORT": "9000",
            "DEBUG_MODE": "true",
            "LOG_LEVEL": "DEBUG"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = AppSettings()
            assert settings.app_name == "Test Chat"
            assert settings.port == 9000
            assert settings.debug_mode == True
            assert settings.log_level == "DEBUG"
    
    def test_feature_flags(self):
        """Test feature flag settings."""
        settings = AppSettings()
        assert hasattr(settings, 'feature_workspaces_enabled')
        assert hasattr(settings, 'feature_rag_enabled')
        assert hasattr(settings, 'feature_tools_enabled')
    
    def test_agent_mode_backward_compatibility(self):
        """Test backward compatibility for agent_mode_available."""
        settings = AppSettings()
        assert settings.agent_mode_available == settings.feature_agent_mode_available


class TestLLMConfig:
    """Test LLMConfig class."""
    
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
        assert isinstance(config.models["gpt-4"], ModelConfig)
    
    def test_model_config_validation(self):
        """Test ModelConfig validation."""
        model_data = {
            "model_name": "test-model",
            "model_url": "https://api.test.com",
            "api_key": "test-key",
            "max_tokens": 5000,
            "temperature": 0.8
        }
        model = ModelConfig(**model_data)
        assert model.model_name == "test-model"
        assert model.max_tokens == 5000
        assert model.temperature == 0.8


class TestMCPConfig:
    """Test MCPConfig class."""
    
    def test_mcp_config_empty(self):
        """Test empty MCP configuration."""
        config = MCPConfig()
        assert len(config.servers) == 0
    
    def test_mcp_config_with_servers(self):
        """Test MCP configuration with servers."""
        servers_data = {
            "servers": {
                "test-server": {
                    "enabled": True,
                    "groups": ["admin"],
                    "command": ["python", "server.py"]
                }
            }
        }
        config = MCPConfig(**servers_data)
        assert len(config.servers) == 1
        assert "test-server" in config.servers
        assert isinstance(config.servers["test-server"], MCPServerConfig)
    
    def test_mcp_server_config_defaults(self):
        """Test MCPServerConfig default values."""
        server = MCPServerConfig()
        assert server.enabled == True
        assert server.is_exclusive == False
        assert server.type == "stdio"
        assert server.groups == []


class TestGlobalConfigManager:
    """Test global config_manager instance."""
    
    def test_global_config_manager_exists(self):
        """Test that global config_manager exists."""
        assert config_manager is not None
        assert isinstance(config_manager, ConfigManager)
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        app_settings = get_app_settings()
        assert isinstance(app_settings, AppSettings)
        
        llm_config = get_llm_config()
        assert isinstance(llm_config, LLMConfig)
        
        mcp_config = get_mcp_config()
        assert isinstance(mcp_config, MCPConfig)
    
    def test_config_validation(self):
        """Test configuration validation."""
        manager = ConfigManager()
        status = manager.validate_config()
        
        assert isinstance(status, dict)
        assert "app_settings" in status
        assert "llm_config" in status
        assert "mcp_config" in status
        assert isinstance(status["app_settings"], bool)
    
    def test_config_reload(self):
        """Test configuration reload."""
        manager = ConfigManager()
        
        # Access configs to cache them
        _ = manager.app_settings
        _ = manager.llm_config
        _ = manager.mcp_config
        
        # Reload should clear cache
        manager.reload_configs()
        
        assert manager._app_settings is None
        assert manager._llm_config is None
        assert manager._mcp_config is None