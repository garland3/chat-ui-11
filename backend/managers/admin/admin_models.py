"""Admin models for configuration management and system monitoring.

Pydantic models used by admin endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, field_validator


class AdminConfigUpdate(BaseModel):
    """Model for updating configuration files."""

    content: str
    file_type: str  # 'json', 'yaml', 'text'


class BannerMessageUpdate(BaseModel):
    """Model for updating banner messages."""

    messages: List[str]


class ConfigViewResponse(BaseModel):
    """Response model for viewing all configurations."""

    app_settings: Dict[str, Any]
    llm_config: Dict[str, Any]
    mcp_config: Dict[str, Any]
    config_validation: Dict[str, bool]


class LogMetadata(BaseModel):
    """Metadata for log viewer response."""

    total_entries: int
    unique_modules: List[str]
    unique_levels: List[str]
    log_file_path: str
    requested_lines: int
    filters_applied: Dict[str, str | None]


class LogEntry(BaseModel):
    """Individual log entry structure."""

    timestamp: str
    level: str
    module: str
    logger: str
    function: str
    message: str
    trace_id: str = ""
    span_id: str = ""
    line: str = ""
    thread_name: str = ""
    extras: Dict[str, Any] = {}

    @field_validator("line", mode="before")
    @classmethod
    def convert_line_to_str(cls, v):
        """Convert line number to string if it's an integer."""
        return str(v) if v is not None else ""


class EnhancedLogsResponse(BaseModel):
    """Response model for enhanced log viewer."""

    entries: List[LogEntry]
    metadata: LogMetadata


class McpReloadResponse(BaseModel):
    """Response model for MCP server reload."""

    message: str
    servers: List[str]
    tool_counts: Dict[str, int]
    prompt_counts: Dict[str, int]
    reloaded_by: str
