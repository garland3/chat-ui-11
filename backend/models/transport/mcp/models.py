"""Common MCP models shared across the application (transport layer)."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from pydantic import BaseModel


class MCPServerConfigModel(BaseModel):
    """Pydantic model for MCP server configuration - used for JSON loading."""
    command: Optional[List[str]] = None
    args: List[str] = []
    url: Optional[str] = None
    transport: str = "stdio"
    cwd: Optional[str] = None
    env: Dict[str, str] = {}
    groups: List[str] = []
    description: str = ""
    author: str = "Unknown"
    short_description: str = ""
    help_email: str = ""


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server - runtime dataclass."""
    command: Optional[str] = None
    args: List[str] = None
    url: Optional[str] = None
    transport: str = 'stdio'  # 'stdio', 'http', 'sse'
    cwd: Optional[str] = None
    env: Dict[str, str] = None
    groups: List[str] = None  # Authorization groups
    description: str = ""  # Full description
    author: str = "Unknown"  # Author/team name
    short_description: str = ""  # Short description for UI
    help_email: str = ""  # Support contact
    
    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.env is None:
            self.env = {}
        if self.groups is None:
            self.groups = []
    
    @classmethod
    def from_pydantic(cls, pydantic_model: MCPServerConfigModel) -> 'MCPServerConfig':
        """Create MCPServerConfig from Pydantic model."""
        # Handle command format conversion
        command = pydantic_model.command
        if isinstance(command, list) and len(command) > 0:
            command_str = command[0]
            args = command[1:] if len(command) > 1 else []
        else:
            command_str = command
            args = pydantic_model.args
        
        return cls(
            command=command_str,
            args=args,
            url=pydantic_model.url,
            transport=pydantic_model.transport,
            cwd=pydantic_model.cwd,
            env=pydantic_model.env,
            groups=pydantic_model.groups,
            description=pydantic_model.description,
            author=pydantic_model.author,
            short_description=pydantic_model.short_description,
            help_email=pydantic_model.help_email
        )


@dataclass
class MCPServer:
    """Represents an MCP server."""
    name: str
    config: MCPServerConfig
    enabled: bool = True
    
    def is_stdio(self) -> bool:
        """Check if this is a STDIO server."""
        return self.config.transport == 'stdio'
    
    def is_http(self) -> bool:
        """Check if this is an HTTP/SSE server."""
        return self.config.transport in ['http', 'sse']
    
    def get_server_path(self) -> Optional[Path]:
        """Get the path to the server script for STDIO servers."""
        if not self.is_stdio():
            return None
        
        if self.config.command:
            return Path(self.config.command)
        else:
            # Default server location
            return Path("mcp/servers") / self.name / "main.py"


@dataclass
class MCPTool:
    """Represents an MCP tool."""
    name: str
    server_name: str
    description: str = ""
    input_schema: Dict[str, Any] = None
    tags: Set[str] = None
    enabled: bool = True
    
    def __post_init__(self):
        if self.input_schema is None:
            self.input_schema = {}
        if self.tags is None:
            self.tags = set()
    
    @property
    def full_name(self) -> str:
        """Get the fully qualified tool name."""
        return f"{self.server_name}_{self.name}"
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.full_name,
                "description": self.description,
                "parameters": self.input_schema
            }
        }


@dataclass
class MCPPrompt:
    """Represents an MCP prompt."""
    name: str
    server_name: str
    description: str = ""
    arguments: Dict[str, Any] = None
    enabled: bool = True
    
    def __post_init__(self):
        if self.arguments is None:
            self.arguments = {}
    
    @property
    def full_name(self) -> str:
        """Get the fully qualified prompt name."""
        return f"{self.server_name}_{self.name}"


@dataclass 
class MCPResource:
    """Represents an MCP resource."""
    uri: str
    name: str
    server_name: str
    description: str = ""
    mime_type: Optional[str] = None
    enabled: bool = True


@dataclass
class ToolCallResult:
    """Result of calling an MCP tool."""
    tool_name: str
    success: bool
    content: Any = None
    error: Optional[str] = None
    artifacts: List[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = []


class MCPConfig(BaseModel):
    """Configuration for MCP servers."""
    servers: Dict[str, MCPServerConfigModel] = {}
