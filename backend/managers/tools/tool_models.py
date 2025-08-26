"""Tool-related models and data structures."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class ToolCall:
    """Represents a tool call request."""

    id: str
    name: str
    arguments: Dict[str, Any]

    def __post_init__(self):
        if self.arguments is None:
            self.arguments = {}


@dataclass
class ToolResult:
    """Result of a tool execution."""

    tool_call_id: str
    success: bool
    content: str = ""
    error: Optional[str] = None
    artifacts: List[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = []


@dataclass
class ToolCapability:
    """Describes a tool's capabilities."""

    name: str
    description: str
    parameters: Dict[str, Any]
    server_name: str
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class ToolExecutionContext:
    """Context for tool execution."""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    file_context: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.file_context is None:
            self.file_context = []
        if self.metadata is None:
            self.metadata = {}
