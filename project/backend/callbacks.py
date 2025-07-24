import logging
from typing import Any, Dict

from session import ChatSession

logger = logging.getLogger(__name__)


async def log_session_events_callback(session: ChatSession, **kwargs) -> None:
    """Log session lifecycle events."""
    event_type = kwargs.get("event_type", "unknown")
    logger.info("[SESSION] %s for user %s (session: %s)", event_type, session.user_email, session.session_id)


async def log_llm_call_callback(session: ChatSession, **kwargs) -> None:
    """Simple logging callback for LLM calls."""
    logger.info(
        "[CALLBACK] User %s is calling model %s with %d total messages.",
        session.user_email,
        session.model_name,
        len(session.messages),
    )


async def message_history_limit_callback(session: ChatSession, **kwargs) -> None:
    """Limit message history to prevent context overflow."""
    max_messages = 20
    if len(session.messages) > max_messages:
        session.messages = session.messages[:1] + session.messages[-(max_messages - 1):]
        logger.info(
            "[CALLBACK] Trimmed message history for %s to %d messages",
            session.user_email,
            len(session.messages),
        )


async def security_audit_callback(session: ChatSession, **kwargs) -> None:
    """Audit security-sensitive operations."""
    message: Dict[str, Any] = kwargs.get("message", {})
    content = message.get("content", "") if message else ""
    sensitive_keywords = ["password", "api_key", "secret", "token", "credential"]
    if any(keyword in content.lower() for keyword in sensitive_keywords):
        logger.warning(
            "[SECURITY] Potentially sensitive content detected from user %s",
            session.user_email,
        )


async def authorization_audit_callback(session: ChatSession, **kwargs) -> None:
    """Audit and log server authorization usage."""
    validated_servers = kwargs.get("validated_servers", [])
    if session.selected_tools:
        requested_servers = set()
        for tool_key in session.selected_tools:
            parts = tool_key.split("_", 1)
            if len(parts) == 2:
                requested_servers.add(parts[0])
        all_servers = set(session.mcp_manager.get_available_servers())
        authorized_servers = set(
            session.mcp_manager.get_authorized_servers(session.user_email, lambda e, g: True)
        )
        unauthorized_servers = all_servers - authorized_servers
        attempted = requested_servers.intersection(unauthorized_servers)
        if attempted:
            logger.warning(
                "[AUTHORIZATION] User %s attempted to access unauthorized servers: %s",
                session.user_email,
                attempted,
            )
    logger.info(
        "[AUTHORIZATION] User %s authorized for %d servers: %s",
        session.user_email,
        len(validated_servers),
        validated_servers,
    )


async def modify_user_message_callback(session: ChatSession, **kwargs) -> None:
    """Example callback that could modify user messages."""
    logger.debug("[CALLBACK] Could modify user message for %s", session.user_email)


async def dynamic_model_selection_callback(session: ChatSession, **kwargs) -> None:
    """Switch models based on message content."""
    message = kwargs.get("message", {})
    content = message.get("content", "") if message else ""
    if any(keyword in content.lower() for keyword in ["analyze", "complex", "detailed", "research"]):
        if session.model_name and "gpt-3.5" in session.model_name:
            logger.info("[CALLBACK] Could upgrade model for complex query from %s", session.user_email)


async def conversation_context_callback(session: ChatSession, **kwargs) -> None:
    """Add initial conversation context."""
    user_message = kwargs.get("user_message", {})
    if user_message and len(session.messages) == 1:
        system_message = {
            "role": "system",
            "content": f"You are helping {session.user_email}. Be helpful and concise.",
        }
        session.messages.insert(0, system_message)
        logger.info(
            "[CALLBACK] Added system context for new conversation with %s",
            session.user_email,
        )
