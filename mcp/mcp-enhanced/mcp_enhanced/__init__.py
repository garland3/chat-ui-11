"""
MCP Enhanced - Server-side extension for fastmcp library

This library provides server-side utilities for MCP tools following the
MCP v2.1 Enhanced Specification. It focuses on server responsibilities:

- Filesystem sandboxing and security
- Response formatting utilities
- Secure output path helpers
- Simple artifact creation

Client responsibilities (handled by chat-ui client):
- Username injection
- File path resolution
- Timeout management and notifications
- Size-based artifact routing (base64 vs S3)
"""

from .decorator import enhanced_tool, validate_tool_signature
from .exceptions import (
    FileSizeExceededError,
    MCPEnhancedError,
    SecurityViolationError,
    TimeoutError,
)
from .responses import (
    artifact,
    create_mcp_response,
    deferred_artifact,
    error_response,
    success_response,
)
from .sandbox import FileSystemSandbox, normalize_filename
from .utils import (
    cleanup_user_files,
    ensure_user_directory,
    get_file_info,
    list_user_files,
    secure_output_path,
)

__version__ = "0.1.0"
__all__ = [
    # Main decorator
    "enhanced_tool",
    "validate_tool_signature",
    # Security
    "FileSystemSandbox",
    "normalize_filename",
    # Response builders
    "create_mcp_response",
    "artifact",
    "deferred_artifact",
    "error_response",
    "success_response",
    # Utilities
    "secure_output_path",
    "list_user_files",
    "cleanup_user_files",
    "get_file_info",
    "ensure_user_directory",
    # Exceptions
    "SecurityViolationError",
    "FileSizeExceededError",
    "TimeoutError",
    "MCPEnhancedError",
]
