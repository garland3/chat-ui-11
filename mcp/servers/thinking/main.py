#!/usr/bin/env python3
"""
Thinking MCP Server using FastMCP
Provides a thinking tool that processes thoughts and breaks down problems step by step.
"""

import logging
from typing import List, Dict, Any

# MCPs may run with CWD at their own tool folder; add parent (backend/mcp) for local imports
# sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# from _mcp_logging import init_mcp_logging, log_tool_call  # type: ignore
from fastmcp import FastMCP


# Initialize unified logging to write to logs/app.jsonl like the main app
# init_mcp_logging("thinking")
logger = logging.getLogger(__name__)
mcp = FastMCP("Thinking")


@mcp.tool
def thinking(list_of_thoughts: List[str]) -> Dict[str, Any]:
    """
    Structured thinking and ideation tool for organizing thoughts, brainstorming, and problem-solving analysis.

    This cognitive assistance tool helps organize and process complex thinking patterns:

    **Thought Organization:**
    - Structured collection and validation of multiple ideas
    - Thought counting and enumeration for analysis
    - List-based organization for sequential thinking
    - Input validation and error handling for robustness

    **Cognitive Support:**
    - Brainstorming session facilitation
    - Problem decomposition and analysis
    - Creative thinking process documentation
    - Decision-making support through thought structuring

    **Analysis Features:**
    - Thought count and quantity analysis
    - Input validation and quality checks
    - Structured output for further processing
    - Error handling for incomplete inputs

    **Use Cases:**
    - Strategic planning and decision making
    - Creative brainstorming sessions
    - Problem-solving workshops
    - Research idea generation
    - Project planning and ideation
    - Learning and knowledge organization

    **Workflow Integration:**
    - Compatible with other analytical tools
    - Structured output for downstream processing
    - Integration with documentation systems
    - Support for iterative thinking processes

    Args:
        list_of_thoughts: Collection of thoughts, ideas, or concepts to organize (array of strings)

    Returns:
        Dictionary containing:
        - thoughts: Organized list of all provided thoughts
        - count: Total number of thoughts processed
        Or error message if no thoughts provided or processing fails
    """
    try:
        # Log call with name + args (sanitized structure)
        # log_tool_call("thinking", list_of_thoughts=list_of_thoughts)

        if not list_of_thoughts:
            return {"results": {"error": "No thoughts provided"}}

        return {
            "results": {
                "thoughts": list_of_thoughts,
                "count": len(list_of_thoughts),
            }
        }

    except Exception as e:
        logger.exception("thinking_tool_error")
        return {"results": {"error": f"Error processing thoughts: {str(e)}"}}


if __name__ == "__main__":
    mcp.run()
