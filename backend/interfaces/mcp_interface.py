import logging
from pathlib import Path
import os

from managers.app_factory.app_factory import app_factory

logger = logging.getLogger(__name__)

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
        
        # For now, assume all users are in the "users" group
        # TODO: Implement proper user group resolution and authorization
        user_groups = ["users"]
        
        # Get authorized servers for the user
        # NOTE: The original code did not use current_user here, but it's good practice to pass it.
        # If mcp_manager.get_authorized_servers requires it, this change is necessary.
        # For now, assuming it might be used internally or for future extensions.
        authorized_servers = mcp_manager.get_authorized_servers(user_groups) # Potentially pass current_user here if needed by the manager
        available_servers = authorized_servers
        
        # Get tools only from authorized servers
        authorized_tools = mcp_manager.get_tools_for_servers(authorized_servers)
        
        # Group tools by server
        server_tools = {}
        for tool in authorized_tools:
            if tool.server_name not in server_tools:
                server_tools[tool.server_name] = []
            server_tools[tool.server_name].append({
                'name': tool.name,
                'description': tool.description,
                'tags': list(tool.tags)
            })
        
        # Build tools info for each authorized server
        for server_name, tools in server_tools.items():
            server_info = mcp_manager.get_server_info(server_name)
            tools_info.append({
                'server': server_name,
                'tools': [tool['name'] for tool in tools],
                'tool_count': len(tools),
                'tool_details': tools,
                'description': server_info['description'] if server_info else f'{server_name} MCP tools',
                'is_exclusive': False,  # Deprecated, always False
                'author': server_info['author'] if server_info else 'MCP Server',
                'short_description': server_info['short_description'] if server_info else f'{server_name} tools',
                'help_email': server_info['help_email'] if server_info else '',
                'groups': server_info['groups'] if server_info else []
            })
            
    except Exception as e:
        logger.error(f"Error getting MCP tools: {e}")
        # Continue without tools if there's an error

    return tools_info, available_servers
