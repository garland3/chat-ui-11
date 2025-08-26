"""Unit tests for MCP interface auth alignment with is_user_in_group."""

import pytest

from interfaces.mcp_interface import get_mcp_tools_info


@pytest.mark.asyncio
async def test_get_mcp_tools_info_uses_is_user_in_group(monkeypatch):
    # Mock app_factory and mcp_manager
    class MockMCPManager:
        def get_available_servers(self):
            return ["calculator", "filesystem"]

        def get_server_info(self, name):
            return (
                {"groups": ["engineering"]} if name == "filesystem" else {"groups": []}
            )

        def get_tools_for_servers(self, servers):
            class Tool:
                def __init__(self, server, name):
                    self.server_name = server
                    self.name = name
                    self.description = ""
                    self.tags = set()

            tools = []
            for s in servers:
                tools.append(Tool(s, "evaluate"))
            return tools

    mock_mcp_manager = MockMCPManager()

    class MockAppFactory:
        async def get_mcp_manager(self):
            return mock_mcp_manager

        async def get_tool_caller(self):
            return None

    # Patch app_factory
    monkeypatch.setattr("interfaces.mcp_interface.app_factory", MockAppFactory())

    # Patch is_user_in_group: user has engineering
    monkeypatch.setattr(
        "interfaces.mcp_interface.is_user_in_group", lambda u, g: g == "engineering"
    )

    tools_info, servers = await get_mcp_tools_info("user@example.com")
    # Should authorize both public (calculator) and engineering (filesystem)
    assert set(servers) == {"calculator", "filesystem"}
    # tools_info should contain entries for both
    assert {g["server"] for g in tools_info} == {"calculator", "filesystem"}
