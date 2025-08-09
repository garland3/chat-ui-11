#!/usr/bin/env python3
"""
Calculator MCP Server using FastMCP
Provides mathematical operations through MCP protocol.
"""

import math
from typing import Any, Dict, Union

from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("Calculator")


def to_float(value: Union[str, int, float]) -> float:
    """Convert input to float, handling strings and numbers."""
    try:
        return float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Cannot convert '{value}' to a number")


def to_int(value: Union[str, int, float]) -> int:
    """Convert input to int, handling strings and numbers."""
    try:
        return int(float(value))  # Convert to float first to handle "5.0" -> 5
    except (ValueError, TypeError):
        raise ValueError(f"Cannot convert '{value}' to an integer")

import math
from typing import Dict, Any

@mcp.tool
def evaluate(expression: str) -> Dict[str, Any]:
    """
    Safely evaluate a mathematical expression with extensive math functions.
    
    Allowed functions/constants:
    abs, round, min, max, sum, pow, divmod,
    pi, e, tau, inf, nan,
    sin, cos, tan, asin, acos, atan, atan2, hypot, degrees, radians,
    sinh, cosh, tanh, asinh, acosh, atanh,
    exp, sqrt, log, log10, log2,
    ceil, floor, trunc, modf, copysign, fabs, fmod,
    factorial, comb, perm, gcd, lcm,
    isfinite, isinf, isnan

    Args:
        expression: Mathematical expression to evaluate (string)
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        expression_str = str(expression)

        # Safety check: prevent overly long or malicious expressions
        if len(expression_str) > 200:
            return {"error": "Expression too long"}

        # Allowed math functions and constants
        allowed_names = {
            # Built-ins
            "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
            "pow": pow, "divmod": divmod,

            # Constants
            "pi": math.pi, "e": math.e, "tau": math.tau, "inf": math.inf, "nan": math.nan,

            # Trigonometric
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
            "hypot": math.hypot, "degrees": math.degrees, "radians": math.radians,

            # Hyperbolic
            "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
            "asinh": math.asinh, "acosh": math.acosh, "atanh": math.atanh,

            # Exponential & logarithmic
            "exp": math.exp, "sqrt": math.sqrt, "log": math.log,
            "log10": math.log10, "log2": math.log2,

            # Rounding & numeric ops
            "ceil": math.ceil, "floor": math.floor, "trunc": math.trunc,
            "modf": math.modf, "copysign": math.copysign, "fabs": math.fabs, "fmod": math.fmod,

            # Combinatorics & number theory
            "factorial": math.factorial, "comb": math.comb, "perm": math.perm,
            "gcd": math.gcd, "lcm": math.lcm,

            # Float checks
            "isfinite": math.isfinite, "isinf": math.isinf, "isnan": math.isnan
        }

        # Evaluate safely
        result = eval(expression_str, {"__builtins__": {}}, allowed_names)

        return {
            "operation": "evaluate",
            "expression": expression_str,
            "result": result
        }
    except Exception as e:
        return {"error": f"Evaluation error: {str(e)}"}



if __name__ == "__main__":
    mcp.run()