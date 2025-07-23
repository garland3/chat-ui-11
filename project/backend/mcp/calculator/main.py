#!/usr/bin/env python3
"""
Calculator MCP Server
Provides basic mathematical operations through MCP protocol.
"""

import asyncio
import json
import sys
import math
from typing import Any, Dict, List, Union


class CalculatorMCPServer:
    """MCP server for mathematical calculations."""
    
    def __init__(self):
        self.tools = {
            "add": self.add,
            "subtract": self.subtract,
            "multiply": self.multiply,
            "divide": self.divide,
            "power": self.power,
            "sqrt": self.sqrt,
            "factorial": self.factorial,
            "sin": self.sin,
            "cos": self.cos,
            "tan": self.tan,
            "log": self.log,
            "evaluate": self.evaluate
        }
    
    async def add(self, a: float, b: float) -> Dict[str, Any]:
        """Add two numbers."""
        try:
            result = a + b
            return {
                "operation": "addition",
                "operands": [a, b],
                "result": result
            }
        except Exception as e:
            return {"error": f"Addition error: {str(e)}"}
    
    async def subtract(self, a: float, b: float) -> Dict[str, Any]:
        """Subtract two numbers."""
        try:
            result = a - b
            return {
                "operation": "subtraction",
                "operands": [a, b],
                "result": result
            }
        except Exception as e:
            return {"error": f"Subtraction error: {str(e)}"}
    
    async def multiply(self, a: float, b: float) -> Dict[str, Any]:
        """Multiply two numbers."""
        try:
            result = a * b
            return {
                "operation": "multiplication",
                "operands": [a, b],
                "result": result
            }
        except Exception as e:
            return {"error": f"Multiplication error: {str(e)}"}
    
    async def divide(self, a: float, b: float) -> Dict[str, Any]:
        """Divide two numbers."""
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
    
    async def power(self, base: float, exponent: float) -> Dict[str, Any]:
        """Raise base to the power of exponent."""
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
    
    async def sqrt(self, number: float) -> Dict[str, Any]:
        """Calculate square root."""
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
    
    async def factorial(self, n: int) -> Dict[str, Any]:
        """Calculate factorial of a number."""
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
    
    async def sin(self, angle: float, degrees: bool = False) -> Dict[str, Any]:
        """Calculate sine of an angle."""
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
    
    async def cos(self, angle: float, degrees: bool = False) -> Dict[str, Any]:
        """Calculate cosine of an angle."""
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
    
    async def tan(self, angle: float, degrees: bool = False) -> Dict[str, Any]:
        """Calculate tangent of an angle."""
        try:
            if degrees:
                angle = math.radians(angle)
            
            result = math.tan(angle)
            return {
                "operation": "tangent",
                "angle": angle,
                "degrees": degrees,
                "result": result
            }
        except Exception as e:
            return {"error": f"Tangent error: {str(e)}"}
    
    async def log(self, number: float, base: float = math.e) -> Dict[str, Any]:
        """Calculate logarithm of a number."""
        try:
            if number <= 0:
                return {"error": "Logarithm requires a positive number"}
            
            if base <= 0 or base == 1:
                return {"error": "Logarithm base must be positive and not equal to 1"}
            
            if base == math.e:
                result = math.log(number)
            else:
                result = math.log(number, base)
            
            return {
                "operation": "logarithm",
                "number": number,
                "base": base,
                "result": result
            }
        except Exception as e:
            return {"error": f"Logarithm error: {str(e)}"}
    
    async def evaluate(self, expression: str) -> Dict[str, Any]:
        """Evaluate a mathematical expression safely."""
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
    
    def get_tools_list(self) -> List[Dict[str, Any]]:
        """Get list of available tools."""
        return [
            {
                "name": "add",
                "description": "Add two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"}
                    },
                    "required": ["a", "b"]
                }
            },
            {
                "name": "subtract",
                "description": "Subtract two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"}
                    },
                    "required": ["a", "b"]
                }
            },
            {
                "name": "multiply",
                "description": "Multiply two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"}
                    },
                    "required": ["a", "b"]
                }
            },
            {
                "name": "divide",
                "description": "Divide two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "Dividend"},
                        "b": {"type": "number", "description": "Divisor"}
                    },
                    "required": ["a", "b"]
                }
            },
            {
                "name": "power",
                "description": "Raise base to the power of exponent",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "base": {"type": "number", "description": "Base number"},
                        "exponent": {"type": "number", "description": "Exponent"}
                    },
                    "required": ["base", "exponent"]
                }
            },
            {
                "name": "sqrt",
                "description": "Calculate square root of a number",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "number": {"type": "number", "description": "Number to calculate square root of"}
                    },
                    "required": ["number"]
                }
            },
            {
                "name": "evaluate",
                "description": "Safely evaluate a mathematical expression",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "Mathematical expression to evaluate"}
                    },
                    "required": ["expression"]
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
    server = CalculatorMCPServer()
    
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