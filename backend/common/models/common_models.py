"""Compatibility layer for domain messaging models.

Re-export entities from backend.models.domain.messaging so existing imports
continue to work during migration.
"""

from models.domain.messaging import (
    LLMResponse,
    MessageRole,
    MessageType,
    Message,
    ToolCall,
    ToolResult,
    ConversationHistory,
)

__all__ = [
    "LLMResponse",
    "MessageRole",
    "MessageType",
    "Message",
    "ToolCall",
    "ToolResult",
    "ConversationHistory",
]
