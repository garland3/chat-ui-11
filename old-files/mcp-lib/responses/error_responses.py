"""Common error response patterns for MCP servers."""

from typing import Optional, Dict, Any
from .response_types import ToolResponse


def validation_error(field: str, value: Any, reason: str) -> ToolResponse:
    """Standard validation error response."""
    message = f"Validation error for '{field}': {reason}. Received value: {value}"
    return ToolResponse(content=message, isError=True)


def not_found_error(resource_type: str, identifier: str) -> ToolResponse:
    """Standard not found error response."""
    message = f"{resource_type} with identifier '{identifier}' not found"
    return ToolResponse(content=message, isError=True)


def permission_error(action: str, resource: str) -> ToolResponse:
    """Standard permission denied error response."""
    message = f"Permission denied: cannot {action} {resource}"
    return ToolResponse(content=message, isError=True)


def internal_error(operation: str, details: Optional[str] = None) -> ToolResponse:
    """Standard internal error response."""
    message = f"Internal error during {operation}"
    if details:
        message += f": {details}"
    return ToolResponse(content=message, isError=True)


def invalid_input_error(parameter: str, expected: str, received: Any) -> ToolResponse:
    """Standard invalid input error response."""
    message = f"Invalid input for parameter '{parameter}': expected {expected}, received {type(received).__name__}: {received}"
    return ToolResponse(content=message, isError=True)


def timeout_error(operation: str, timeout_seconds: int) -> ToolResponse:
    """Standard timeout error response."""
    message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"
    return ToolResponse(content=message, isError=True)


def rate_limit_error(retry_after_seconds: Optional[int] = None) -> ToolResponse:
    """Standard rate limit error response."""
    message = "Rate limit exceeded"
    if retry_after_seconds:
        message += f", retry after {retry_after_seconds} seconds"
    return ToolResponse(content=message, isError=True)