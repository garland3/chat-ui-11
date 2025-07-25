"""FastMCP client for connecting to MCP servers and managing tools."""

import logging
import os
from typing import Dict, List, Any

from fastmcp import Client
from config_utils import load_mcp_config

logger = logging.getLogger(__name__)


class MCPToolManager:
    """Manager for MCP servers and their tools."""
    
    def __init__(self, config_path: str = "mcp.json"):
        self.config_path = config_path
        self.servers_config = load_mcp_config(config_path)
        self.clients = {}
        self.available_tools = {}
        
    
    async def initialize_clients(self):
        """Initialize FastMCP clients for all configured servers."""
        for server_name, config in self.servers_config.items():
            try:
                # TODO: allow different mcp types. 
                # Create client based on server type
                server_path = f"mcp/{server_name}/main.py"
                print(f"[DEBUG] Attempting to initialize {server_name} at path: {server_path}")
                if os.path.exists(server_path):
                    print(f"[DEBUG] Server script exists for {server_name}, creating client...")
                    client = Client(server_path)
                    self.clients[server_name] = client
                    logger.info(f"Created MCP client for {server_name}")
                    print(f"[DEBUG] Successfully created client for {server_name}")
                else:
                    logger.error(f"MCP server script not found: {server_path}")
                    print(f"[DEBUG] Server script NOT found: {server_path}")
                    # add traceback
                    import traceback
                    print(traceback.format_exc())
            except Exception as e:
                logger.error(f"Error creating client for {server_name}: {e}")
                import traceback
                print(f"[DEBUG] Full traceback for {server_name}:")
                print(traceback.format_exc())
    
    async def discover_tools(self):
        """Discover tools from all MCP servers."""
        self.available_tools = {}

        
        for server_name, client in self.clients.items():
            print(f"[DEBUG] Attempting to discover tools from {server_name}")
            try:
                print(f"[DEBUG] Opening client connection for {server_name}")
                async with client:
                    print(f"[DEBUG] Client connected for {server_name}, listing tools...")
                    tools = await client.list_tools()
                    print(f"[DEBUG] Got {len(tools)} tools from {server_name}: {[tool.name for tool in tools]}")
                    self.available_tools[server_name] = {
                        'tools': tools,
                        'config': self.servers_config[server_name]
                    }
                    logger.info(f"Discovered {len(tools)} tools from {server_name}")
                    print(f"[DEBUG] Successfully stored tools for {server_name}")
            except Exception as e:
                logger.error(f"Error discovering tools from {server_name}: {e}")
                # use traceback
                import traceback
                print(f"[DEBUG] Full traceback for {server_name} tool discovery:")
                print(traceback.format_exc())
                self.available_tools[server_name] = {
                    'tools': [],
                    'config': self.servers_config[server_name]
                }
                print(f"[DEBUG] Set empty tools list for failed server {server_name}")
    
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
        authorized = []
        available_servers = self.get_available_servers()
        
        logger.info(f"Checking authorization for user {user_email} across {len(available_servers)} servers: {available_servers}")
        
        for server_name in available_servers:
            required_groups = self.get_server_groups(server_name)
            logger.info(f"Server {server_name} requires groups: {required_groups}")
            
            if not required_groups:  # No restrictions
                logger.info(f"Server {server_name} has no group restrictions - adding to authorized list")
                authorized.append(server_name)
            else:
                # Check if user is in any required group
                user_authorized = False
                for group in required_groups:
                    is_in_group = auth_check_func(user_email, group)
                    logger.info(f"User {user_email} in group '{group}': {is_in_group}")
                    if is_in_group:
                        logger.info(f"User {user_email} authorized for server {server_name}")
                        authorized.append(server_name)
                        user_authorized = True
                        break
                
                if not user_authorized:
                    logger.info(f"User {user_email} NOT authorized for server {server_name}")
        
        logger.info(f"Final authorized servers for {user_email}: {authorized}")
        return authorized
    
    async def cleanup(self):
        """Cleanup all clients."""
        logger.info("Cleaning up MCP clients")
        # FastMCP clients handle cleanup automatically with context managers