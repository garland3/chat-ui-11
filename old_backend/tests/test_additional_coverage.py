"""
Additional unit tests for enhanced test coverage.
Testing core functionality with focused, minimal test cases.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from auth import is_user_in_group, get_user_from_header
from config import AppSettings, ModelConfig, MCPServerConfig
from mcp_client import MCPToolManager


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


class TestMCPTransportDetection:
    """Test MCP transport detection logic."""
    
    def test_explicit_transport_http(self):
        """Test explicit transport field takes priority."""
        manager = MCPToolManager()
        config = {
            "url": "my-service:8080/mcp",  # No protocol
            "transport": "http",  # Explicit transport
            "type": "stdio"  # Should be ignored
        }
        result = manager._determine_transport_type(config)
        assert result == "http"
    
    def test_explicit_transport_sse(self):
        """Test explicit SSE transport."""
        manager = MCPToolManager()
        config = {
            "url": "http://example.com/mcp",  # Has protocol
            "transport": "sse"  # Explicit SSE overrides URL detection
        }
        result = manager._determine_transport_type(config)
        assert result == "sse"
    
    def test_explicit_transport_stdio(self):
        """Test explicit STDIO transport."""
        manager = MCPToolManager()
        config = {
            "url": "http://example.com/mcp",  # Has URL
            "transport": "stdio"  # Explicit STDIO overrides URL
        }
        result = manager._determine_transport_type(config)
        assert result == "stdio"
    
    def test_auto_detect_http_from_url(self):
        """Test auto-detection of HTTP from URL with protocol."""
        manager = MCPToolManager()
        config = {"url": "http://example.com/mcp"}
        result = manager._determine_transport_type(config)
        assert result == "http"
    
    def test_auto_detect_https_from_url(self):
        """Test auto-detection of HTTP from HTTPS URL."""
        manager = MCPToolManager()
        config = {"url": "https://example.com/mcp"}
        result = manager._determine_transport_type(config)
        assert result == "http"
    
    def test_auto_detect_sse_from_url(self):
        """Test auto-detection of SSE from URL ending with /sse."""
        manager = MCPToolManager()
        config = {"url": "http://example.com/sse"}
        result = manager._determine_transport_type(config)
        assert result == "sse"
    
    def test_url_without_protocol_defaults_to_http(self):
        """Test URL without protocol defaults to HTTP."""
        manager = MCPToolManager()
        config = {"url": "my-service:8080/mcp"}
        result = manager._determine_transport_type(config)
        assert result == "http"
    
    def test_url_without_protocol_uses_type_field(self):
        """Test URL without protocol uses type field if it's http/sse."""
        manager = MCPToolManager()
        config = {
            "url": "my-service:8080/mcp",
            "type": "sse"
        }
        result = manager._determine_transport_type(config)
        assert result == "sse"
    
    def test_url_without_protocol_ignores_invalid_type(self):
        """Test URL without protocol ignores invalid type field."""
        manager = MCPToolManager()
        config = {
            "url": "my-service:8080/mcp",
            "type": "invalid"
        }
        result = manager._determine_transport_type(config)
        assert result == "http"  # Should default to http
    
    def test_auto_detect_stdio_from_command(self):
        """Test auto-detection of STDIO from command."""
        manager = MCPToolManager()
        config = {"command": ["python", "server.py"]}
        result = manager._determine_transport_type(config)
        assert result == "stdio"
    
    def test_fallback_to_type_field(self):
        """Test fallback to type field when no URL or command."""
        manager = MCPToolManager()
        config = {"type": "http"}
        result = manager._determine_transport_type(config)
        assert result == "http"
    
    def test_fallback_to_default_stdio(self):
        """Test fallback to default stdio when no indicators."""
        manager = MCPToolManager()
        config = {}
        result = manager._determine_transport_type(config)
        assert result == "stdio"
    
    def test_command_overrides_url(self):
        """Test that command presence overrides URL for STDIO detection."""
        manager = MCPToolManager()
        config = {
            "url": "http://example.com/mcp",
            "command": ["python", "server.py"]
        }
        result = manager._determine_transport_type(config)
        assert result == "stdio"  # Command should win without explicit transport
    
    def test_k8s_service_example(self):
        """Test typical K8s service configuration."""
        manager = MCPToolManager()
        config = {
            "url": "my-mcp-service.default.svc.cluster.local:8080/mcp",
            "transport": "http",
            "groups": ["users"]
        }
        result = manager._determine_transport_type(config)
        assert result == "http"
    
    def test_new_transport_field_in_config_schema(self):
        """Test that the new transport field is properly defined in MCPServerConfig."""
        config = MCPServerConfig(
            description="Test server",
            transport="http",
            url="my-service:8080/mcp"
        )
        assert config.transport == "http"
        assert config.url == "my-service:8080/mcp"
        assert config.type == "stdio"  # Default value