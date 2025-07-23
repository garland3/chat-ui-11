#!/usr/bin/env python3
"""
Filesystem MCP Server
Provides file system read/write operations through MCP protocol.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List


class FilesystemMCPServer:
    """MCP server for file system operations."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path).resolve()
        self.tools = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "list_directory": self.list_directory,
            "create_directory": self.create_directory,
            "delete_file": self.delete_file,
            "file_exists": self.file_exists
        }
    
    def _safe_path(self, path: str) -> Path:
        """Ensure path is within base directory for security."""
        requested_path = Path(path)
        if requested_path.is_absolute():
            full_path = requested_path
        else:
            full_path = self.base_path / requested_path
        
        resolved_path = full_path.resolve()
        
        # Ensure the path is within base_path
        try:
            resolved_path.relative_to(self.base_path)
        except ValueError:
            raise PermissionError(f"Access denied: path outside base directory")
        
        return resolved_path
    
    async def read_file(self, path: str) -> Dict[str, Any]:
        """Read file contents."""
        try:
            file_path = self._safe_path(path)
            if not file_path.exists():
                return {"error": f"File not found: {path}"}
            
            if file_path.is_dir():
                return {"error": f"Path is a directory: {path}"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "content": content,
                "size": len(content),
                "path": str(file_path.relative_to(self.base_path))
            }
        except PermissionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Error reading file: {str(e)}"}
    
    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to file."""
        try:
            file_path = self._safe_path(path)
            
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "path": str(file_path.relative_to(self.base_path)),
                "size": len(content)
            }
        except PermissionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Error writing file: {str(e)}"}
    
    async def list_directory(self, path: str = ".") -> Dict[str, Any]:
        """List directory contents."""
        try:
            dir_path = self._safe_path(path)
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
                "path": str(dir_path.relative_to(self.base_path)),
                "items": sorted(items, key=lambda x: (x["type"], x["name"]))
            }
        except PermissionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Error listing directory: {str(e)}"}
    
    async def create_directory(self, path: str) -> Dict[str, Any]:
        """Create a directory."""
        try:
            dir_path = self._safe_path(path)
            dir_path.mkdir(parents=True, exist_ok=True)
            
            return {
                "success": True,
                "path": str(dir_path.relative_to(self.base_path))
            }
        except PermissionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Error creating directory: {str(e)}"}
    
    async def delete_file(self, path: str) -> Dict[str, Any]:
        """Delete a file."""
        try:
            file_path = self._safe_path(path)
            if not file_path.exists():
                return {"error": f"File not found: {path}"}
            
            if file_path.is_dir():
                return {"error": f"Path is a directory (use rmdir): {path}"}
            
            file_path.unlink()
            return {
                "success": True,
                "path": str(file_path.relative_to(self.base_path))
            }
        except PermissionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Error deleting file: {str(e)}"}
    
    async def file_exists(self, path: str) -> Dict[str, Any]:
        """Check if file exists."""
        try:
            file_path = self._safe_path(path)
            return {
                "exists": file_path.exists(),
                "is_file": file_path.is_file(),
                "is_directory": file_path.is_dir(),
                "path": str(file_path.relative_to(self.base_path))
            }
        except PermissionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Error checking file: {str(e)}"}
    
    def get_tools_list(self) -> List[Dict[str, Any]]:
        """Get list of available tools."""
        return [
            {
                "name": "read_file",
                "description": "Read contents of a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file to read"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "description": "Write content to a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file to write"},
                        "content": {"type": "string", "description": "Content to write to the file"}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "list_directory",
                "description": "List contents of a directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the directory to list", "default": "."}
                    }
                }
            },
            {
                "name": "create_directory",
                "description": "Create a directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the directory to create"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "delete_file",
                "description": "Delete a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file to delete"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "file_exists",
                "description": "Check if a file or directory exists",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to check"}
                    },
                    "required": ["path"]
                }
            }
        ]
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request."""
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "tools/list":
            return {
                "tools": self.get_tools_list()
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            if tool_name in self.tools:
                result = await self.tools[tool_name](**tool_args)
                return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        else:
            return {"error": f"Unknown method: {method}"}


async def main():
    """Main server loop."""
    server = FilesystemMCPServer()
    
    while True:
        try:
            # Read request from stdin
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )
            
            if not line:
                break
            
            request = json.loads(line.strip())
            response = await server.handle_request(request)
            
            # Send response to stdout
            print(json.dumps(response))
            sys.stdout.flush()
            
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON"}))
            sys.stdout.flush()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(json.dumps({"error": f"Server error: {str(e)}"}))
            sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())