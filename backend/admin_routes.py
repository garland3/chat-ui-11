"""Admin routes for configuration management and system monitoring.

This module provides admin-only routes for managing:
- Banner messages
- MCP server configuration
- LLM configuration  
- Help content
- System logs and health
"""

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from auth import is_user_in_group
from utils import get_current_user
from config import config_manager
from mcp_health_check import mcp_health_monitor, get_mcp_health_status, trigger_mcp_health_check


logger = logging.getLogger(__name__)

# Admin router
admin_router = APIRouter(prefix="/admin", tags=["admin"])


class AdminConfigUpdate(BaseModel):
    """Model for admin configuration updates."""
    content: str
    file_type: str  # 'json', 'yaml', 'text'


class BannerMessageUpdate(BaseModel):
    """Model for banner message updates."""
    messages: List[str]


class SystemStatus(BaseModel):
    """Model for system status information."""
    component: str
    status: str
    details: Optional[Dict[str, Any]] = None


def require_admin(current_user: str = Depends(get_current_user)) -> str:
    """Dependency to require admin group membership."""
    admin_group = os.getenv("ADMIN_GROUP", "admin")
    if not is_user_in_group(current_user, admin_group):
        raise HTTPException(
            status_code=403, 
            detail=f"Admin access required. User must be in '{admin_group}' group."
        )
    return current_user


def setup_configfilesadmin():
    """Set up configfilesadmin directory, copying from configfiles if empty."""
    admin_config_dir = Path("configfilesadmin")
    source_config_dir = Path("configfiles")
    
    # Create admin config directory if it doesn't exist
    admin_config_dir.mkdir(exist_ok=True)
    
    # Check if admin config directory is empty
    if not any(admin_config_dir.iterdir()):
        logger.info("configfilesadmin is empty, copying from configfiles")
        
        # Copy all files from configfiles to configfilesadmin
        for file_path in source_config_dir.glob("*"):
            if file_path.is_file():
                dest_path = admin_config_dir / file_path.name
                shutil.copy2(file_path, dest_path)
                logger.info(f"Copied {file_path} to {dest_path}")
    else:
        logger.info("configfilesadmin already contains files, skipping copy")


def get_admin_config_path(filename: str) -> Path:
    """Get the path to a file in configfilesadmin directory."""
    return Path("configfilesadmin") / filename


def get_file_content(file_path: Path) -> str:
    """Read file content safely with encoding error handling."""
    try:
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File {file_path.name} not found")
        
        # Try UTF-8 first, then fall back to UTF-8 with error handling
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Fall back to UTF-8 with error replacement
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


def write_file_content(file_path: Path, content: str, file_type: str = "text"):
    """Write file content safely with validation."""
    try:
        # Validate content based on file type
        if file_type == "json":
            json.loads(content)  # Validate JSON
        elif file_type == "yaml":
            yaml.safe_load(content)  # Validate YAML
        
        # Write to temporary file first, then rename for atomic operation
        temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
        
        # Remove temporary file if it already exists
        if temp_path.exists():
            temp_path.unlink()
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # On Windows, we need to remove the target file before rename
        # to avoid "file already exists" error
        if os.name == 'nt' and file_path.exists():
            file_path.unlink()
        
        # Atomic rename
        temp_path.rename(file_path)
        logger.info(f"Successfully updated {file_path}")
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error writing file: {str(e)}")


# --- Admin Dashboard Routes ---

@admin_router.get("/")
async def admin_dashboard(admin_user: str = Depends(require_admin)):
    """Get admin dashboard overview."""
    return {
        "message": "Admin Dashboard",
        "user": admin_user,
        "available_endpoints": [
            "/admin/banners",
            "/admin/mcp-config", 
            "/admin/llm-config",
            "/admin/help-config",
            "/admin/logs",
            "/admin/logs/download",
            "/admin/system-status",
            "/admin/mcp-health",
            "/admin/trigger-health-check",
            "/admin/reload-config"
        ]
    }


# --- Banner Management ---

