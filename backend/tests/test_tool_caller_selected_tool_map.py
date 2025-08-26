"""Tests for ToolCaller with selected_tool_map filtering."""

import pytest
from unittest.mock import Mock
from managers.tools.tool_caller import ToolCaller
from managers.mcp.mcp_manager import MCPManager


def make_tool_schema(name):
    return {"function": {"name": name}}


def test_tool_caller_filters_by_selected_tool_map():
    mock_mcp = Mock(spec=MCPManager)
    mock_mcp.get_available_servers.return_value = ['calculator', 'filesystem']
    mock_mcp.get_server_info.side_effect = lambda s: {"groups": []}
    # available tools for both servers
    tool_calc = Mock(); tool_calc.to_openai_schema.return_value = make_tool_schema('calculator_evaluate')
    tool_fs_list = Mock(); tool_fs_list.to_openai_schema.return_value = make_tool_schema('filesystem_list')
    tool_fs_read = Mock(); tool_fs_read.to_openai_schema.return_value = make_tool_schema('filesystem_read')
    mock_mcp.get_tools_for_servers.return_value = [tool_calc, tool_fs_list, tool_fs_read]

    tc = ToolCaller(mock_mcp)

    result = tc.get_authorized_tools_for_user(
        username='user',
        selected_tool_map={'calculator': ['evaluate'], 'filesystem': ['read']},
        is_user_in_group=lambda u, g: True
    )

    names = [t['function']['name'] for t in result]
    assert set(names) == {'calculator_evaluate', 'filesystem_read'}
