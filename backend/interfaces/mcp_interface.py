import logging

from managers.app_factory.app_factory import app_factory

logger = logging.getLogger(__name__)

from managers.auth.auth_manager import is_user_in_group


async def get_mcp_tools_info(current_user: str):
    """
    Fetches MCP tools information.
    This function encapsulates the logic for retrieving MCP tools and servers.
    """
    tools_info = []
    available_servers = []

    try:
        mcp_manager = await app_factory.get_mcp_manager()
        # Initialize tool_caller to ensure MCP manager is ready
        await app_factory.get_tool_caller()

        # Determine authorized servers using is_user_in_group for each server's groups
        authorized_servers = []
        for server_name in mcp_manager.get_available_servers():
            info = mcp_manager.get_server_info(server_name) or {}
            groups = info.get("groups", []) or []
            if not groups:
                authorized_servers.append(server_name)
                continue
            if any(is_user_in_group(current_user, g) for g in groups):
                authorized_servers.append(server_name)
        available_servers = authorized_servers

        # Get tools only from authorized servers
        authorized_tools = mcp_manager.get_tools_for_servers(authorized_servers)

        # Group tools by server
        server_tools = {}
        for tool in authorized_tools:
            if tool.server_name not in server_tools:
                server_tools[tool.server_name] = []
            server_tools[tool.server_name].append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "tags": list(tool.tags),
                }
            )

        # Build tools info for each authorized server
        for server_name, tools in server_tools.items():
            server_info = mcp_manager.get_server_info(server_name) or {}
            tools_info.append(
                {
                    "server": server_name,
                    "tools": [tool["name"] for tool in tools],
                    "tool_count": len(tools),
                    "tool_details": tools,
                    "description": server_info.get(
                        "description", f"{server_name} MCP tools"
                    ),
                    "is_exclusive": False,  # Deprecated, always False
                    "author": server_info.get("author", "MCP Server"),
                    "short_description": server_info.get(
                        "short_description", f"{server_name} tools"
                    ),
                    "help_email": server_info.get("help_email", ""),
                    "groups": server_info.get("groups", []),
                }
            )

    except Exception as e:
        logger.error(f"Error getting MCP tools: {e}")
        # Continue without tools if there's an error

    return tools_info, available_servers
