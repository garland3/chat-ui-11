"""Test for config route admin group functionality."""

from unittest.mock import patch, Mock
import pytest

from routes.config_route import get_config


@pytest.mark.asyncio
@patch("routes.config_route.get_mcp_tools_info")
@patch("routes.config_route.get_mcp_prompts_info")
@patch("routes.config_route.app_factory")
@patch("routes.config_route.is_user_in_group")
async def test_config_route_includes_admin_group_status(
    mock_is_user_in_group,
    mock_app_factory,
    mock_get_mcp_prompts_info,
    mock_get_mcp_tools_info,
):
    """Test that config route includes is_in_admin_group field."""
    # Mock config manager
    mock_config_manager = Mock()
    mock_app_settings = Mock()
    mock_app_settings.app_name = "Test App"
    mock_app_settings.feature_tools_enabled = False
    mock_app_settings.admin_group = "admin_group"
    mock_app_settings.feature_workspaces_enabled = False
    mock_app_settings.feature_rag_enabled = False
    mock_app_settings.feature_marketplace_enabled = False
    mock_app_settings.feature_files_panel_enabled = False
    mock_app_settings.feature_chat_history_enabled = False

    mock_llm_config = Mock()
    mock_model1 = Mock()
    mock_model1.model_name = "gpt-4"
    mock_model2 = Mock()
    mock_model2.model_name = "claude-3"
    mock_llm_config.models = [mock_model1, mock_model2]

    mock_config_manager.app_settings = mock_app_settings
    mock_config_manager.llm_config = mock_llm_config
    mock_app_factory.get_config_manager.return_value = mock_config_manager

    # Mock user is in admin group
    mock_is_user_in_group.return_value = True

    # Mock MCP functions (not called when tools disabled)
    mock_get_mcp_tools_info.return_value = ([], [])
    mock_get_mcp_prompts_info.return_value = ([], [])

    result = await get_config("test_user")

    # Verify is_in_admin_group is included and correct
    assert "is_in_admin_group" in result
    assert result["is_in_admin_group"] is True
    assert result["user"] == "test_user"
    assert result["app_name"] == "Test App"
    assert result["models"] == ["gpt-4", "claude-3"]

    # Verify is_user_in_group was called with correct parameters
    mock_is_user_in_group.assert_called_once_with("test_user", "admin_group")


@pytest.mark.asyncio
@patch("routes.config_route.get_mcp_tools_info")
@patch("routes.config_route.get_mcp_prompts_info")
@patch("routes.config_route.app_factory")
@patch("routes.config_route.is_user_in_group")
async def test_config_route_non_admin_user(
    mock_is_user_in_group,
    mock_app_factory,
    mock_get_mcp_prompts_info,
    mock_get_mcp_tools_info,
):
    """Test that non-admin users get is_in_admin_group: false."""
    # Mock config manager
    mock_config_manager = Mock()
    mock_app_settings = Mock()
    mock_app_settings.app_name = "Test App"
    mock_app_settings.feature_tools_enabled = False
    mock_app_settings.admin_group = "admin_group"
    mock_app_settings.feature_workspaces_enabled = False
    mock_app_settings.feature_rag_enabled = False
    mock_app_settings.feature_marketplace_enabled = False
    mock_app_settings.feature_files_panel_enabled = False
    mock_app_settings.feature_chat_history_enabled = False

    mock_llm_config = Mock()
    mock_llm_config.models = []

    mock_config_manager.app_settings = mock_app_settings
    mock_config_manager.llm_config = mock_llm_config
    mock_app_factory.get_config_manager.return_value = mock_config_manager

    # Mock user is NOT in admin group
    mock_is_user_in_group.return_value = False

    # Mock MCP functions
    mock_get_mcp_tools_info.return_value = ([], [])
    mock_get_mcp_prompts_info.return_value = ([], [])

    result = await get_config("regular_user")

    # Verify is_in_admin_group is false for non-admin user
    assert "is_in_admin_group" in result
    assert result["is_in_admin_group"] is False
    assert result["user"] == "regular_user"

    # Verify is_user_in_group was called with correct parameters
    mock_is_user_in_group.assert_called_once_with("regular_user", "admin_group")
