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
    
    def __init__(self, config_path: str = "configfiles/mcp.json"):
        self.config_path = config_path
        mcp_config = config_manager.mcp_config
        self.servers_config = {name: server.model_dump() for name, server in mcp_config.servers.items()}
        self.clients = {}
        self.available_tools = {}
        self.available_prompts = {}
        
    
    async def initialize_clients(self):
        """Initialize FastMCP clients for all configured servers."""
        for server_name, config in self.servers_config.items():
            try:
                # Check for HTTP URL first
                url = config.get("url")
                if url:
                    # HTTP/SSE MCP server - Client auto-detects transport from URL
                    logger.debug(f"Creating HTTP/SSE client for {server_name} at {url}")
                    client = Client(url)
                    self.clients[server_name] = client
                    logger.info(f"Created HTTP/SSE MCP client for {server_name}")
                    continue
                
                # Check for custom command
                command = config.get("command")
                if command:
                    # STDIO MCP server with custom command - Client auto-detects STDIO transport
                    cwd = config.get("cwd")
                    if cwd:
                        # Convert relative path to absolute path from project root
                        if not os.path.isabs(cwd):
                            # Assume relative to project root (parent of backend)
                            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                            cwd = os.path.join(project_root, cwd)
                        
                        if os.path.exists(cwd):
                            logger.debug(f"Creating STDIO client for {server_name} with command: {command} in cwd: {cwd}")
                            # FastMCP Client can handle cwd parameter in StdioTransport
                            from fastmcp.client.transports import StdioTransport
                            transport = StdioTransport(command=command[0], args=command[1:], cwd=cwd)
                            client = Client(transport)
                            self.clients[server_name] = client
                            logger.info(f"Created STDIO MCP client for {server_name} with custom command and cwd")
                        else:
                            logger.error(f"Working directory does not exist: {cwd}")
                            continue
                    else:
                        logger.debug(f"Creating STDIO client for {server_name} with command: {command}")
                        client = Client(command)
                        self.clients[server_name] = client
                        logger.info(f"Created STDIO MCP client for {server_name} with custom command")
                    continue
                
                # Fallback to old behavior for backward compatibility
                server_path = f"mcp/{server_name}/main.py"
                logger.debug(f"Attempting to initialize {server_name} at path: {server_path}")
                if os.path.exists(server_path):
                    logger.debug(f"Server script exists for {server_name}, creating client...")
                    client = Client(server_path)  # Client auto-detects STDIO transport from .py file
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
    
    async def discover_prompts(self):
        """Discover prompts from all MCP servers."""
        self.available_prompts = {}
        
        for server_name, client in self.clients.items():
            logger.debug(f"Attempting to discover prompts from {server_name}")
            try:
                logger.debug(f"Opening client connection for {server_name}")
                async with client:
                    logger.debug(f"Client connected for {server_name}, listing prompts...")
                    try:
                        prompts = await client.list_prompts()
                        logger.debug(f"Got {len(prompts)} prompts from {server_name}: {[prompt.name for prompt in prompts]}")
                        self.available_prompts[server_name] = {
                            'prompts': prompts,
                            'config': self.servers_config[server_name]
                        }
                        logger.info(f"Discovered {len(prompts)} prompts from {server_name}")
                        logger.debug(f"Successfully stored prompts for {server_name}")
                    except AttributeError:
                        # Server doesn't support prompts
                        logger.debug(f"Server {server_name} does not support prompts")
                        self.available_prompts[server_name] = {
                            'prompts': [],
                            'config': self.servers_config[server_name]
                        }
            except Exception as e:
                logger.error(f"Error discovering prompts from {server_name}: {e}", exc_info=True)
                self.available_prompts[server_name] = {
                    'prompts': [],
                    'config': self.servers_config[server_name]
                }
                logger.debug(f"Set empty prompts list for failed server {server_name}")
    
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
    
    async def get_prompt(self, server_name: str, prompt_name: str, arguments: Dict[str, Any] = None) -> Any:
        """Get a specific prompt from an MCP server."""
        if server_name not in self.clients:
            raise ValueError(f"No client available for server: {server_name}")
        
        client = self.clients[server_name]
        try:
            async with client:
                if arguments:
                    result = await client.get_prompt(prompt_name, arguments)
                else:
                    result = await client.get_prompt(prompt_name)
                logger.info(f"Successfully retrieved prompt {prompt_name} from {server_name}")
                return result
        except Exception as e:
            logger.error(f"Error getting prompt {prompt_name} from {server_name}: {e}")
            raise
    
    def get_available_prompts_for_servers(self, server_names: List[str]) -> Dict[str, Any]:
        """Get available prompts for selected servers."""
        available_prompts = {}
        
        for server_name in server_names:
            if server_name in self.available_prompts:
                server_prompts = self.available_prompts[server_name]['prompts']
                for prompt in server_prompts:
                    prompt_key = f"{server_name}_{prompt.name}"
                    available_prompts[prompt_key] = {
                        'server': server_name,
                        'name': prompt.name,
                        'description': prompt.description or '',
                        'arguments': prompt.arguments or {}
                    }
        
        return available_prompts
    
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