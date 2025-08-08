#!/usr/bin/env python3
"""
Thinking MCP Server using FastMCP
Provides a thinking tool that processes thoughts and breaks down problems step by step.
"""

from typing import List, Dict, Any
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("Thinking")


@mcp.tool
def thinking(list_of_thoughts: List[str]) -> Dict[str, Any]:
    """
    Simple thinking tool that returns a list of thoughts.
    
    Args:
        list_of_thoughts: A list of thoughts, ideas, or problem descriptions
        
    Returns:
        Dictionary with the list of thoughts
    """
    try:
        if not list_of_thoughts:
            return {"error": "No thoughts provided"}
        
        return {
            "thoughts": list_of_thoughts,
            "count": len(list_of_thoughts)
        }
        
    except Exception as e:
        return {"error": f"Error processing thoughts: {str(e)}"}


if __name__ == "__main__":
    mcp.run()