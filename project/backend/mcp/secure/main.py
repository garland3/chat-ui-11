#!/usr/bin/env python3
"""
Log Reader MCP Server using FastMCP
Provides a tool to read logs/app.log contents.
"""

from pathlib import Path
from typing import Dict, Any

from fastmcp import FastMCP

mcp = FastMCP("LogReader")

BASE_LOG_PATH = Path("logs").resolve()
LOG_FILE = BASE_LOG_PATH / "app.log"

@mcp.tool
def read_log() -> Dict[str, Any]:
    try:
        if not BASE_LOG_PATH.exists():
            return {"error": "Log directory does not exist."}
        if not LOG_FILE.exists():
            return {"error": "Log file does not exist."}
        with LOG_FILE.open("r", encoding="utf-8") as f:
            content = f.read()
        return {
            "path": str(LOG_FILE),
            "content": content,
            "size": len(content),
        }
    except Exception as e:
        return {"error": f"Error reading log file: {str(e)}"}

if __name__ == "__main__":
    mcp.run()
