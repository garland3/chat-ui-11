"""Tool notification functions for sending callbacks to the UI."""

import logging
from typing import Any, Awaitable, Callable, Dict, Optional
from uuid import UUID

from .sanitizer import sanitize_arguments, sanitize_tool_result, parse_tool_name
from managers.tools.tool_models import ToolCall, ToolResult

logger = logging.getLogger(__name__)


async def notify_tool_start(
    tool_call: ToolCall,
    session_id: UUID,
    update_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
) -> None:
    """
    Send tool_start callback to the frontend.

    Args:
        tool_call: The tool call being started
        session_id: Session ID for the chat
        update_callback: Callback function to send the message
    """
    if not update_callback:
        return

    server_name, tool_name = parse_tool_name(tool_call.name)
    tool_start_message = {
        "type": "tool_start",
        "tool_call_id": tool_call.id,
        "tool_name": tool_name,
        "server_name": server_name,
        "arguments": sanitize_arguments(tool_call.arguments),
        "session_id": str(session_id),
    }

    try:
        await update_callback(tool_start_message)
        logger.debug(f"Sent tool_start callback for {tool_call.name}")
    except Exception as callback_error:
        logger.error(f"Error sending tool_start callback: {callback_error}")


async def notify_tool_complete(
    tool_call: ToolCall,
    result: ToolResult,
    session_id: UUID,
    update_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
) -> None:
    """
    Send tool_complete callback to the frontend.

    Args:
        tool_call: The tool call that completed
        result: The tool execution result
        session_id: Session ID for the chat
        update_callback: Callback function to send the message
    """
    if not update_callback:
        return

    server_name, tool_name = parse_tool_name(tool_call.name)
    tool_complete_message = {
        "type": "tool_complete",
        "tool_call_id": tool_call.id,
        "tool_name": tool_name,
        "server_name": server_name,
        "success": result.success,
        "result": sanitize_tool_result(result),
    }

    try:
        await update_callback(tool_complete_message)
        logger.debug(f"Sent tool_complete callback for {tool_call.name}")
    except Exception as callback_error:
        logger.error(f"Error sending tool_complete callback: {callback_error}")


async def notify_tool_error(
    tool_call: ToolCall,
    error: str,
    session_id: UUID,
    update_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]],
) -> None:
    """
    Send tool_error callback to the frontend.

    Args:
        tool_call: The tool call that failed
        error: The error message
        session_id: Session ID for the chat
        update_callback: Callback function to send the message
    """
    if not update_callback:
        return

    server_name, tool_name = parse_tool_name(tool_call.name)
    tool_error_message = {
        "type": "tool_error",
        "tool_call_id": tool_call.id,
        "tool_name": tool_name,
        "server_name": server_name,
        "error": str(error)[:500],  # Truncate error message
    }

    try:
        await update_callback(tool_error_message)
        logger.debug(f"Sent tool_error callback for {tool_call.name}")
    except Exception as callback_error:
        logger.error(f"Error sending tool_error callback: {callback_error}")
