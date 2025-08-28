"""
Server-side enhanced decorator for MCP tools.

This decorator focuses on server-side responsibilities:
- Filesystem sandboxing for security
- Response formatting helpers
- Path validation utilities

Client-side responsibilities (handled by the chat-ui client):
- Username injection
- File path resolution
- Timeout management and notifications
- Size-based artifact routing (base64 vs S3)
"""

import inspect
from functools import wraps
from typing import Any, Callable, Dict

from .responses import create_mcp_response
from .sandbox import FileSystemSandbox


def enhanced_tool(enable_sandbox: bool = True):
    """
    Server-side decorator for MCP tools with filesystem sandboxing.

    This decorator provides:
    - Automatic filesystem sandboxing (restricts writes to /tmp/{username}/)
    - Input validation for username parameter
    - Simple response formatting

    The client is responsible for:
    - Injecting the username parameter
    - Resolving file paths before calling the tool
    - Managing timeouts and progress reporting
    - Processing artifact paths for size-based routing

    Args:
        enable_sandbox: Whether to enable filesystem sandboxing (default: True)

    Usage:
        @enhanced_tool()
        def my_tool(filename: str, username: str) -> dict:
            # filename is already resolved by client to secure path
            # username is already injected by client

            df = pd.read_csv(filename)
            output_path = secure_output_path(username, "result.csv")
            df.to_csv(output_path)

            return create_mcp_response(
                results={"processed": len(df)},
                artifacts=[{
                    "name": "result.csv",
                    "path": output_path,
                    "mime": "text/csv"
                }]
            )
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Any]:
            """Wrapper that provides sandboxing and validation"""

            # Validate username parameter exists
            username = kwargs.get("username")
            if not username:
                return {
                    "results": {"error": "Missing username parameter"},
                    "meta_data": {
                        "is_error": True,
                        "reason": "MissingUsername",
                        "error_code": "E_NO_USERNAME",
                        "retryable": False,
                    },
                }

            try:
                if enable_sandbox:
                    # Run with filesystem sandbox
                    sandbox = FileSystemSandbox(f"/tmp/{username}")

                    with sandbox.sandbox_context():
                        result = func(*args, **kwargs)
                else:
                    # Run without sandbox
                    result = func(*args, **kwargs)

                # Ensure result is a proper MCP response
                if isinstance(result, dict) and "results" in result:
                    return result
                else:
                    # Convert simple return to MCP format
                    return create_mcp_response(
                        results=result if isinstance(result, dict) else {"status": str(result)}
                    )

            except Exception as e:
                return {
                    "results": {"error": f"Tool execution failed: {str(e)}"},
                    "meta_data": {
                        "is_error": True,
                        "reason": "ExecutionError",
                        "error_code": "E_EXECUTION_FAILED",
                        "details": {"exception_type": type(e).__name__},
                        "retryable": True,
                    },
                }

        # Mark as enhanced tool
        wrapper.__enhanced_tool__ = True
        wrapper.__original_func__ = func
        wrapper.__enable_sandbox__ = enable_sandbox

        return wrapper

    return decorator


def validate_tool_signature(func: Callable) -> Dict[str, Any]:
    """
    Validate that a function signature follows MCP Enhanced patterns.

    Returns validation info and recommendations.
    """
    sig = inspect.signature(func)

    validation = {
        "valid": True,
        "has_username": "username" in sig.parameters,
        "has_filename": "filename" in sig.parameters,
        "has_filenames": "filenames" in sig.parameters,
        "warnings": [],
        "recommendations": [],
    }

    # Check for username parameter when tool handles files
    if (validation["has_filename"] or validation["has_filenames"]) and not validation[
        "has_username"
    ]:
        validation["warnings"].append(
            "Tools that handle files should include 'username: str' parameter for security"
        )

    # Check return type hint
    if sig.return_annotation == inspect.Signature.empty:
        validation["recommendations"].append("Add return type hint: -> Dict[str, Any]")

    return validation
