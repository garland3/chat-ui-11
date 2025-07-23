#!/usr/bin/env python3
"""
RAG MCP Server using FastMCP
Provides multiple data source retrieval functions as MCP tools.
"""

from fastmcp import FastMCP
from typing import Dict, Any

mcp = FastMCP("RAG")

# Placeholder functions for data sources
def get_engineering_data() -> Dict[str, Any]:
    return {
        "source": "engineering",
        "content": (
            "Airplane structural analysis indicates the wing load distribution "
            "is within safety margins. Composite materials reduce weight by 15%."
        )
    }

def get_financial_data() -> Dict[str, Any]:
    return {
        "source": "financial",
        "content": (
            "The airplane project budget shows a 10% increase due to material costs "
            "and delayed delivery schedules impacting Q3 projections."
        )
    }

# Map data source names to functions
data_sources = {
    "engineering_data": get_engineering_data,
    "financial_data": get_financial_data,
}

# Programmatically add MCP tools for each data source
for name, func in data_sources.items():
    mcp.tool(name)(func)

if __name__ == "__main__":
    mcp.run()

