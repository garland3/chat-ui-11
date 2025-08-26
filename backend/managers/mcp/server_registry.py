"""Registry for managing MCP servers."""

import logging
from typing import Dict, List, Optional
from .mcp_models import MCPServer

logger = logging.getLogger(__name__)


class ServerRegistry:
    """Registry for MCP servers."""

    def __init__(self):
        self._servers: Dict[str, MCPServer] = {}

    def add_server(self, server: MCPServer) -> None:
        """Add a server to the registry."""
        self._servers[server.name] = server
        logger.debug(f"Added server to registry: {server.name}")

    def get_server(self, name: str) -> Optional[MCPServer]:
        """Get a server by name."""
        return self._servers.get(name)

    def get_all_servers(self) -> List[MCPServer]:
        """Get all registered servers."""
        return list(self._servers.values())

    def get_enabled_servers(self) -> List[MCPServer]:
        """Get only enabled servers."""
        return [server for server in self._servers.values() if server.enabled]

    def remove_server(self, name: str) -> bool:
        """Remove a server from the registry."""
        if name in self._servers:
            del self._servers[name]
            logger.debug(f"Removed server from registry: {name}")
            return True
        return False

    def server_exists(self, name: str) -> bool:
        """Check if a server exists in the registry."""
        return name in self._servers

    def get_server_names(self) -> List[str]:
        """Get list of all server names."""
        return list(self._servers.keys())

    def get_enabled_server_names(self) -> List[str]:
        """Get list of enabled server names."""
        return [name for name, server in self._servers.items() if server.enabled]

    def clear(self) -> None:
        """Clear all servers from the registry."""
        self._servers.clear()
        logger.debug("Cleared server registry")

    def count(self) -> int:
        """Get count of registered servers."""
        return len(self._servers)
