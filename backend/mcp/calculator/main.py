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


@mcp.tool
def add(a: Union[str, float], b: Union[str, float]) -> Dict[str, Any]:
    """
    Add two numbers.
    
    Args:
        a: First number (string or numerical)
        b: Second number (string or numerical)
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        a_num = to_float(a)
        b_num = to_float(b)
        result = a_num + b_num
        return {
            "operation": "addition",
            "operands": [a_num, b_num],
            "result": result
        }
    except Exception as e:
        return {"error": f"Addition error: {str(e)}"}


@mcp.tool
def subtract(a: Union[str, float], b: Union[str, float]) -> Dict[str, Any]:
    """
    Subtract two numbers.
    
    Args:
        a: First number (minuend) (string or numerical)
        b: Second number (subtrahend) (string or numerical)
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        a_num = to_float(a)
        b_num = to_float(b)
        result = a_num - b_num
        return {
            "operation": "subtraction",
            "operands": [a_num, b_num],
            "result": result
        }
    except Exception as e:
        return {"error": f"Subtraction error: {str(e)}"}


@mcp.tool
def multiply(a: Union[str, float], b: Union[str, float]) -> Dict[str, Any]:
    """
    Multiply two numbers.
    
    Args:
        a: First number (string or numerical)
        b: Second number (string or numerical)
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        a_num = to_float(a)
        b_num = to_float(b)
        result = a_num * b_num
        return {
            "operation": "multiplication",
            "operands": [a_num, b_num],
            "result": result
        }
    except Exception as e:
        return {"error": f"Multiplication error: {str(e)}"}


@mcp.tool
def divide(a: Union[str, float], b: Union[str, float]) -> Dict[str, Any]:
    """
    Divide two numbers.
    
    Args:
        a: Dividend (string or numerical)
        b: Divisor (string or numerical)
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        a_num = to_float(a)
        b_num = to_float(b)
        
        if b_num == 0:
            return {"error": "Division by zero"}
        
        result = a_num / b_num
        return {
            "operation": "division",
            "operands": [a_num, b_num],
            "result": result
        }
    except Exception as e:
        return {"error": f"Division error: {str(e)}"}


@mcp.tool
def power(base: Union[str, float], exponent: Union[str, float]) -> Dict[str, Any]:
    """
    Raise base to the power of exponent.
    
    Args:
        base: Base number (string or numerical)
        exponent: Power to raise the base to (string or numerical)
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        base_num = to_float(base)
        exponent_num = to_float(exponent)
        result = base_num ** exponent_num
        return {
            "operation": "power",
            "base": base_num,
            "exponent": exponent_num,
            "result": result
        }
    except Exception as e:
        return {"error": f"Power error: {str(e)}"}


@mcp.tool
def sqrt(number: Union[str, float]) -> Dict[str, Any]:
    """
    Calculate square root of a number.
    
    Args:
        number: Number to calculate square root of (string or numerical)
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        number_num = to_float(number)
        
        if number_num < 0:
            return {"error": "Cannot calculate square root of negative number"}
        
        result = math.sqrt(number_num)
        return {
            "operation": "square_root",
            "operand": number_num,
            "result": result
        }
    except Exception as e:
        return {"error": f"Square root error: {str(e)}"}


@mcp.tool
def factorial(n: Union[str, int]) -> Dict[str, Any]:
    """
    Calculate factorial of a number.
    
    Args:
        n: Non-negative integer to calculate factorial of (string or numerical)
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        n_int = to_int(n)
        
        if n_int < 0:
            return {"error": "Factorial requires a non-negative integer"}
        
        result = math.factorial(n_int)
        return {
            "operation": "factorial",
            "operand": n_int,
            "result": result
        }
    except Exception as e:
        return {"error": f"Factorial error: {str(e)}"}


@mcp.tool
def sin(angle: Union[str, float], degrees: Union[str, bool] = False) -> Dict[str, Any]:
    """
    Calculate sine of an angle.
    
    Args:
        angle: Angle value (string or numerical)
        degrees: Whether the angle is in degrees (default: False, radians)
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        angle_num = to_float(angle)
        
        # Handle degrees parameter conversion
        if isinstance(degrees, str):
            degrees_bool = degrees.lower() in ('true', '1', 'yes', 'on')
        else:
            degrees_bool = bool(degrees)
        
        if degrees_bool:
            angle_rad = math.radians(angle_num)
        else:
            angle_rad = angle_num
        
        result = math.sin(angle_rad)
        return {
            "operation": "sine",
            "angle": angle_num,
            "degrees": degrees_bool,
            "result": result
        }
    except Exception as e:
        return {"error": f"Sine error: {str(e)}"}


@mcp.tool
def cos(angle: Union[str, float], degrees: Union[str, bool] = False) -> Dict[str, Any]:
    """
    Calculate cosine of an angle.
    
    Args:
        angle: Angle value (string or numerical)
        degrees: Whether the angle is in degrees (default: False, radians)
        
    Returns:
        Dictionary with operation details and result
    """
    try:
        angle_num = to_float(angle)
        
        # Handle degrees parameter conversion
        if isinstance(degrees, str):
            degrees_bool = degrees.lower() in ('true', '1', 'yes', 'on')
        else:
            degrees_bool = bool(degrees)
        
        if degrees_bool:
            angle_rad = math.radians(angle_num)
        else:
            angle_rad = angle_num
        
        result = math.cos(angle_rad)
        return {
            "operation": "cosine",
            "angle": angle_num,
            "degrees": degrees_bool,
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
        # Convert to string if not already
        expression_str = str(expression)
        
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