@admin_router.get("/banners")
async def get_banner_config(admin_user: str = Depends(require_admin)):
    """Get current banner messages configuration."""
    try:
        # For now, we'll create a simple messages.txt file in configfilesadmin
        messages_file = get_admin_config_path("messages.txt")
        
        if not messages_file.exists():
            # Create with default content
            default_content = "System status: All services operational\n"
            write_file_content(messages_file, default_content)
        
        content = get_file_content(messages_file)
        messages = [line.strip() for line in content.splitlines() if line.strip()]
        
        return {
            "messages": messages,
            "file_path": str(messages_file),
            "last_modified": messages_file.stat().st_mtime if messages_file.exists() else None
        }
    except Exception as e:
        logger.error(f"Error getting banner config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/banners")
async def update_banner_config(
    update: BannerMessageUpdate,
    admin_user: str = Depends(require_admin)
):
    """Update banner messages configuration."""
    try:
        messages_file = get_admin_config_path("messages.txt")
        content = "\n".join(update.messages) + "\n" if update.messages else ""
        
        write_file_content(messages_file, content)
        
        logger.info(f"Banner messages updated by {admin_user}")
        return {
            "message": "Banner messages updated successfully",
            "messages": update.messages,
            "updated_by": admin_user
        }
    except Exception as e:
        logger.error(f"Error updating banner config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- MCP Configuration ---

@admin_router.get("/mcp-config")
async def get_mcp_config(admin_user: str = Depends(require_admin)):
    """Get current MCP server configuration."""
    try:
        mcp_file = get_admin_config_path("mcp.json")
        content = get_file_content(mcp_file)
        
        return {
            "content": content,
            "parsed": json.loads(content),
            "file_path": str(mcp_file),
            "last_modified": mcp_file.stat().st_mtime
        }
    except Exception as e:
        logger.error(f"Error getting MCP config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/mcp-config")
async def update_mcp_config(
    update: AdminConfigUpdate,
    admin_user: str = Depends(require_admin)
):
    """Update MCP server configuration."""
    try:
        mcp_file = get_admin_config_path("mcp.json")
        write_file_content(mcp_file, update.content, "json")
        
        logger.info(f"MCP configuration updated by {admin_user}")
        return {
            "message": "MCP configuration updated successfully",
            "updated_by": admin_user
        }
    except Exception as e:
        logger.error(f"Error updating MCP config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- LLM Configuration ---

@admin_router.get("/llm-config")
async def get_llm_config(admin_user: str = Depends(require_admin)):
    """Get current LLM configuration."""
    try:
        llm_file = get_admin_config_path("llmconfig.yml")
        content = get_file_content(llm_file)
        
        return {
            "content": content,
            "parsed": yaml.safe_load(content),
            "file_path": str(llm_file),
            "last_modified": llm_file.stat().st_mtime
        }
    except Exception as e:
        logger.error(f"Error getting LLM config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/llm-config")
async def update_llm_config(
    update: AdminConfigUpdate,
    admin_user: str = Depends(require_admin)
):
    """Update LLM configuration."""
    try:
        llm_file = get_admin_config_path("llmconfig.yml")
        write_file_content(llm_file, update.content, "yaml")
        
        logger.info(f"LLM configuration updated by {admin_user}")
        return {
            "message": "LLM configuration updated successfully", 
            "updated_by": admin_user
        }
    except Exception as e:
        logger.error(f"Error updating LLM config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Help Configuration ---

@admin_router.get("/help-config")
async def get_help_config(admin_user: str = Depends(require_admin)):
    """Get current help configuration."""
    try:
        help_file = get_admin_config_path("help-config.json")
        content = get_file_content(help_file)
        
        return {
            "content": content,
            "parsed": json.loads(content),
            "file_path": str(help_file),
            "last_modified": help_file.stat().st_mtime
        }
    except Exception as e:
        logger.error(f"Error getting help config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/help-config")
async def update_help_config(
    update: AdminConfigUpdate,
    admin_user: str = Depends(require_admin)
):
    """Update help configuration."""
    try:
        help_file = get_admin_config_path("help-config.json")
        write_file_content(help_file, update.content, "json")
        
        logger.info(f"Help configuration updated by {admin_user}")
        return {
            "message": "Help configuration updated successfully",
            "updated_by": admin_user
        }
    except Exception as e:
        logger.error(f"Error updating help config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Log Management ---

@admin_router.get("/logs")
async def get_app_logs(
    lines: int = 500,
    admin_user: str = Depends(require_admin)
):
    """Get application logs."""
    try:
        log_file = Path("logs/app.log")
        
        if not log_file.exists():
            return {
                "content": "No log file found",
                "lines": 0,
                "file_path": str(log_file)
            }
        
        # Read last N lines with encoding error handling
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
        except UnicodeDecodeError:
            # Fall back to UTF-8 with error replacement
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                all_lines = f.readlines()
        
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {
            "content": "".join(recent_lines),
            "lines": len(recent_lines),
            "total_lines": len(all_lines),
            "file_path": str(log_file),
            "last_modified": log_file.stat().st_mtime
        }
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/logs/download")
async def download_app_logs(admin_user: str = Depends(require_admin)):
    """Download the complete application log file."""
    try:
        log_file = Path("logs/app.log")
        
        if not log_file.exists():
            raise HTTPException(status_code=404, detail="Log file not found")
        
        # Import FileResponse here to avoid circular imports
        from fastapi.responses import FileResponse
        
        return FileResponse(
            path=str(log_file),
            filename=f"app_log_{log_file.stat().st_mtime}.log",
            media_type="text/plain"
        )
    except Exception as e:
        logger.error(f"Error downloading logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- System Status ---

@admin_router.get("/system-status")
async def get_system_status(admin_user: str = Depends(require_admin)):
    """Get overall system status including MCP servers and LLM health."""
    try:
        status_info = []
        
        # Check if configfilesadmin exists and has files
        admin_config_dir = Path("configfilesadmin")
        config_status = "healthy" if admin_config_dir.exists() and any(admin_config_dir.iterdir()) else "warning"
        status_info.append(SystemStatus(
            component="Configuration",
            status=config_status,
            details={
                "admin_config_dir": str(admin_config_dir),
                "files_count": len(list(admin_config_dir.glob("*"))) if admin_config_dir.exists() else 0
            }
        ))
        
        # Check log file
        log_file = Path("logs/app.log")
        log_status = "healthy" if log_file.exists() else "warning"
        status_info.append(SystemStatus(
            component="Logging",
            status=log_status,
            details={
                "log_file": str(log_file),
                "exists": log_file.exists(),
                "size_bytes": log_file.stat().st_size if log_file.exists() else 0
            }
        ))
        
        # Check MCP server health
        mcp_health = get_mcp_health_status()
        mcp_status = mcp_health.get("overall_status", "unknown")
        status_info.append(SystemStatus(
            component="MCP Servers",
            status=mcp_status,
            details={
                "healthy_count": mcp_health.get("healthy_count", 0),
                "total_count": mcp_health.get("total_count", 0),
                "last_check": mcp_health.get("last_check"),
                "check_interval": mcp_health.get("check_interval", 300)
            }
        ))
        
        return {
            "overall_status": "healthy" if all(s.status == "healthy" for s in status_info) else "warning",
            "components": [s.model_dump() for s in status_info],
            "checked_by": admin_user,
            "timestamp": log_file.stat().st_mtime if log_file.exists() else None
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Health Check Trigger ---

@admin_router.get("/mcp-health")
async def get_mcp_health(admin_user: str = Depends(require_admin)):
    """Get detailed MCP server health information."""
    try:
        health_summary = get_mcp_health_status()
        return {
            "health_summary": health_summary,
            "checked_by": admin_user
        }
    except Exception as e:
        logger.error(f"Error getting MCP health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/trigger-health-check")
async def trigger_health_check(admin_user: str = Depends(require_admin)):
    """Manually trigger MCP server health checks."""
    try:
        # Try to get the MCP manager from main application state
        mcp_manager = None
        try:
            from main import mcp_manager as main_mcp_manager
            mcp_manager = main_mcp_manager
        except ImportError:
            # In test environment, mcp_manager might not be available
            logger.warning("MCP manager not available for health check")
        
        # Trigger health check
        health_results = await trigger_mcp_health_check(mcp_manager)
        
        # Get summary
        health_summary = get_mcp_health_status()
        
        logger.info(f"Health check triggered by {admin_user}")
        return {
            "message": "MCP server health check completed",
            "triggered_by": admin_user,
            "summary": health_summary,
            "details": health_results
        }
    except Exception as e:
        logger.error(f"Error triggering health check: {e}")
        raise HTTPException(status_code=500, detail=f"Error triggering health check: {str(e)}")


@admin_router.post("/reload-config")
async def reload_configuration(admin_user: str = Depends(require_admin)):
    """Reload configuration from configfilesadmin files."""
    try:
        # Reload configuration from files
        config_manager.reload_configs()
        
        # Validate the reloaded configurations
        validation_status = config_manager.validate_config()
        
        # Get the updated configurations for verification
        llm_models = list(config_manager.llm_config.models.keys())
        mcp_servers = list(config_manager.mcp_config.servers.keys())
        
        logger.info(f"Configuration reloaded by {admin_user}")
        logger.info(f"Reloaded LLM models: {llm_models}")
        logger.info(f"Reloaded MCP servers: {mcp_servers}")
        
        return {
            "message": "Configuration reloaded successfully",
            "reloaded_by": admin_user,
            "validation_status": validation_status,
            "llm_models_count": len(llm_models),
            "mcp_servers_count": len(mcp_servers),
            "llm_models": llm_models,
            "mcp_servers": mcp_servers
        }
    except Exception as e:
        logger.error(f"Error reloading config: {e}")
        raise HTTPException(status_code=500, detail=f"Error reloading configuration: {str(e)}")


# --- Logging Management ---

@admin_router.get("/logs")
async def get_application_logs(
    admin_user: str = Depends(require_admin),
    limit: int = 100,
    level: str = None,
    search: str = None
):
    """Get application logs from the database."""
    try:
        import sqlite3
        from pathlib import Path
        
        db_path = Path("logs/app_logs.db")
        if not db_path.exists():
            return {
                "logs": [],
                "message": "No log database found",
                "retrieved_by": admin_user
            }
        
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Build query with optional filters
            query = "SELECT * FROM app_logs"
            params = []
            conditions = []
            
            if level:
                conditions.append("level = ?")
                params.append(level.upper())
            
            if search:
                conditions.append("(message LIKE ? OR logger_name LIKE ? OR user_email LIKE ?)")
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param])
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            logs = [dict(row) for row in cursor.fetchall()]
        
        return {
            "logs": logs,
            "count": len(logs),
            "filters": {"level": level, "search": search, "limit": limit},
            "retrieved_by": admin_user
        }
    except Exception as e:
        logger.error(f"Error retrieving logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/logs/file/{filename}")
async def get_log_file(
    filename: str,
    admin_user: str = Depends(require_admin)
):
    """Download a log file."""
    try:
        log_file = Path("logs") / filename
        if not log_file.exists():
            raise HTTPException(status_code=404, detail=f"Log file {filename} not found")
        
        # Security check - ensure the file is in the logs directory
        if not str(log_file.resolve()).startswith(str(Path("logs").resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
        
        logger.info(f"Log file {filename} downloaded by {admin_user}")
        return FileResponse(
            path=str(log_file),
            filename=filename,
            media_type='text/plain'
        )
    except Exception as e:
        logger.error(f"Error downloading log file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/llm-calls")
async def get_llm_call_logs(
    admin_user: str = Depends(require_admin),
    limit: int = 50,
    user_email: str = None,
    model_name: str = None,
    has_error: bool = None
):
    """Get LLM call logs from the database."""
    try:
        from logging_config import get_llm_call_logger
        
        llm_logger = get_llm_call_logger()
        if not llm_logger:
            return {
                "calls": [],
                "message": "LLM call logger not available",
                "retrieved_by": admin_user
            }
        
        import sqlite3
        from pathlib import Path
        
        db_path = Path("logs/llm_calls.db")
        if not db_path.exists():
            return {
                "calls": [],
                "message": "No LLM call database found",
                "retrieved_by": admin_user
            }
        
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Build query with optional filters
            query = "SELECT * FROM llm_calls"
            params = []
            conditions = []
            
            if user_email:
                conditions.append("user_email = ?")
                params.append(user_email)
            
            if model_name:
                conditions.append("model_name = ?")
                params.append(model_name)
            
            if has_error is not None:
                if has_error:
                    conditions.append("error_message IS NOT NULL")
                else:
                    conditions.append("error_message IS NULL")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            calls = [dict(row) for row in cursor.fetchall()]
        
        # Don't return full input/output for list view - only for detail view
        for call in calls:
            if len(call.get('input_messages', '')) > 500:
                call['input_messages'] = call['input_messages'][:500] + "... (truncated)"
            if len(call.get('output_response', '')) > 500:
                call['output_response'] = call['output_response'][:500] + "... (truncated)"
        
        return {
            "calls": calls,
            "count": len(calls),
            "filters": {
                "user_email": user_email,
                "model_name": model_name,
                "has_error": has_error,
                "limit": limit
            },
            "retrieved_by": admin_user
        }
    except Exception as e:
        logger.error(f"Error retrieving LLM call logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/llm-calls/{call_id}")
async def get_llm_call_detail(
    call_id: int,
    admin_user: str = Depends(require_admin)
):
    """Get detailed information about a specific LLM call."""
    try:
        import sqlite3
        from pathlib import Path
        
        db_path = Path("logs/llm_calls.db")
        if not db_path.exists():
            raise HTTPException(status_code=404, detail="LLM call database not found")
        
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM llm_calls WHERE id = ?",
                (call_id,)
            )
            call = cursor.fetchone()
        
        if not call:
            raise HTTPException(status_code=404, detail=f"LLM call {call_id} not found")
        
        logger.info(f"LLM call details {call_id} viewed by {admin_user}")
        return {
            "call": dict(call),
            "retrieved_by": admin_user
        }
    except Exception as e:
        logger.error(f"Error retrieving LLM call detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/llm-stats")
async def get_llm_usage_stats(
    admin_user: str = Depends(require_admin),
    days: int = 7
):
    """Get LLM usage statistics."""
    try:
        import sqlite3
        from pathlib import Path
        from datetime import datetime, timedelta
        
        db_path = Path("logs/llm_calls.db")
        if not db_path.exists():
            return {
                "stats": {},
                "message": "No LLM call database found",
                "retrieved_by": admin_user
            }
        
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            # Total calls and errors
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN error_message IS NOT NULL THEN 1 ELSE 0 END) as error_calls,
                    AVG(processing_time_ms) as avg_processing_time,
                    SUM(token_count_input) as total_input_tokens,
                    SUM(token_count_output) as total_output_tokens
                FROM llm_calls 
                WHERE timestamp >= ?
            """, (since_date,))
            summary = dict(cursor.fetchone())
            
            # Calls by model
            cursor = conn.execute("""
                SELECT model_name, COUNT(*) as count
                FROM llm_calls 
                WHERE timestamp >= ?
                GROUP BY model_name
                ORDER BY count DESC
            """, (since_date,))
            by_model = [dict(row) for row in cursor.fetchall()]
            
            # Calls by user
            cursor = conn.execute("""
                SELECT user_email, COUNT(*) as count
                FROM llm_calls 
                WHERE timestamp >= ?
                GROUP BY user_email
                ORDER BY count DESC
                LIMIT 10
            """, (since_date,))
            by_user = [dict(row) for row in cursor.fetchall()]
            
            # Daily usage
            cursor = conn.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as calls,
                    SUM(CASE WHEN error_message IS NOT NULL THEN 1 ELSE 0 END) as errors
                FROM llm_calls 
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """, (since_date,))
            daily_usage = [dict(row) for row in cursor.fetchall()]
        
        return {
            "stats": {
                "summary": summary,
                "by_model": by_model,
                "by_user": by_user,
                "daily_usage": daily_usage,
                "period_days": days
            },
            "retrieved_by": admin_user
        }
    except Exception as e:
        logger.error(f"Error retrieving LLM stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))