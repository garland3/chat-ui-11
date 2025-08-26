"""Domain models for sessions - Phase 1A simplified version."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from common.models.common_models import MessageRole, Message, ConversationHistory


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
            "active": self.active,
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

    def add_assistant_message(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Add an assistant message to the session."""
        message = Message(
            role=MessageRole.ASSISTANT, content=content, metadata=metadata or {}
        )
        self.history.add_message(message)
        self.update_timestamp()
        return message

    def add_tool_message(
        self, tool_name: str, content: str, tool_call_id: str
    ) -> Message:
        """Add a tool result message to the session."""
        message = Message(
            role=MessageRole.TOOL,
            content=content,
            metadata={"tool_name": tool_name, "tool_call_id": tool_call_id},
        )
        self.history.add_message(message)
        self.update_timestamp()
        return message
