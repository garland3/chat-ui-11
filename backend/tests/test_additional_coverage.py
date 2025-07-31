"""
Additional unit tests for enhanced test coverage.
Testing core functionality with focused, minimal test cases.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from auth import is_user_in_group, get_user_from_header
from config import AppSettings, ModelConfig, MCPServerConfig


class TestAuthFunctionality:
    """Test authentication and authorization functions."""
    
    def test_is_user_in_group_authorized_user(self):
        """Test that authorized users return True."""
        result = is_user_in_group("test@test.com", "users")
        assert result is True
    
    def test_is_user_in_group_unauthorized_user(self):
        """Test that unauthorized users return False."""
        result = is_user_in_group("unknown@test.com", "admin")
        assert result is False
    
    def test_is_user_in_group_empty_group(self):
        """Test behavior with empty group."""
        result = is_user_in_group("test@test.com", "")
        assert result is False
    
    def test_get_user_from_header_valid_email(self):
        """Test extracting valid email from header."""
        result = get_user_from_header("user@example.com")
        assert result == "user@example.com"
    
    def test_get_user_from_header_none(self):
        """Test handling None header."""
        result = get_user_from_header(None)
        assert result is None
    
    def test_get_user_from_header_empty_string(self):
        """Test handling empty string header."""
        result = get_user_from_header("")
        assert result is None


class TestConfigurationClasses:
    """Test configuration data classes."""
    
    # def test_app_settings_default_initialization(self):
    #     """Test AppSettings with default values."""
    #     settings = AppSettings()
    #     assert settings.app_name == "Chat UI"
    #     assert settings.port == 8000
    #     assert settings.debug_mode is False
    
    def test_model_config_initialization(self):
        """Test ModelConfig with custom values."""
        config = ModelConfig(
            model_name="test-model",
            model_url="http://test-url.com",
            api_key="test-key"
        )
        assert config.model_name == "test-model"
        assert config.model_url == "http://test-url.com"
        assert config.api_key == "test-key"
    
    def test_mcp_server_config_with_groups(self):
        """Test MCPServerConfig with required groups."""
        config = MCPServerConfig(
            description="Test server",
            command=["python", "test.py"],
            groups=["admin", "users"]
        )
        assert config.description == "Test server"
        assert config.groups == ["admin", "users"]
    
    def test_mcp_server_config_exclusive_server(self):
        """Test MCPServerConfig with exclusive flag."""
        config = MCPServerConfig(
            description="exclusive-server",
            command=["python", "exclusive.py"],
            is_exclusive=True
        )
        assert config.is_exclusive is True