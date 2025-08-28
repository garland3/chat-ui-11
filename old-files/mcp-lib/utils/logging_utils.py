"""Shared logging initialization for MCP servers.

Ensures MCP modules write JSON logs to the same file as the main app
by reusing OpenTelemetryConfig from backend.core.otel_config.

Usage in an MCP entrypoint (before creating FastMCP):

    from backend.mcp._mcp_logging import init_mcp_logging, log_tool_call
    init_mcp_logging("thinking")

    # inside a tool function
    log_tool_call("thinking", list_of_thoughts=list_of_thoughts)

This respects APP_LOG_DIR and DEBUG_MODE, and configures the root logger
with the same JSON formatter used by the backend.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

_initialized = False
_log_file: Optional[Path] = None


def _ensure_project_root_on_syspath() -> None:
    """Put project root on sys.path so we can import backend.core.otel_config.

    This file lives at backend/mcp/_mcp_logging.py, so project root is two parents up.
    """
    project_root = Path(__file__).resolve().parents[2]
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def init_mcp_logging(service_name: str = "mcp") -> Path:
    """Initialize unified JSON logging for an MCP server.

    Creates/uses logs/app.jsonl via backend.core.otel_config.OpenTelemetryConfig.
    Safe to call multiple times; only the first call resets handlers.

    Returns the log file path.
    """
    global _initialized, _log_file
    if _initialized and _log_file is not None:
        return _log_file

    _ensure_project_root_on_syspath()

    from backend.core.otel_config import OpenTelemetryConfig  # type: ignore

    cfg = OpenTelemetryConfig(service_name=f"mcp-{service_name}")
    _log_file = cfg.get_log_file_path()
    _initialized = True
    return _log_file


def _preview_payload(payload: dict[str, Any], max_chars: int = 400) -> str:
    """Create a compact, JSON-like preview string for log message."""
    try:
        text = json.dumps(payload, default=str)
    except Exception:
        text = repr(payload)
    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text


def log_tool_call(tool_name: str, **payload: Any) -> None:
    """Log a structured MCP tool invocation.

    Fields will appear in JSON as extra_tool_name and extra_tool_payload.
    """
    logger = logging.getLogger("mcp.tool")
    msg = f"mcp.tool call: tool={tool_name} args={_preview_payload(payload)}"
    # stacklevel=2 attributes module/function/line to the caller (tool function)
    logger.info(
        msg,
        extra={"tool_name": tool_name, "tool_payload": payload},
        stacklevel=2,
    )
