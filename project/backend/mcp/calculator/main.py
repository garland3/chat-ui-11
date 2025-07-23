#!/usr/bin/env python3
"""
Calculator MCP Server using FastMCP
Provides mathematical operations through MCP protocol.
"""

import math
from typing import Any, Dict

from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("Calculator")


@mcp.tool
def add(a: float, b: float) -> Dict[str, Any]:
    """
    Add two numbers.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        result = a + b
        return {
            "operation": "addition",
            "operands": [a, b],
            "result": result
        }
    except Exception as e:
        return {"error": f"Addition error: {str(e)}"}


@mcp.tool
def subtract(a: float, b: float) -> Dict[str, Any]:
    """
    Subtract two numbers.
    
    Args:
        a: First number (minuend)
        b: Second number (subtrahend)
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        result = a - b
        return {
            "operation": "subtraction",
            "operands": [a, b],
            "result": result
        }
    except Exception as e:
        return {"error": f"Subtraction error: {str(e)}"}


@mcp.tool
def multiply(a: float, b: float) -> Dict[str, Any]:
    """
    Multiply two numbers.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        result = a * b
        return {
            "operation": "multiplication",
            "operands": [a, b],
            "result": result
        }
    except Exception as e:
        return {"error": f"Multiplication error: {str(e)}"}


@mcp.tool
def divide(a: float, b: float) -> Dict[str, Any]:
    """
    Divide two numbers.
    
    Args:
        a: Dividend
        b: Divisor
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        if b == 0:
            return {"error": "Division by zero"}
        
        result = a / b
        return {
            "operation": "division",
            "operands": [a, b],
            "result": result
        }
    except Exception as e:
        return {"error": f"Division error: {str(e)}"}


@mcp.tool
def power(base: float, exponent: float) -> Dict[str, Any]:
    """
    Raise base to the power of exponent.
    
    Args:
        base: Base number
        exponent: Power to raise the base to
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        result = base ** exponent
        return {
            "operation": "power",
            "base": base,
            "exponent": exponent,
            "result": result
        }
    except Exception as e:
        return {"error": f"Power error: {str(e)}"}


@mcp.tool
def sqrt(number: float) -> Dict[str, Any]:
    """
    Calculate square root of a number.
    
    Args:
        number: Number to calculate square root of
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        if number < 0:
            return {"error": "Cannot calculate square root of negative number"}
        
        result = math.sqrt(number)
        return {
            "operation": "square_root",
            "operand": number,
            "result": result
        }
    except Exception as e:
        return {"error": f"Square root error: {str(e)}"}


@mcp.tool
def factorial(n: int) -> Dict[str, Any]:
    """
    Calculate factorial of a number.
    
    Args:
        n: Non-negative integer to calculate factorial of
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        if not isinstance(n, int) or n < 0:
            return {"error": "Factorial requires a non-negative integer"}
        
        result = math.factorial(n)
        return {
            "operation": "factorial",
            "operand": n,
            "result": result
        }
    except Exception as e:
        return {"error": f"Factorial error: {str(e)}"}


@mcp.tool
def sin(angle: float, degrees: bool = False) -> Dict[str, Any]:
    """
    Calculate sine of an angle.
    
    Args:
        angle: Angle value
        degrees: Whether the angle is in degrees (default: False, radians)
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        if degrees:
            angle = math.radians(angle)
        
        result = math.sin(angle)
        return {
            "operation": "sine",
            "angle": angle,
            "degrees": degrees,
            "result": result
        }
    except Exception as e:
        return {"error": f"Sine error: {str(e)}"}


@mcp.tool
def cos(angle: float, degrees: bool = False) -> Dict[str, Any]:
    """
    Calculate cosine of an angle.
    
    Args:
        angle: Angle value
        degrees: Whether the angle is in degrees (default: False, radians)
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        if degrees:
            angle = math.radians(angle)
        
        result = math.cos(angle)
        return {
            "operation": "cosine",
            "angle": angle,
            "degrees": degrees,
            "result": result
        }
    except Exception as e:
        return {"error": f"Cosine error: {str(e)}"}


@mcp.tool
def evaluate(expression: str) -> Dict[str, Any]:
    """
    Safely evaluate a mathematical expression.
    
    Args:
        expression: Mathematical expression to evaluate
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        # Only allow safe mathematical operations
        allowed_names = {
            "abs": abs, "round": round, "min": min, "max": max,
            "sum": sum, "pow": pow, "divmod": divmod,
            "pi": math.pi, "e": math.e,
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
            "ceil": math.ceil, "floor": math.floor,
            "factorial": math.factorial, "degrees": math.degrees,
            "radians": math.radians
        }
        
        # Evaluate expression in restricted environment
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        
        return {
            "operation": "evaluate",
            "expression": expression,
            "result": result
        }
    except Exception as e:
        return {"error": f"Evaluation error: {str(e)}"}


if __name__ == "__main__":
    mcp.run()