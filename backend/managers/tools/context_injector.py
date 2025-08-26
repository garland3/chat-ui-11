"""Context injection for tool execution."""

import logging
from typing import Optional
from .tool_models import ToolCall, ToolExecutionContext

logger = logging.getLogger(__name__)


class ContextInjector:
    """Handles context injection for tool calls."""

    def __init__(self):
        pass

    def inject_context(
        self, tool_call: ToolCall, context: ToolExecutionContext
    ) -> ToolCall:
        """Inject context into tool call arguments."""
        # Create a copy to avoid modifying original
        injected_call = ToolCall(
            id=tool_call.id, name=tool_call.name, arguments=tool_call.arguments.copy()
        )

        # Inject user context if available
        if context.user_id:
            injected_call.arguments["_user_id"] = context.user_id

        # Inject session context if available
        if context.session_id:
            injected_call.arguments["_session_id"] = context.session_id

        # Inject file context if available
        if context.file_context:
            injected_call.arguments["_file_context"] = context.file_context

        # Inject any additional metadata
        if context.metadata:
            injected_call.arguments["_metadata"] = context.metadata

        logger.debug(f"Injected context for tool {tool_call.name}")
        return injected_call

    def extract_username(self, context: ToolExecutionContext) -> Optional[str]:
        """Extract username from context for tools that need it."""
        if context.metadata and "username" in context.metadata:
            return context.metadata["username"]
        return None

    def get_file_references(self, context: ToolExecutionContext) -> list[str]:
        """Get file references from context."""
        return context.file_context or []
