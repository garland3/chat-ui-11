"""Admin manager for administrative operations.

Coordinates admin operations including MCP server management and
administrative utilities.
"""

from __future__ import annotations

import logging
from typing import Dict

from fastapi import HTTPException

from managers.admin.admin_models import McpReloadResponse
from managers.app_factory.app_factory import app_factory
from managers.config.config_manager import config_manager

logger = logging.getLogger(__name__)


def get_admin_group_name() -> str:
    """Get admin group name from configuration."""
    return config_manager.app_settings.admin_group


class AdminManager:
    """Manages administrative operations and MCP server coordination."""
    
    @staticmethod
    async def reload_mcp_servers(admin_user: str) -> McpReloadResponse:
        """Reload MCP servers and return status information."""
        try:
            mcp = await app_factory.get_mcp_manager()
            # Re-initialize all MCP state
            await mcp.cleanup()
            await mcp.initialize()

            # Build counts per server
            servers = mcp.get_available_servers()
            tool_counts: Dict[str, int] = {name: 0 for name in servers}
            prompt_counts: Dict[str, int] = {name: 0 for name in servers}

            for tool in mcp.get_available_tools():
                tool_counts[tool.server_name] = tool_counts.get(tool.server_name, 0) + 1
            for prompt in mcp.get_available_prompts():
                prompt_counts[prompt.server_name] = (
                    prompt_counts.get(prompt.server_name, 0) + 1
                )

            logger.info(f"MCP servers reloaded by {admin_user}")
            
            return McpReloadResponse(
                message="MCP servers reloaded",
                servers=servers,
                tool_counts=tool_counts,
                prompt_counts=prompt_counts,
                reloaded_by=admin_user,
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error reloading MCP servers: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def get_admin_dashboard_info(admin_user: str) -> Dict[str, any]:
        """Get admin dashboard information."""
        return {
            "message": "Admin Dashboard",
            "user": admin_user,
            "available_endpoints": [
                "/admin/banners",
                "/admin/config/view",
                "/admin/llm-config",
                "/admin/mcp-config",
                "/admin/mcp/reload",
                "/admin/logs/viewer",
                "/admin/logs/clear",
                "/admin/logs/download",
            ],
        }