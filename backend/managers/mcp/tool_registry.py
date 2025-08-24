"""Registry for managing MCP tools."""

import logging
from typing import Dict, List, Optional, Set
from .mcp_models import MCPTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for MCP tools."""
    
    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}  # full_name -> tool
        self._tools_by_server: Dict[str, List[MCPTool]] = {}  # server_name -> tools
    
    def add_tool(self, tool: MCPTool) -> None:
        """Add a tool to the registry."""
        # Store by full name
        self._tools[tool.full_name] = tool
        
        # Store by server
        if tool.server_name not in self._tools_by_server:
            self._tools_by_server[tool.server_name] = []
        self._tools_by_server[tool.server_name].append(tool)
        
        logger.debug(f"Added tool to registry: {tool.full_name}")
    
    def get_tool_by_name(self, full_name: str) -> Optional[MCPTool]:
        """Get a tool by its full name."""
        return self._tools.get(full_name)
    
    def get_tools_by_server(self, server_name: str) -> List[MCPTool]:
        """Get all tools for a specific server."""
        return self._tools_by_server.get(server_name, [])
    
    def get_all_tools(self) -> List[MCPTool]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    def get_enabled_tools(self) -> List[MCPTool]:
        """Get only enabled tools."""
        return [tool for tool in self._tools.values() if tool.enabled]
    
    def get_tools_by_tags(self, tags: Set[str]) -> List[MCPTool]:
        """Get tools that have any of the specified tags."""
        return [
            tool for tool in self._tools.values()
            if tool.tags.intersection(tags)
        ]
    
    def remove_tool(self, full_name: str) -> bool:
        """Remove a tool from the registry."""
        tool = self._tools.get(full_name)
        if tool:
            # Remove from main registry
            del self._tools[full_name]
            
            # Remove from server registry
            server_tools = self._tools_by_server.get(tool.server_name, [])
            self._tools_by_server[tool.server_name] = [
                t for t in server_tools if t.full_name != full_name
            ]
            
            logger.debug(f"Removed tool from registry: {full_name}")
            return True
        return False
    
    def remove_tools_by_server(self, server_name: str) -> int:
        """Remove all tools for a specific server."""
        server_tools = self._tools_by_server.get(server_name, [])
        count = 0
        
        for tool in server_tools:
            if tool.full_name in self._tools:
                del self._tools[tool.full_name]
                count += 1
        
        if server_name in self._tools_by_server:
            del self._tools_by_server[server_name]
        
        if count > 0:
            logger.debug(f"Removed {count} tools for server: {server_name}")
        
        return count
    
    def tool_exists(self, full_name: str) -> bool:
        """Check if a tool exists in the registry."""
        return full_name in self._tools
    
    def get_tool_names(self) -> List[str]:
        """Get list of all tool names."""
        return list(self._tools.keys())
    
    def get_server_names(self) -> List[str]:
        """Get list of server names that have tools."""
        return list(self._tools_by_server.keys())
    
    def clear(self) -> None:
        """Clear all tools from the registry."""
        self._tools.clear()
        self._tools_by_server.clear()
        logger.debug("Cleared tool registry")
    
    def count(self) -> int:
        """Get count of registered tools."""
        return len(self._tools)
    
    def count_by_server(self, server_name: str) -> int:
        """Get count of tools for a specific server."""
        return len(self._tools_by_server.get(server_name, []))
