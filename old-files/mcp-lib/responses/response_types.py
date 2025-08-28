"""Standard MCP response formats and types."""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass


@dataclass
class ToolResponse:
    """Standard tool response format."""
    content: Union[str, List[Dict[str, Any]]]
    isError: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format expected by MCP."""
        return {
            "content": [{"type": "text", "text": str(self.content)}] if isinstance(self.content, str) else self.content,
            "isError": self.isError
        }


@dataclass 
class ErrorResponse:
    """Standard error response format."""
    message: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_tool_response(self) -> ToolResponse:
        """Convert to ToolResponse format."""
        error_content = f"Error: {self.message}"
        if self.details:
            error_content += f" Details: {self.details}"
        return ToolResponse(content=error_content, isError=True)


@dataclass
class ProgressResponse:
    """Progress update response format."""
    progress: float  # 0.0 to 1.0
    message: str
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "type": "progress",
            "progress": self.progress,
            "message": self.message
        }
        if self.current_step:
            result["current_step"] = self.current_step
        if self.total_steps:
            result["total_steps"] = self.total_steps
        return result


def success_response(message: str, data: Optional[Dict[str, Any]] = None) -> ToolResponse:
    """Create a success response."""
    if data:
        content = [
            {"type": "text", "text": message},
            {"type": "text", "text": f"Data: {data}"}
        ]
    else:
        content = message
    return ToolResponse(content=content, isError=False)


def error_response(message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> ToolResponse:
    """Create an error response."""
    error = ErrorResponse(message=message, code=code, details=details)
    return error.to_tool_response()