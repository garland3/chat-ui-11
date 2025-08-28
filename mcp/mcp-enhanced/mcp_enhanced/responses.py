"""
Response builders for MCP Enhanced tools.

Simple utilities for creating MCP v2.1 compliant responses.
Server-side only - focuses on proper response formatting.
"""

import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional


def create_mcp_response(
    results: Dict[str, Any],
    artifacts: Optional[List[Dict[str, Any]]] = None,
    deferred_artifacts: Optional[List[Dict[str, Any]]] = None,
    meta_data: Optional[Dict[str, Any]] = None,
    display: Optional[Dict[str, Any]] = None,
    retryable: bool = False,
) -> Dict[str, Any]:
    """
    Create a properly formatted MCP v2.1 response.

    The server provides artifact paths - the client handles size-based routing
    (converting to base64 or S3 based on file size).

    Args:
        results: The primary result object
        artifacts: List of artifact dictionaries with 'name', 'path', 'mime' fields
        deferred_artifacts: List of deferred artifact dictionaries
        meta_data: Additional metadata
        display: Display configuration hints
        retryable: Whether the operation can be retried
    """
    response = {"results": results}

    if artifacts:
        # Validate and enrich artifacts
        processed_artifacts = []
        for artifact in artifacts:
            processed = _process_artifact(artifact)
            if processed:
                processed_artifacts.append(processed)

        if processed_artifacts:
            response["artifacts"] = processed_artifacts

    if deferred_artifacts:
        response["deferred_artifacts"] = deferred_artifacts

    if meta_data:
        response["meta_data"] = meta_data

    if display:
        response["display"] = display

    if retryable:
        response["retryable"] = retryable

    return response


def _process_artifact(artifact: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process and validate an artifact dictionary"""
    if not isinstance(artifact, dict):
        return None

    # Required fields
    name = artifact.get("name")
    if not name:
        return None

    # Try to determine MIME type if not provided
    mime = artifact.get("mime")
    if not mime:
        path = artifact.get("path", "")
        mime = mimetypes.guess_type(path)[0] or "application/octet-stream"

    processed = {"name": name, "mime": mime}

    # Add optional fields
    for field in ["path", "description", "viewer", "category", "auto_open"]:
        if field in artifact:
            processed[field] = artifact[field]

    # Try to add size if path exists
    if "path" in artifact and artifact["path"]:
        try:
            size = Path(artifact["path"]).stat().st_size
            processed["size"] = size
        except (OSError, ValueError):
            pass

    return processed


def artifact(
    name: str,
    path: str,
    mime: Optional[str] = None,
    description: Optional[str] = None,
    viewer: Optional[str] = None,
    category: Optional[str] = None,
    auto_open: bool = False,
) -> Dict[str, Any]:
    """
    Create an artifact dictionary for MCP response.

    Args:
        name: File name (will be shown to user)
        path: Server file path (client will process for size-based routing)
        mime: MIME type (auto-detected if not provided)
        description: Human-readable description
        viewer: UI hint ('image', 'pdf', 'html', 'code', 'data')
        category: File category ('report', 'dataset', 'visualization', 'draft')
        auto_open: Whether to open file immediately
    """
    return {
        "name": name,
        "path": path,
        "mime": mime or mimetypes.guess_type(path)[0] or "application/octet-stream",
        "description": description,
        "viewer": viewer or _guess_viewer(mime or ""),
        "category": category,
        "auto_open": auto_open,
    }


def deferred_artifact(
    name: str,
    path: str,
    mime: Optional[str] = None,
    description: Optional[str] = None,
    reason: Optional[str] = None,
    next_actions: Optional[List[str]] = None,
    category: Optional[str] = None,
    expires_hours: int = 72,
) -> Dict[str, Any]:
    """
    Create a deferred artifact dictionary for MCP response.

    Deferred artifacts are files that need additional processing before
    being finalized (e.g., drafts that need editing).
    """
    return {
        "name": name,
        "path": path,
        "mime": mime or mimetypes.guess_type(path)[0] or "application/octet-stream",
        "description": description,
        "reason": reason,
        "next_actions": next_actions or [],
        "category": category,
        "expires_hours": expires_hours,
    }


def _guess_viewer(mime_type: str) -> str:
    """Guess appropriate viewer based on MIME type"""
    if mime_type.startswith("image/"):
        return "image"
    elif mime_type == "application/pdf":
        return "pdf"
    elif mime_type.startswith("text/html"):
        return "html"
    elif mime_type.startswith("text/") or "json" in mime_type or "javascript" in mime_type:
        return "code"
    elif any(data_type in mime_type for data_type in ["csv", "excel", "spreadsheet"]):
        return "data"
    else:
        return "code"  # Safe default


def error_response(
    message: str,
    reason: str = "ExecutionError",
    error_code: str = "E_EXECUTION_FAILED",
    retryable: bool = True,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    """
    meta_data = {
        "is_error": True,
        "reason": reason,
        "error_code": error_code,
        "retryable": retryable,
    }

    if details:
        meta_data["details"] = details

    return {"results": {"error": message}, "meta_data": meta_data}


def success_response(results: Dict[str, Any], message: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a simple success response.
    """
    if message and "message" not in results:
        results = {"message": message, **results}

    return {"results": results}
