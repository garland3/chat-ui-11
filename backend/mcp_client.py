"""FastMCP client for connecting to MCP servers and managing tools."""

import logging
import os
from typing import Dict, List, Any

from fastmcp import Client
from config import config_manager
from auth_utils import create_authorization_manager

logger = logging.getLogger(__name__)


class MCPToolManager:
    """Manager for MCP servers and their tools."""
    
    def __init__(self, config_path: str = "mcp.json"):
        self.config_path = config_path
        mcp_config = config_manager.mcp_config
        self.servers_config = {name: server.model_dump() for name, server in mcp_config.servers.items()}
        self.clients = {}
        self.available_tools = {}
        
    
    async def initialize_clients(self):
        """Initialize FastMCP clients for all configured servers."""
        for server_name, config in self.servers_config.items():
            try:
                # TODO: allow different mcp types. 
                # Create client based on server type
                server_path = f"mcp/{server_name}/main.py"
                logger.debug(f"Attempting to initialize {server_name} at path: {server_path}")
                if os.path.exists(server_path):
                    logger.debug(f"Server script exists for {server_name}, creating client...")
                    client = Client(server_path)
                    self.clients[server_name] = client
                    logger.info(f"Created MCP client for {server_name}")
                    logger.debug(f"Successfully created client for {server_name}")
                else:
                    logger.error(f"MCP server script not found: {server_path}", exc_info=True)
            except Exception as e:
                logger.error(f"Error creating client for {server_name}: {e}", exc_info=True)
    
    async def discover_tools(self):
        """Discover tools from all MCP servers."""
        self.available_tools = {}

        
        for server_name, client in self.clients.items():
            logger.debug(f"Attempting to discover tools from {server_name}")
            try:
                logger.debug(f"Opening client connection for {server_name}")
                async with client:
                    logger.debug(f"Client connected for {server_name}, listing tools...")
                    tools = await client.list_tools()
                    logger.debug(f"Got {len(tools)} tools from {server_name}: {[tool.name for tool in tools]}")
                    self.available_tools[server_name] = {
                        'tools': tools,
                        'config': self.servers_config[server_name]
                    }
                    logger.info(f"Discovered {len(tools)} tools from {server_name}")
                    logger.debug(f"Successfully stored tools for {server_name}")
            except Exception as e:
                logger.error(f"Error discovering tools from {server_name}: {e}", exc_info=True)
                self.available_tools[server_name] = {
                    'tools': [],
                    'config': self.servers_config[server_name]
                }
                logger.debug(f"Set empty tools list for failed server {server_name}")
    
    def get_server_groups(self, server_name: str) -> List[str]:
        """Get required groups for a server."""
        if server_name in self.servers_config:
            return self.servers_config[server_name].get("groups", [])
        return []
    
    def is_server_exclusive(self, server_name: str) -> bool:
        """Check if server is exclusive (cannot run with others)."""
        if server_name in self.servers_config:
            return self.servers_config[server_name].get("is_exclusive", False)
        return False
    
    def get_available_servers(self) -> List[str]:
        """Get list of configured servers."""
        return list(self.servers_config.keys())
    
    def get_tools_for_servers(self, server_names: List[str]) -> Dict[str, Any]:
        """Get tools and their schemas for selected servers."""
        tools_schema = []
        server_tool_mapping = {}
        
        for server_name in server_names:
            # Handle canvas pseudo-tool
            if server_name == "canvas":
                canvas_tool_schema = {
                    "type": "function",
                    "function": {
                        "name": "canvas_canvas",
                        "description": "Display final rendered content in a visual canvas panel. Use this for: 1) Complete code (not code discussions), 2) Final reports/documents (not report discussions), 3) Data visualizations, 4) Any polished content that should be viewed separately from the conversation. Put the actual content in the canvas, keep discussions in chat.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "The content to display in the canvas. Can be markdown, code, or plain text."
                                }
                            },
                            "required": ["content"]
                        }
                    }
                }
                tools_schema.append(canvas_tool_schema)
                server_tool_mapping["canvas_canvas"] = {
                    'server': 'canvas',
                    'tool_name': 'canvas'
                }
            elif server_name in self.available_tools:
                server_tools = self.available_tools[server_name]['tools']
                for tool in server_tools:
                    # Convert MCP tool format to OpenAI function calling format
                    tool_schema = {
                        "type": "function",
                        "function": {
                            "name": f"{server_name}_{tool.name}",
                            "description": tool.description or '',
                            "parameters": tool.inputSchema or {}
                        }
                    }
                    # log the server -> function name
                    logger.info(f"Adding tool {tool.name} for server {server_name} ")
                    tools_schema.append(tool_schema)
                    server_tool_mapping[f"{server_name}_{tool.name}"] = {
                        'server': server_name,
                        'tool_name': tool.name
                    }
        
        return {
            'tools': tools_schema,
            'mapping': server_tool_mapping
        }
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a specific tool on an MCP server."""
        if server_name not in self.clients:
            raise ValueError(f"No client available for server: {server_name}")
        
        client = self.clients[server_name]
        try:
            async with client:
                result = await client.call_tool(tool_name, arguments)
                logger.info(f"Successfully called {tool_name} on {server_name}")
                return result
        except Exception as e:
            logger.error(f"Error calling {tool_name} on {server_name}: {e}")
            raise
    
    def get_authorized_servers(self, user_email: str, auth_check_func) -> List[str]:
        """Get list of servers the user is authorized to use."""
        try:
            auth_manager = create_authorization_manager(auth_check_func)
            return auth_manager.filter_authorized_servers(
                user_email, 
                self.servers_config, 
                self.get_server_groups
            )
        except Exception as e:
            logger.error(f"Error getting authorized servers for {user_email}: {e}", exc_info=True)
            return []
    
    async def cleanup(self):
        """Cleanup all clients."""
        logger.info("Cleaning up MCP clients")
        # FastMCP clients handle cleanup automatically with context managers