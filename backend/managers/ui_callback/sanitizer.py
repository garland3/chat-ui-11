"""Sanitization utilities for tool arguments and results."""

from typing import Any, Dict, List


# Sensitive keys that should be masked (case-insensitive, substring matching)
SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "authorization",
    "cookie",
    "session",
    "bearer",
    "apikey",
    "clientsecret",
    "privatekey",
    "auth",
    "credential",
    "jwt",
    "oauth",
    "refresh_token",
    "access_token",
}

# More specific patterns for "key" to avoid false positives
KEY_PATTERNS = {"_key", "key_", "api_key", "private_key", "public_key", "secret_key"}

# Content length limits
MAX_STRING_LENGTH = 200
MAX_CONTENT_LENGTH = 2000
MAX_LIST_ITEMS = 25


def _is_sensitive_key(key: str) -> bool:
    """Check if a key name suggests sensitive data."""
    key_lower = key.lower()

    # Check standard sensitive keys
    for sensitive in SENSITIVE_KEYS:
        if sensitive in key_lower:
            return True

    # Check specific key patterns to avoid false positives
    for pattern in KEY_PATTERNS:
        if pattern in key_lower:
            return True

    return False


def _truncate_string(value: str, max_length: int) -> str:
    """Truncate a string with informative suffix."""
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}... (truncated, {len(value)} chars total)"


def _sanitize_value(value: Any, max_string_length: int = MAX_STRING_LENGTH) -> Any:
    """Sanitize a single value recursively."""
    if isinstance(value, str):
        return _truncate_string(value, max_string_length)
    elif isinstance(value, dict):
        return _sanitize_dict(value, max_string_length)
    elif isinstance(value, list):
        return _sanitize_list(value, max_string_length)
    elif value is None:
        return None
    else:
        # Convert non-JSON-serializable values to strings
        try:
            # Test if it's JSON serializable
            import json

            json.dumps(value)
            return value
        except (TypeError, ValueError):
            return str(value)


def _sanitize_dict(
    data: Dict[str, Any], max_string_length: int = MAX_STRING_LENGTH
) -> Dict[str, Any]:
    """Sanitize dictionary values, masking sensitive keys."""
    result = {}
    for key, value in data.items():
        if _is_sensitive_key(key):
            result[key] = "***MASKED***"
        else:
            result[key] = _sanitize_value(value, max_string_length)
    return result


def _sanitize_list(
    data: List[Any], max_string_length: int = MAX_STRING_LENGTH
) -> List[Any]:
    """Sanitize list items with size limits."""
    if len(data) <= MAX_LIST_ITEMS:
        return [_sanitize_value(item, max_string_length) for item in data]
    else:
        sanitized_items = [
            _sanitize_value(item, max_string_length) for item in data[:MAX_LIST_ITEMS]
        ]
        sanitized_items.append(f"(truncated list with {len(data)} items)")
        return sanitized_items


def sanitize_arguments(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize tool arguments for safe frontend display.

    Args:
        args: Tool arguments dictionary

    Returns:
        Sanitized arguments dictionary safe for JSON serialization
    """
    if not isinstance(args, dict):
        return {"error": "Arguments not a dictionary"}

    return _sanitize_dict(args)


def sanitize_tool_result(result) -> Dict[str, Any]:
    """
    Sanitize tool result for safe frontend display.

    Args:
        result: ToolResult object

    Returns:
        Sanitized result dictionary safe for JSON serialization
    """
    from managers.tools.tool_models import ToolResult

    if not isinstance(result, ToolResult):
        return {"error": "Invalid tool result object"}

    sanitized = {
        "success": result.success,
        "tool_call_id": result.tool_call_id,
    }

    # Sanitize content
    if result.content:
        if isinstance(result.content, str):
            try:
                import json

                parsed_content = json.loads(result.content)
                sanitized["content"] = _sanitize_value(parsed_content)
            except json.JSONDecodeError:
                sanitized["content"] = _truncate_string(
                    result.content, MAX_CONTENT_LENGTH
                )
        else:
            sanitized["content"] = _sanitize_value(result.content)
    elif result.success:
        sanitized["content"] = "OK"

    # Sanitize error message
    if result.error:
        sanitized["error"] = _truncate_string(result.error, MAX_CONTENT_LENGTH)

    # Sanitize artifacts - keep only metadata, not content bodies
    if result.artifacts:
        sanitized_artifacts = []
        for artifact in result.artifacts[:MAX_LIST_ITEMS]:
            if isinstance(artifact, dict):
                # Keep only safe metadata keys
                safe_artifact = {}
                safe_keys = {
                    "filename",
                    "content_type",
                    "size",
                    "name",
                    "type",
                    "format",
                }
                for key, value in artifact.items():
                    if key in safe_keys and not _is_sensitive_key(key):
                        safe_artifact[key] = _sanitize_value(value, MAX_STRING_LENGTH)
                sanitized_artifacts.append(safe_artifact)
            else:
                sanitized_artifacts.append(str(artifact)[:MAX_STRING_LENGTH])

        if len(result.artifacts) > MAX_LIST_ITEMS:
            sanitized_artifacts.append(
                f"(truncated, {len(result.artifacts)} artifacts total)"
            )

        sanitized["artifacts"] = sanitized_artifacts

    # Sanitize metadata - apply masking rules
    if result.meta_data:
        sanitized["meta_data"] = _sanitize_dict(result.meta_data)

    return sanitized


def parse_tool_name(full_tool_name: str) -> tuple[str, str]:
    """
    Parse a fully qualified tool name into server and tool components.

    Args:
        full_tool_name: Tool name like "server_toolName" or "just_tool_name"

    Returns:
        Tuple of (server_name, tool_name). Server name may be empty.
    """
    if "_" in full_tool_name:
        parts = full_tool_name.split("_", 1)  # Split only on first underscore
        return parts[0], parts[1]
    else:
        return "", full_tool_name
