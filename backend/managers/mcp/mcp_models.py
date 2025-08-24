"""MCP-related models compatibility shim.

Re-exports MCP transport models so legacy imports from managers layer keep
working while the authoritative definitions live under models.transport.mcp.
"""

from models.transport.mcp.models import (
    MCPServerConfig,
    MCPServer,
    MCPTool,
    MCPPrompt,
    MCPResource,
    ToolCallResult,
    MCPServerConfigModel,
    MCPConfig,
)

# Re-export for backward compatibility
__all__ = [
    'MCPServerConfig',
    'MCPServer', 
    'MCPTool',
    'MCPPrompt',
    'MCPResource',
    'ToolCallResult',
    'MCPServerConfigModel',
    'MCPConfig'
]
