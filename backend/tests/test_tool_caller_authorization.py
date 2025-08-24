"""Unit tests for ToolCaller authorization logic - critical security tests."""

import pytest
from unittest.mock import Mock, MagicMock
from managers.tools.tool_caller import ToolCaller
from managers.mcp.mcp_manager import MCPManager


class TestToolCallerAuthorization:
    """Test suite for ToolCaller authorization logic with security focus."""
    
    @pytest.fixture
    def mock_mcp_manager(self):
        """Create mock MCP manager for testing."""
        mock = Mock(spec=MCPManager)
        mock.get_available_servers.return_value = ["server1", "server2", "server3"]
        
        # Server info with different group requirements
        server_info_map = {
            "server1": {"groups": ["admin_group"]},  # Restricted server
            "server2": {"groups": ["test_group"]},   # Different restricted server
            "server3": {"groups": []},               # Public server
        }
        mock.get_server_info.side_effect = lambda name: server_info_map.get(name)
        
        # Mock tools for servers
        mock.get_tools_for_servers.return_value = []
        
        return mock
    
    @pytest.fixture
    def tool_caller(self, mock_mcp_manager):
        """Create ToolCaller instance for testing."""
        return ToolCaller(mock_mcp_manager)
    
    def test_authorization_blocks_unauthorized_user_from_restricted_servers(self, tool_caller):
        """SECURITY TEST: User without required groups cannot access restricted servers."""
        def unauthorized_user_check(username, group):
            # User has no groups - should be blocked from all restricted servers
            return False
        
        result = tool_caller.get_authorized_tools_for_user(
            username="unauthorized_user",
            selected_tools=["any_tool"],
            is_user_in_group=unauthorized_user_check
        )
        
        # Should only get tools from public servers (server3)
        tool_caller.mcp_manager.get_tools_for_servers.assert_called_once_with(["server3"])
    
    def test_authorization_allows_admin_access_to_admin_servers(self, tool_caller):
        """SECURITY TEST: Admin user can access admin-restricted servers."""
        def admin_user_check(username, group):
            # Admin user has admin_group access
            return group == "admin_group"
        
        result = tool_caller.get_authorized_tools_for_user(
            username="admin_user",
            selected_tools=["admin_tool"],
            is_user_in_group=admin_user_check
        )
        
        # Should get tools from admin server (server1) and public server (server3)
        expected_servers = ["server1", "server3"]
        tool_caller.mcp_manager.get_tools_for_servers.assert_called_once_with(expected_servers)
    
    def test_authorization_prevents_privilege_escalation_attempts(self, tool_caller):
        """SECURITY TEST: User cannot access servers outside their groups."""
        def test_user_check(username, group):
            # Test user only has test_group, NOT admin_group
            return group == "test_group"
        
        result = tool_caller.get_authorized_tools_for_user(
            username="test_user",
            selected_tools=["admin_tool", "test_tool"],  # Trying to access admin tools
            is_user_in_group=test_user_check
        )
        
        # Should only get tools from test server (server2) and public server (server3)
        # NOT from admin server (server1)
        expected_servers = ["server2", "server3"]
        tool_caller.mcp_manager.get_tools_for_servers.assert_called_once_with(expected_servers)
    
    def test_tool_filtering_works_with_authorization(self, tool_caller):
        """Test that tool filtering works correctly after authorization."""
        # Mock tools returned from authorized servers
        mock_tools = [
            {"function": {"name": "allowed_tool"}},
            {"function": {"name": "another_tool"}},
        ]
        tool_caller.mcp_manager.get_tools_for_servers.return_value = mock_tools
        
        def test_user_check(username, group):
            return group == "test_group"
        
        result = tool_caller.get_authorized_tools_for_user(
            username="test_user",
            selected_tools=["allowed_tool"],  # Only request one specific tool
            is_user_in_group=test_user_check
        )
        
        # Should return only the requested tool
        assert len(result) == 1
        assert result[0]["function"]["name"] == "allowed_tool"
    
    def test_empty_tool_selection_returns_all_authorized_tools(self, tool_caller):
        """Test that empty selection returns all tools user is authorized for."""
        mock_tools = [
            {"function": {"name": "tool1"}},
            {"function": {"name": "tool2"}},
        ]
        tool_caller.mcp_manager.get_tools_for_servers.return_value = mock_tools
        
        def test_user_check(username, group):
            return group == "test_group"
        
        result = tool_caller.get_authorized_tools_for_user(
            username="test_user",
            selected_tools=[],  # No specific tools requested
            is_user_in_group=test_user_check
        )
        
        # Should return all authorized tools
        assert len(result) == 2
        assert result == mock_tools