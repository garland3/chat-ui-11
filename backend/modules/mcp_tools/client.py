"""FastMCP client for connecting to MCP servers and managing tools."""

import logging
import os
from typing import Dict, List, Any, Optional

from fastmcp import Client
from modules.config import config_manager
from core.auth_utils import create_authorization_manager
from domain.messages.models import ToolCall, ToolResult

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
        
    
    def _determine_transport_type(self, config: Dict[str, Any]) -> str:
        """Determine the transport type for an MCP server configuration.
        
        Priority order:
        1. Explicit 'transport' field (highest priority)
        2. Auto-detection from command
        3. Auto-detection from URL if it has protocol
        4. Fallback to 'type' field (backward compatibility)
        """
        # 1. Explicit transport field takes highest priority
        if config.get("transport"):
            logger.debug(f"Using explicit transport: {config['transport']}")
            return config["transport"]
        
        # 2. Auto-detect from command (takes priority over URL)
        if config.get("command"):
            logger.debug("Auto-detected STDIO transport from command")
            return "stdio"
        
        # 3. Auto-detect from URL if it has protocol
        url = config.get("url")
        if url:
            if url.startswith(("http://", "https://")):
                if url.endswith("/sse"):
                    logger.debug(f"Auto-detected SSE transport from URL: {url}")
                    return "sse"
                else:
                    logger.debug(f"Auto-detected HTTP transport from URL: {url}")
                    return "http"
            else:
                # URL without protocol - check if type field specifies transport
                transport_type = config.get("type", "stdio")
                if transport_type in ["http", "sse"]:
                    logger.debug(f"Using type field '{transport_type}' for URL without protocol: {url}")
                    return transport_type
                else:
                    logger.debug(f"URL without protocol, defaulting to HTTP: {url}")
                    return "http"
            
        # 4. Fallback to type field (backward compatibility)
        transport_type = config.get("type", "stdio")
        logger.debug(f"Using fallback transport type: {transport_type}")
        return transport_type

    async def initialize_clients(self):
        """Initialize FastMCP clients for all configured servers."""
        for server_name, config in self.servers_config.items():
            try:
                transport_type = self._determine_transport_type(config)
                
                if transport_type in ["http", "sse"]:
                    # HTTP/SSE MCP server
                    url = config.get("url")
                    if not url:
                        logger.error(f"No URL provided for HTTP/SSE server: {server_name}")
                        continue
                    
                    # Ensure URL has protocol for FastMCP client
                    if not url.startswith(("http://", "https://")):
                        url = f"http://{url}"
                        logger.debug(f"Added http:// protocol to URL: {url}")
                    
                    if transport_type == "sse":
                        # Use explicit SSE transport
                        logger.debug(f"Creating SSE client for {server_name} at {url}")
                        from fastmcp.client.transports import SSETransport
                        transport = SSETransport(url)
                        client = Client(transport)
                    else:
                        # Use HTTP transport (StreamableHttp)
                        logger.debug(f"Creating HTTP client for {server_name} at {url}")
                        client = Client(url)
                    
                    self.clients[server_name] = client
                    logger.info(f"Created {transport_type.upper()} MCP client for {server_name}")
                    continue
                
                elif transport_type == "stdio":
                    # STDIO MCP server
                    command = config.get("command")
                    if command:
                        # Custom command specified
                        cwd = config.get("cwd")
                        if cwd:
                            # Convert relative path to absolute path from project root
                            if not os.path.isabs(cwd):
                                # Assume relative to project root (parent of backend)
                                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                                cwd = os.path.join(project_root, cwd)
                            
                            if os.path.exists(cwd):
                                logger.debug(f"Creating STDIO client for {server_name} with command: {command} in cwd: {cwd}")
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
                    else:
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
                            continue
                else:
                    logger.error(f"Unsupported transport type '{transport_type}' for server: {server_name}")
                    continue
                            
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
                    # logger.info(f"Adding tool {tool.name} for server {server_name} ")
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
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        available_tools = []
        for server_name, server_data in self.available_tools.items():
            if server_name == "canvas":
                available_tools.append("canvas_canvas")
            else:
                for tool in server_data.get('tools', []):
                    available_tools.append(f"{server_name}_{tool.name}")
        return available_tools
    
    def get_tools_schema(self, tool_names: List[str]) -> List[Dict[str, Any]]:
        """Get schemas for specified tools."""
        # Extract server names from tool names
        server_names = []
        for tool_name in tool_names:
            if tool_name.startswith("canvas_"):
                server_names.append("canvas")
            else:
                # Extract server name (everything before the last underscore)
                parts = tool_name.split("_")
                if len(parts) >= 2:
                    server_name = "_".join(parts[:-1])
                    if server_name in self.available_tools:
                        server_names.append(server_name)
        
        # Remove duplicates while preserving order
        server_names = list(dict.fromkeys(server_names))
        
        # Get tools for these servers
        tools_data = self.get_tools_for_servers(server_names)
        return tools_data.get('tools', [])
    
    async def execute_tool(
        self,
        tool_call: ToolCall,
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Execute a tool call."""
        # Handle canvas pseudo-tool
        if tool_call.name == "canvas_canvas":
            # Canvas tool just returns the content - it's handled by frontend
            content = tool_call.arguments.get("content", "")
            return ToolResult(
                tool_call_id=tool_call.id,
                content=f"Canvas content displayed: {content[:100]}..." if len(content) > 100 else f"Canvas content displayed: {content}",
                success=True
            )
        
        # Parse server and tool name from tool_call.name
        parts = tool_call.name.split("_")
        if len(parts) < 2:
            return ToolResult(
                tool_call_id=tool_call.id,
                content=f"Invalid tool name format: {tool_call.name}",
                success=False,
                error=f"Invalid tool name format: {tool_call.name}"
            )
        
        # Extract server name (everything except the last part)
        server_name = "_".join(parts[:-1])
        actual_tool_name = parts[-1]
        
        try:
            result = await self.call_tool(server_name, actual_tool_name, tool_call.arguments)
            return ToolResult(
                tool_call_id=tool_call.id,
                content=str(result),
                success=True
            )
        except Exception as e:
            logger.error(f"Error executing tool {tool_call.name}: {e}")
            return ToolResult(
                tool_call_id=tool_call.id,
                content=f"Error executing tool: {str(e)}",
                success=False,
                error=str(e)
            )
    
    async def execute_tool_calls(
        self,
        tool_calls: List[ToolCall],
        context: Optional[Dict[str, Any]] = None
    ) -> List[ToolResult]:
        """Execute multiple tool calls."""
        results = []
        for tool_call in tool_calls:
            result = await self.execute_tool(tool_call, context)
            results.append(result)
        return results

    async def cleanup(self):
        """Cleanup all clients."""
        logger.info("Cleaning up MCP clients")
        # FastMCP clients handle cleanup automatically with context managers