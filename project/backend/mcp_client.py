"""FastMCP client for connecting to MCP servers and managing tools."""

import asyncio
import json
import logging
import os
from typing import Dict, List, Any, Optional

from fastmcp import Client

logger = logging.getLogger(__name__)


class MCPToolManager:
    """Manager for MCP servers and their tools."""
    
    def __init__(self, config_path: str = "mcp.json"):
        self.config_path = config_path
        self.servers_config = {}
        self.clients = {}
        self.available_tools = {}
        self.load_config()
        
    def load_config(self):
        """Load MCP server configuration."""
        config_paths = [
            self.config_path,          # Default: mcp.json
            f"../{self.config_path}",  # Parent directory
            os.path.join(os.path.dirname(__file__), "..", self.config_path)  # Relative to script
        ]
        
        for config_path in config_paths:
            try:
                if os.path.exists(config_path):
                    logger.info(f"Found MCP config at: {os.path.abspath(config_path)}")
                    with open(config_path, 'r') as f:
                        self.servers_config = json.load(f)
                        if isinstance(self.servers_config, dict):
                            logger.info(f"Loaded MCP config with {len(self.servers_config)} servers: {list(self.servers_config.keys())}")
                            return
                        else:
                            logger.error(f"Invalid JSON format in {config_path}: expected dict, got {type(self.servers_config)}")
                            self.servers_config = {}
                            return
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error in {config_path}: {e}")
                self.servers_config = {}
                return
            except Exception as e:
                logger.error(f"Error reading {config_path}: {e}")
                continue
        
        logger.warning(f"MCP config file not found in any of these locations: {config_paths}")
        logger.info("Create mcp.json with your MCP server configurations to enable tool support")
        self.servers_config = {}
    
    async def initialize_clients(self):
        """Initialize FastMCP clients for all configured servers."""
        for server_name, config in self.servers_config.items():
            try:
                # TODO: allow different mcp types. 
                # Create client based on server type
                server_path = f"mcp/{server_name}/main.py"
                if os.path.exists(server_path):
                    client = Client(server_path)
                    self.clients[server_name] = client
                    logger.info(f"Created MCP client for {server_name}")
                else:
                    logger.error(f"MCP server script not found: {server_path}")
                    # add traceback
                    import traceback
                    print(traceback.format_exc())
            except Exception as e:
                logger.error(f"Error creating client for {server_name}: {e}")
    
    async def discover_tools(self):
        """Discover tools from all MCP servers."""
        self.available_tools = {}

        
        for server_name, client in self.clients.items():
            try:
                async with client:
                    tools = await client.list_tools()
                    self.available_tools[server_name] = {
                        'tools': tools,
                        'config': self.servers_config[server_name]
                    }
                    logger.info(f"Discovered {len(tools)} tools from {server_name}")
            except Exception as e:
                logger.error(f"Error discovering tools from {server_name}: {e}")
                # use traceback
                import traceback
                print(traceback.format_exc())
                self.available_tools[server_name] = {
                    'tools': [],
                    'config': self.servers_config[server_name]
                }
    
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
            if server_name in self.available_tools:
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
        
        for server_name in self.get_available_servers():
            required_groups = self.get_server_groups(server_name)
            if not required_groups:  # No restrictions
                authorized.append(server_name)
            else:
                # Check if user is in any required group
                for group in required_groups:
                    if auth_check_func(user_email, group):
                        authorized.append(server_name)
                        break
        
        return authorized
    
    async def cleanup(self):
        """Cleanup all clients."""
        logger.info("Cleaning up MCP clients")
        # FastMCP clients handle cleanup automatically with context managers