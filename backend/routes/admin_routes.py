"""Admin routes for configuration management and system monitoring.

FastAPI routes that delegate business logic to admin managers.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from managers.admin import (
    AdminManager,
    AdminConfigUpdate,
    BannerMessageUpdate,
    ConfigHandler,
    LogManager,
    get_admin_group_name,
)
from managers.auth.utils import get_current_user
from managers.auth.auth_manager import is_user_in_group

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(current_user: str = Depends(get_current_user)) -> str:
    """Require admin group membership for route access."""
    admin_group = get_admin_group_name()
    if not is_user_in_group(current_user, admin_group):
        raise HTTPException(
            status_code=403,
            detail=f"Admin access required. User must be in '{admin_group}' group.",
        )
    return current_user


@admin_router.get("/")
async def admin_dashboard(admin_user: str = Depends(require_admin)):
    """Get admin dashboard information."""
    return AdminManager.get_admin_dashboard_info(admin_user)


# --- Banner Management ---


@admin_router.get("/banners")
async def get_banner_config(admin_user: str = Depends(require_admin)):
    """Get current banner messages configuration."""
    try:
        messages, file_path, last_modified = ConfigHandler.get_banner_messages()
        return {
            "messages": messages,
            "file_path": str(file_path),
            "last_modified": last_modified,
        }
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error getting banner config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/banners")
async def update_banner_config(
    update: BannerMessageUpdate, admin_user: str = Depends(require_admin)
):
    """Update banner messages configuration."""
    try:
        messages_file = ConfigHandler.get_admin_config_path("messages.txt")
        logger.info(f"Updating banner messages to: {update.messages}")
        logger.info(f"Writing banner messages to file: {messages_file}")
        ConfigHandler.update_banner_messages(update.messages)
        logger.info(f"Banner messages updated by {admin_user}")
        return {
            "message": "Banner messages updated successfully",
            "messages": update.messages,
            "updated_by": admin_user,
        }
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error updating banner config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- MCP Management ---


@admin_router.post("/mcp/reload")
async def reload_mcp_servers(admin_user: str = Depends(require_admin)):
    """Reload MCP servers (clients, tools, prompts)."""
    return await AdminManager.reload_mcp_servers(admin_user)


@admin_router.get("/mcp-config")
async def get_mcp_config(admin_user: str = Depends(require_admin)):
    """Get current MCP server configuration."""
    try:
        content, parsed, file_path, last_modified = ConfigHandler.get_mcp_config()
        return {
            "content": content,
            "parsed": parsed,
            "file_path": str(file_path),
            "last_modified": last_modified,
        }
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error getting MCP config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/mcp-config")
async def update_mcp_config(
    update: AdminConfigUpdate, admin_user: str = Depends(require_admin)
):
    """Update MCP server configuration."""
    try:
        ConfigHandler.update_mcp_config(update.content)
        logger.info(f"MCP configuration updated by {admin_user}")
        return {
            "message": "MCP configuration updated successfully",
            "updated_by": admin_user,
        }
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error updating MCP config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- LLM Configuration ---


@admin_router.get("/llm-config")
async def get_llm_config(admin_user: str = Depends(require_admin)):
    """Get current LLM configuration."""
    try:
        content, parsed, file_path, last_modified = ConfigHandler.get_llm_config()
        return {
            "content": content,
            "parsed": parsed,
            "file_path": str(file_path),
            "last_modified": last_modified,
        }
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error getting LLM config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/llm-config")
async def update_llm_config(
    update: AdminConfigUpdate, admin_user: str = Depends(require_admin)
):
    """Update LLM configuration."""
    try:
        ConfigHandler.update_llm_config(update.content)
        logger.info(f"LLM configuration updated by {admin_user}")
        return {
            "message": "LLM configuration updated successfully",
            "updated_by": admin_user,
        }
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error updating LLM config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Config Viewer ---


@admin_router.get("/config/view")
async def get_all_configs(admin_user: str = Depends(require_admin)):
    """Get all configuration values for admin viewing with masking."""
    try:
        return ConfigHandler.get_all_configs_view()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error getting config view: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Log Management ---


@admin_router.get("/logs/viewer")
async def get_enhanced_logs(
    lines: int = 500,
    level_filter: Optional[str] = None,
    module_filter: Optional[str] = None,
    admin_user: str = Depends(require_admin),  # noqa: ARG001 (enforces auth)
):
    """Get enhanced logs with filtering capabilities."""
    return LogManager.get_enhanced_logs(lines, level_filter, module_filter)


@admin_router.post("/logs/clear")
async def clear_app_logs(admin_user: str = Depends(require_admin)):
    """Clear application log files."""
    try:
        cleared_files, message = LogManager.clear_logs()
        if cleared_files:
            logger.info(f"Log files cleared by {admin_user}: {cleared_files}")
        return {
            "message": message,
            "cleared_by": admin_user,
            "files_cleared": cleared_files,
        }
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error clearing logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/logs/download")
async def download_logs(admin_user: str = Depends(require_admin)):
    """Download the raw application log file."""
    return LogManager.get_log_file_for_download()
