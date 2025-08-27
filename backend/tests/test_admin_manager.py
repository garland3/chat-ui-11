"""Tests for admin manager MCP operations and dashboard functionality."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from managers.admin.admin_manager import AdminManager, get_admin_group_name


@pytest.mark.asyncio
@patch("managers.admin.admin_manager.app_factory")
async def test_reload_mcp_servers_success(mock_app_factory):
    """Test reload_mcp_servers successfully reloads and reports MCP server status."""
    # Mock MCP manager and its methods (sync methods, not async)
    mock_mcp = Mock()
    mock_mcp.cleanup = AsyncMock()  # These are async
    mock_mcp.initialize = AsyncMock()  # These are async
    mock_mcp.get_available_servers.return_value = ["server1", "server2"]  # This is sync
    
    # Mock tools with server names
    mock_tool1 = Mock()
    mock_tool1.server_name = "server1"
    mock_tool2 = Mock() 
    mock_tool2.server_name = "server1"
    mock_tool3 = Mock()
    mock_tool3.server_name = "server2"
    mock_mcp.get_available_tools.return_value = [mock_tool1, mock_tool2, mock_tool3]  # This is sync
    
    # Mock prompts with server names
    mock_prompt1 = Mock()
    mock_prompt1.server_name = "server2"
    mock_mcp.get_available_prompts.return_value = [mock_prompt1]  # This is sync
    
    # Mock app_factory.get_mcp_manager as an async function that returns the mock
    mock_app_factory.get_mcp_manager = AsyncMock(return_value=mock_mcp)
    
    result = await AdminManager.reload_mcp_servers("test_admin")
    
    # Should call cleanup and initialize
    mock_mcp.cleanup.assert_called_once()
    mock_mcp.initialize.assert_called_once()
    
    # Should return proper response structure
    assert result.message == "MCP servers reloaded"
    assert result.servers == ["server1", "server2"]
    assert result.tool_counts["server1"] == 2  # 2 tools
    assert result.tool_counts["server2"] == 1  # 1 tool
    assert result.prompt_counts["server1"] == 0  # 0 prompts
    assert result.prompt_counts["server2"] == 1  # 1 prompt
    assert result.reloaded_by == "test_admin"


@pytest.mark.asyncio
@patch("managers.admin.admin_manager.app_factory")
async def test_reload_mcp_servers_handles_errors(mock_app_factory):
    """Test reload_mcp_servers raises HTTPException on MCP manager errors."""
    mock_app_factory.get_mcp_manager = AsyncMock(side_effect=Exception("MCP connection failed"))
    
    with pytest.raises(HTTPException) as exc_info:
        await AdminManager.reload_mcp_servers("test_admin")
    
    assert exc_info.value.status_code == 500
    assert "MCP connection failed" in str(exc_info.value.detail)


def test_get_admin_dashboard_info():
    """Test get_admin_dashboard_info returns complete dashboard information."""
    result = AdminManager.get_admin_dashboard_info("admin_user")
    
    # Should return structured dashboard info
    assert result["message"] == "Admin Dashboard"
    assert result["user"] == "admin_user"
    assert isinstance(result["available_endpoints"], list)
    
    # Should include all expected endpoints
    expected_endpoints = [
        "/admin/banners",
        "/admin/config/view", 
        "/admin/llm-config",
        "/admin/mcp-config",
        "/admin/mcp/reload",
        "/admin/logs/viewer",
        "/admin/logs/clear",
        "/admin/logs/download"
    ]
    
    for endpoint in expected_endpoints:
        assert endpoint in result["available_endpoints"]
    
    # Should have exactly 8 endpoints (no extras)
    assert len(result["available_endpoints"]) == 8