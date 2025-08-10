#!/usr/bin/env python3
"""
Filesystem MCP Server using FastMCP
Provides file system read/write operations through MCP protocol.
"""

from pathlib import Path
from typing import Any, Dict

from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("Filesystem")

# Base path for file operations (security constraint)
BASE_PATH = Path(".").resolve()


def _safe_path(path: str) -> Path:
    """Ensure path is within base directory for security."""
    requested_path = Path(path)
    if requested_path.is_absolute():
        full_path = requested_path
    else:
        full_path = BASE_PATH / requested_path
    
    resolved_path = full_path.resolve()
    
    # Ensure the path is within BASE_PATH
    try:
        resolved_path.relative_to(BASE_PATH)
    except ValueError:
        raise PermissionError("Access denied: path outside base directory")
    
    return resolved_path


@mcp.tool
def read_file(path: str) -> Dict[str, Any]:
    """
    Read contents of a file.
    
    Args:
        path: Path to the file to read
        
    Returns:
        Dictionary with file content, size, and path
    """
    try:
        file_path = _safe_path(path)
        if not file_path.exists():
            return {"error": f"File not found: {path}"}
        
        if file_path.is_dir():
            return {"error": f"Path is a directory: {path}"}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "content": content,
            "size": len(content),
            "path": str(file_path.relative_to(BASE_PATH))
        }
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Error reading file: {str(e)}"}


@mcp.tool
def write_file(path: str, content: str) -> Dict[str, Any]:
    """
    Write content to a file.
    
    Args:
        path: Path to the file to write
        content: Content to write to the file
        
    Returns:
        Dictionary with success status, path, and size
    """
    try:
        file_path = _safe_path(path)
        
        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "path": str(file_path.relative_to(BASE_PATH)),
            "size": len(content)
        }
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Error writing file: {str(e)}"}


@mcp.tool
def list_directory(path: str = ".") -> Dict[str, Any]:
    """
    List contents of a directory.
    
    Args:
        path: Path to the directory to list (defaults to current directory)
        
    Returns:
        Dictionary with directory path and list of items
    """
    try:
        dir_path = _safe_path(path)
        if not dir_path.exists():
            return {"error": f"Directory not found: {path}"}
        
        if not dir_path.is_dir():
            return {"error": f"Path is not a directory: {path}"}
        
        items = []
        for item in dir_path.iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None
            })
        
        return {
            "path": str(dir_path.relative_to(BASE_PATH)),
            "items": sorted(items, key=lambda x: (x["type"], x["name"]))
        }
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Error listing directory: {str(e)}"}


@mcp.tool
def create_directory(path: str) -> Dict[str, Any]:
    """
    Create a directory.
    
    Args:
        path: Path to the directory to create
        
    Returns:
        Dictionary with success status and path
    """
    try:
        dir_path = _safe_path(path)
        dir_path.mkdir(parents=True, exist_ok=True)
        
        return {
            "success": True,
            "path": str(dir_path.relative_to(BASE_PATH))
        }
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Error creating directory: {str(e)}"}


@mcp.tool
def delete_file(path: str) -> Dict[str, Any]:
    """
    Delete a file.
    
    Args:
        path: Path to the file to delete
        
    Returns:
        Dictionary with success status and path
    """
    try:
        file_path = _safe_path(path)
        if not file_path.exists():
            return {"error": f"File not found: {path}"}
        
        if file_path.is_dir():
            return {"error": f"Path is a directory (use rmdir): {path}"}
        
        file_path.unlink()
        return {
            "success": True,
            "path": str(file_path.relative_to(BASE_PATH))
        }
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Error deleting file: {str(e)}"}


@mcp.tool
def file_exists(path: str) -> Dict[str, Any]:
    """
    Check if a file or directory exists.
    
    Args:
        path: Path to check
        
    Returns:
        Dictionary with existence status and file type information
    """
    try:
        file_path = _safe_path(path)
        return {
            "exists": file_path.exists(),
            "is_file": file_path.is_file(),
            "is_directory": file_path.is_dir(),
            "path": str(file_path.relative_to(BASE_PATH))
        }
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Error checking file: {str(e)}"}


if __name__ == "__main__":
    mcp.run()