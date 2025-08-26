"""Compatibility layer for MCP models.

Re-export MCP transport models from the new location under
backend.models.transport.mcp so existing imports continue to work during
migration.
"""

from models.transport.mcp.models import (
    MCPServerConfigModel,
    MCPServerConfig,
    MCPServer,
    MCPTool,
    MCPPrompt,
    MCPResource,
    ToolCallResult,
    MCPConfig,
)

__all__ = [
    "MCPServerConfigModel",
    "MCPServerConfig",
    "MCPServer",
    "MCPTool",
    "MCPPrompt",
    "MCPResource",
    "ToolCallResult",
    "MCPConfig",
]
