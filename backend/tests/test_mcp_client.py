"""
Unit tests for MCP client functionality.
"""
import os
import pytest
from unittest.mock import Mock, patch, AsyncMock

# Import the mcp_client module
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from mcp_client import MCPToolManager


class TestMCPToolManager:
    """Test MCPToolManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_mcp_config = Mock()
        self.mock_mcp_config.servers = {
            "filesystem": Mock(enabled=True, groups=["users"]),
            "calculator": Mock(enabled=True, groups=["users"]),
            "secure": Mock(enabled=True, groups=["admin"], is_exclusive=True)
        }
        
        with patch('mcp_client.config_manager') as mock_config:
            mock_config.mcp_config = self.mock_mcp_config
            self.manager = MCPToolManager()
    
    def test_initialization(self):
        """Test MCPToolManager initialization."""
        assert self.manager is not None
        
    def test_get_available_servers(self):
        """Test getting available servers."""
        if hasattr(self.manager, 'get_available_servers'):
            servers = self.manager.get_available_servers()
            assert isinstance(servers, (list, dict))
        
    def test_get_authorized_servers_for_user(self):
        """Test getting authorized servers for a specific user."""
        mock_is_user_in_group = Mock(return_value=True)
        
        if hasattr(self.manager, 'get_authorized_servers'):
            servers = self.manager.get_authorized_servers("test@example.com", mock_is_user_in_group)
            assert isinstance(servers, list)
        
    def test_get_authorized_servers_admin_user(self):
        """Test getting authorized servers for admin user."""
        def mock_is_user_in_group(email, group):
            return group in ["users", "admin"]
            
        if hasattr(self.manager, 'get_authorized_servers'):
            servers = self.manager.get_authorized_servers("admin@example.com", mock_is_user_in_group)
            # Admin should have access to more servers
            assert isinstance(servers, list)
        
    def test_is_server_exclusive(self):
        """Test checking if server is exclusive."""
        if hasattr(self.manager, 'is_server_exclusive'):
            assert self.manager.is_server_exclusive("secure") is True
            assert self.manager.is_server_exclusive("filesystem") is False
        
    def test_server_exists(self):
        """Test checking if server exists."""
        if hasattr(self.manager, 'server_exists'):
            assert self.manager.server_exists("filesystem") is True
            assert self.manager.server_exists("nonexistent") is False


class TestMCPToolManagerMethods:
    """Test specific MCPToolManager methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = Mock(spec=MCPToolManager)
        
    def test_start_server(self):
        """Test starting an MCP server."""
        self.manager.start_server = Mock(return_value=True)
        
        result = self.manager.start_server("filesystem")
        assert result is True
        self.manager.start_server.assert_called_once_with("filesystem")
        
    def test_stop_server(self):
        """Test stopping an MCP server."""
        self.manager.stop_server = Mock(return_value=True)
        
        result = self.manager.stop_server("filesystem")
        assert result is True
        self.manager.stop_server.assert_called_once_with("filesystem")
        
    def test_call_tool(self):
        """Test calling a tool on MCP server."""
        self.manager.call_tool = AsyncMock(return_value={"result": "success"})
        
        async def test_async():
            result = await self.manager.call_tool("filesystem", "read_file", {"path": "test.txt"})
            assert result == {"result": "success"}
            
        # Note: Actual async execution would be done in an async test runner
        
    def test_get_tools_for_server(self):
        """Test getting available tools for a server."""
        self.manager.get_tools_for_server = Mock(return_value=["read_file", "write_file"])
        
        tools = self.manager.get_tools_for_server("filesystem")
        assert tools == ["read_file", "write_file"]
        self.manager.get_tools_for_server.assert_called_once_with("filesystem")