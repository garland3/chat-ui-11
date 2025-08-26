"""Domain messaging models previously under common.models.common_models."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class LLMResponse:
    """Response from LLM."""

    def __init__(
        self,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        model_used: Optional[str] = None,
    ):
        self.content = content
        self.tool_calls = tool_calls
        self.model_used = model_used

    def has_tool_calls(self) -> bool:
        """Check if response has tool calls."""
        return bool(self.tool_calls)


class MessageRole(Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageType(Enum):
    """Message type enumeration."""

    CHAT = "chat"
    CHAT_RESPONSE = "chat_response"
    ERROR = "error"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    AGENT_UPDATE = "agent_update"
    INTERMEDIATE_UPDATE = "intermediate_update"
    DOWNLOAD_FILE = "download_file"
    FILE_DOWNLOAD = "file_download"


@dataclass
class Message:
    """Domain model for a chat message."""

    id: UUID = field(default_factory=uuid4)
    role: MessageRole = MessageRole.USER
    content: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    def to_llm_format(self) -> Dict[str, Any]:
        """Convert to LLM API format."""
        # For tool messages, ensure content is a JSON string if it's a dict
        content = self.content
        if self.role == MessageRole.TOOL and isinstance(self.content, dict):
            content = json.dumps(self.content)
        
        result = {
            "role": self.role.value,
            "content": content,
        }
        # For tool messages, include tool_call_id from metadata if present
        if self.role == MessageRole.TOOL and "tool_call_id" in self.metadata:
            result["tool_call_id"] = self.metadata["tool_call_id"]

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            role=MessageRole(data.get("role", "user")),
            content=data.get("content", ""),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.now(timezone.utc),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ToolCall:
    """Domain model for a tool call."""

    id: str
    name: str
    arguments: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
        }


@dataclass
class ToolResult:
    """Domain model for a tool result with v2 MCP support."""

    tool_call_id: str
    content: str
    success: bool = True
    error: Optional[str] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    display_config: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "tool_call_id": self.tool_call_id,
            "content": self.content,
            "success": self.success,
            "error": self.error,
            "artifacts": self.artifacts,
        }
        if self.display_config:
            result["display_config"] = self.display_config
        if self.meta_data:
            result["meta_data"] = self.meta_data
        return result


@dataclass
class ConversationHistory:
    """Domain model for conversation history."""

    messages: List[Message] = field(default_factory=list)

    def add_message(self, message: Message) -> None:
        """Add a message to the history."""
        self.messages.append(message)

    def get_messages_for_llm(self) -> List[Dict[str, Any]]:
        """Get messages formatted for LLM API."""
        return [msg.to_llm_format() for msg in self.messages]

    def to_dict(self) -> List[Dict[str, Any]]:
        """Convert to dictionary list."""
        return [msg.to_dict() for msg in self.messages]
