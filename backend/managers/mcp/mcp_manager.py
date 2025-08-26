"""Clean, modern MCP manager using FastMCP patterns."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport, SSETransport

from managers.config.config_manager import ConfigManager
from .mcp_models import MCPServer, MCPTool, MCPPrompt, MCPServerConfig
from .server_registry import ServerRegistry
from .tool_registry import ToolRegistry
from .prompt_registry import PromptRegistry

logger = logging.getLogger(__name__)


class MCPManager:
    """Modern MCP server and tool management."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.server_registry = ServerRegistry()
        self.tool_registry = ToolRegistry()
        self.prompt_registry = PromptRegistry()
        self.clients: Dict[str, Client] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize MCP manager and discover servers."""
        if self._initialized:
            return

        logger.info("Initializing MCP manager")

        # Load server configurations
        await self._load_server_configs()

        # Initialize clients in parallel
        await self._initialize_clients()

        # Discover tools from all servers
        await self._discover_tools()

        # Discover prompts from all servers
        await self._discover_prompts()

        self._initialized = True
        logger.info(f"MCP manager initialized with {len(self.clients)} servers")

    async def _load_server_configs(self) -> None:
        """Load MCP server configurations."""
        try:
            mcp_config = self.config_manager.get_mcp_config()

            for server_name, server_config in mcp_config.servers.items():
                # Use the from_pydantic method for clean conversion
                runtime_config = MCPServerConfig.from_pydantic(server_config)

                mcp_server = MCPServer(name=server_name, config=runtime_config)
                self.server_registry.add_server(mcp_server)
                logger.debug(f"Loaded config for server: {server_name}")

        except Exception as e:
            logger.error(f"Failed to load MCP server configs: {e}")
            raise

    async def _initialize_clients(self) -> None:
        """Initialize FastMCP clients for all servers."""
        servers = self.server_registry.get_all_servers()

        if not servers:
            logger.warning("No MCP servers configured")
            return

        # Initialize clients in parallel
        tasks = [self._initialize_client(server) for server in servers]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for server, result in zip(servers, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to initialize client for {server.name}: {result}")
            elif result:
                self.clients[server.name] = result
                logger.debug(f"Initialized client for {server.name}")

    async def _initialize_client(self, server: MCPServer) -> Optional[Client]:
        """Initialize a single MCP client."""
        try:
            config = server.config

            if config.transport == "stdio":
                return self._create_stdio_client(server)
            elif config.transport in ["http", "sse"]:
                return self._create_http_client(server)
            else:
                logger.error(
                    f"Unsupported transport '{config.transport}' for server {server.name}"
                )
                return None

        except Exception as e:
            logger.error(f"Error initializing client for {server.name}: {e}")
            return None

    def _create_stdio_client(self, server: MCPServer) -> Optional[Client]:
        """Create STDIO client for MCP server."""
        config = server.config

        if config.command:
            # Use custom command
            args = config.args or []
            cwd = None

            if config.cwd:
                # Convert relative path to absolute
                if not Path(config.cwd).is_absolute():
                    # Project root is parent of backend (.. of backend dir)
                    # __file__ = /repo/backend/managers/mcp/mcp_manager.py
                    # parents[3] -> /repo
                    project_root = Path(__file__).parents[3]  # /workspaces/chat-ui-11
                    cwd = str(project_root / config.cwd)
                else:
                    cwd = config.cwd

                if not Path(cwd).exists():
                    logger.error(f"Working directory does not exist: {cwd}")
                    return None

            transport = StdioTransport(
                command=config.command, args=args, cwd=cwd, env=config.env
            )
            return Client(transport)
        else:
            # Default: look for server in /mcp/servers/{server_name}/main.py
            server_path = Path("mcp/servers") / server.name / "main.py"
            if server_path.exists():
                return Client(str(server_path))
            else:
                logger.error(
                    f"No command specified and default server not found: {server_path}"
                )
                return None

    def _create_http_client(self, server: MCPServer) -> Optional[Client]:
        """Create HTTP/SSE client for MCP server."""
        config = server.config

        if not config.url:
            logger.error(f"No URL specified for HTTP server {server.name}")
            return None

        url = config.url
        # not sure this is good. in k8 sometimes the url does not have https
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"

        if config.transport == "sse":
            transport = SSETransport(url)
            return Client(transport)
        else:
            return Client(url)

    async def _discover_tools(self) -> None:
        """Discover tools from all initialized clients."""
        if not self.clients:
            logger.warning("No clients initialized for tool discovery")
            return

        logger.info(f"Discovering tools from {len(self.clients)} servers")

        # Discover tools in parallel
        tasks = [
            self._discover_tools_for_server(server_name, client)
            for server_name, client in self.clients.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for server_name, result in zip(self.clients.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to discover tools for {server_name}: {result}")
            elif isinstance(result, list):
                for tool in result:
                    self.tool_registry.add_tool(tool)
                logger.debug(f"Discovered {len(result)} tools from {server_name}")

    async def _discover_tools_for_server(
        self, server_name: str, client: Client
    ) -> List[MCPTool]:
        """Discover tools for a single server."""
        tools = []
        try:
            async with client:
                raw_tools = await client.list_tools()

                for raw_tool in raw_tools:
                    tool = MCPTool(
                        name=raw_tool.name,
                        server_name=server_name,
                        description=getattr(raw_tool, "description", ""),
                        input_schema=getattr(raw_tool, "inputSchema", {}),
                        tags=getattr(
                            getattr(raw_tool, "meta", {}), "get", lambda x, d: d
                        )("tags", set()),
                    )
                    tools.append(tool)

                logger.info(
                    f"Found {len(tools)} tools in {server_name}: {[t.name for t in tools]}"
                )

        except Exception as e:
            logger.error(f"Error discovering tools for {server_name}: {e}")

        return tools

    async def _discover_prompts(self) -> None:
        """Discover prompts from all initialized clients."""
        if not self.clients:
            logger.warning("No clients initialized for prompt discovery")
            return

        logger.info(f"Discovering prompts from {len(self.clients)} servers")

        # Discover prompts in parallel
        tasks = [
            self._discover_prompts_for_server(server_name, client)
            for server_name, client in self.clients.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for server_name, result in zip(self.clients.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to discover prompts for {server_name}: {result}")
            elif isinstance(result, list):
                for prompt in result:
                    self.prompt_registry.add_prompt(prompt)
                logger.debug(f"Discovered {len(result)} prompts from {server_name}")

    async def _discover_prompts_for_server(
        self, server_name: str, client: Client
    ) -> List[MCPPrompt]:
        """Discover prompts for a single server."""
        prompts = []
        try:
            async with client:
                raw_prompts = await client.list_prompts()

                for raw_prompt in raw_prompts:
                    prompt = MCPPrompt(
                        name=raw_prompt.name,
                        server_name=server_name,
                        description=getattr(raw_prompt, "description", ""),
                        arguments=getattr(raw_prompt, "arguments", {}),
                    )
                    prompts.append(prompt)

                logger.info(
                    f"Found {len(prompts)} prompts in {server_name}: {[p.name for p in prompts]}"
                )

        except Exception as e:
            logger.error(f"Error discovering prompts for {server_name}: {e}")

        return prompts

    # Public API methods

    def get_available_servers(self) -> List[str]:
        """Get list of available server names."""
        return list(self.clients.keys())

    def get_authorized_servers(self, user_groups: List[str]) -> List[str]:
        """Get servers the user is authorized to access based on groups."""
        authorized = []

        for server_name in self.clients.keys():
            server = self.server_registry.get_server(server_name)
            if not server:
                continue

            # If server has no groups restriction, it's available to everyone
            if not server.config.groups:
                authorized.append(server_name)
                continue

            # Check if user has any of the required groups
            if any(group in user_groups for group in server.config.groups):
                authorized.append(server_name)

        return authorized

    def get_server_info(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a server."""
        server = self.server_registry.get_server(server_name)
        if not server:
            return None

        return {
            "name": server.name,
            "description": server.config.description,
            "short_description": server.config.short_description,
            "author": server.config.author,
            "help_email": server.config.help_email,
            "groups": server.config.groups,
            "enabled": server.enabled,
            "transport": server.config.transport,
        }

    def get_available_tools(self) -> List[MCPTool]:
        """Get list of all available tools."""
        return self.tool_registry.get_all_tools()

    def get_tools_for_servers(self, server_names: List[str]) -> List[MCPTool]:
        """Get tools for specific servers."""
        all_tools = self.tool_registry.get_all_tools()
        return [tool for tool in all_tools if tool.server_name in server_names]

    def get_tool_by_name(self, tool_name: str) -> Optional[MCPTool]:
        """Get a tool by its full name (server_toolname)."""
        return self.tool_registry.get_tool_by_name(tool_name)

    def get_available_prompts(self) -> List[MCPPrompt]:
        """Get list of all available prompts."""
        return self.prompt_registry.get_all_prompts()

    def get_prompts_for_servers(self, server_names: List[str]) -> List[MCPPrompt]:
        """Get prompts for specific servers."""
        all_prompts = self.prompt_registry.get_all_prompts()
        return [prompt for prompt in all_prompts if prompt.server_name in server_names]

    def get_prompt_by_name(self, prompt_name: str) -> Optional[MCPPrompt]:
        """Get a prompt by its full name (server_promptname)."""
        return self.prompt_registry.get_prompt_by_name(prompt_name)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on its server."""
        tool = self.get_tool_by_name(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        client = self.clients.get(tool.server_name)
        if not client:
            raise ValueError(f"No client available for server: {tool.server_name}")

        try:
            async with client:
                # Use the original tool name from the server
                actual_tool_name = tool.name
                result = await client.call_tool(actual_tool_name, arguments)
                logger.debug(f"Successfully called {tool_name}")
                return result
        except Exception as e:
            logger.error(f"Error calling {tool_name}: {e}")
            raise

    async def get_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> Any:
        """Get a prompt from its server."""
        prompt = self.get_prompt_by_name(prompt_name)
        if not prompt:
            raise ValueError(f"Prompt not found: {prompt_name}")

        client = self.clients.get(prompt.server_name)
        if not client:
            raise ValueError(f"No client available for server: {prompt.server_name}")

        try:
            async with client:
                # Use the original prompt name from the server
                actual_prompt_name = prompt.name
                result = await client.get_prompt(actual_prompt_name, arguments)
                logger.debug(f"Successfully retrieved prompt {prompt_name}")
                return result
        except Exception as e:
            logger.error(f"Error retrieving prompt {prompt_name}: {e}")
            raise

    async def cleanup(self) -> None:
        """Cleanup resources."""
        logger.info("Cleaning up MCP manager")
        # FastMCP clients handle cleanup automatically
        self.clients.clear()
        self._initialized = False
