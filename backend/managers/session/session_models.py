"""Domain models for sessions - Phase 1A simplified version."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class MessageRole(Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


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
            "metadata": self.metadata
        }
    
    def to_llm_format(self) -> Dict[str, str]:
        """Convert to LLM API format."""
        return {
            "role": self.role.value,
            "content": self.content
        }


@dataclass
class ConversationHistory:
    """Domain model for conversation history."""
    messages: List[Message] = field(default_factory=list)
    
    def add_message(self, message: Message) -> None:
        """Add a message to the history."""
        self.messages.append(message)
    
    def get_messages_for_llm(self) -> List[Dict[str, str]]:
        """Get messages formatted for LLM API."""
        return [msg.to_llm_format() for msg in self.messages]
    
    def to_dict(self) -> List[Dict[str, Any]]:
        """Convert to dictionary list."""
        return [msg.to_dict() for msg in self.messages]


@dataclass
class Session:
    """Domain model for a chat session - Phase 1A simplified."""
    id: UUID = field(default_factory=uuid4)
    user_email: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    history: ConversationHistory = field(default_factory=ConversationHistory)
    context: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_email": self.user_email,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "history": self.history.to_dict(),
            "context": self.context,
            "active": self.active
        }
    
    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.now(timezone.utc)
    
    def add_user_message(self, content: str) -> Message:
        """Add a user message to the session."""
        message = Message(role=MessageRole.USER, content=content)
        self.history.add_message(message)
        self.update_timestamp()
        return message
    
    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Add an assistant message to the session."""
        message = Message(
            role=MessageRole.ASSISTANT, 
            content=content,
            metadata=metadata or {}
        )
        self.history.add_message(message)
        self.update_timestamp()
        return message