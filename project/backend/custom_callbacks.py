"""Custom callback functions for the Chat UI system.

This file demonstrates how to create custom callbacks that can modify
ChatSession state and behavior. All callbacks must follow the signature:

async def callback_name(session: ChatSession, **kwargs) -> None:
    # Your custom logic here
    pass
"""

import logging

logger = logging.getLogger(__name__)


async def rate_limiting_callback(session, **kwargs):
    """Example rate limiting callback."""
    # Add a request counter to the session
    if not hasattr(session, 'request_count'):
        session.request_count = 0
    
    session.request_count += 1
    
    # Example: Limit to 10 requests per session
    if session.request_count > 10:
        logger.warning(f"Rate limit exceeded for user {session.user_email}")
        # Could raise an exception or modify behavior
        # raise ValueError("Rate limit exceeded")
    
    logger.info(f"Request #{session.request_count} for user {session.user_email}")


async def auto_tool_selection_callback(session, **kwargs):
    """Automatically select tools based on message content."""
    message = kwargs.get('message', {})
    content = message.get('content', '') if message else ''
    
    # Auto-select calculator for math queries
    if any(keyword in content.lower() for keyword in ['calculate', 'math', '+', '-', '*', '/', 'sum']):
        # Add calculator tools to selected_tools if available
        available_servers = session.mcp_manager.get_authorized_servers(session.user_email, 
                                                                        lambda email, group: True)  # Mock auth check
        if 'calculator' in available_servers:
            calculator_tools = [f"calculator_{tool.name}" 
                              for tool in session.mcp_manager.available_tools.get('calculator', {}).get('tools', [])]
            session.selected_tools.extend(calculator_tools)
            logger.info(f"Auto-selected calculator tools for {session.user_email}: {calculator_tools}")
    
    # Auto-select filesystem for file operations
    if any(keyword in content.lower() for keyword in ['file', 'directory', 'folder', 'read', 'write', 'list']):
        available_servers = session.mcp_manager.get_authorized_servers(session.user_email,
                                                                        lambda email, group: True)  # Mock auth check
        if 'filesystem' in available_servers:
            filesystem_tools = [f"filesystem_{tool.name}" 
                               for tool in session.mcp_manager.available_tools.get('filesystem', {}).get('tools', [])]
            session.selected_tools.extend(filesystem_tools)
            logger.info(f"Auto-selected filesystem tools for {session.user_email}: {filesystem_tools}")


async def conversation_summarization_callback(session, **kwargs):
    """Summarize long conversations to save context."""
    # If conversation gets too long, summarize older messages
    if len(session.messages) > 15:
        # Keep first system message, summarize middle messages, keep last 5
        system_messages = [msg for msg in session.messages[:2] if msg.get('role') == 'system']
        recent_messages = session.messages[-5:]
        middle_messages = session.messages[len(system_messages):-5]
        
        if middle_messages:
            # Create a summary (in a real implementation, you might call an LLM for this)
            summary = {
                "role": "system",
                "content": f"[Previous conversation summary: {len(middle_messages)} messages exchanged about various topics]"
            }
            session.messages = system_messages + [summary] + recent_messages
            logger.info(f"Summarized {len(middle_messages)} messages for {session.user_email}")


async def user_preference_callback(session, **kwargs):
    """Apply user preferences to the session."""
    # Mock user preferences - in real app, load from database
    user_preferences = {
        "test@test.com": {
            "preferred_model": "gpt-4",
            "auto_tools": True,
            "verbose_responses": False
        }
    }
    
    prefs = user_preferences.get(session.user_email, {})
    
    # Apply preferred model
    if prefs.get("preferred_model") and not session.model_name:
        session.model_name = prefs["preferred_model"]
        logger.info(f"Applied preferred model {session.model_name} for {session.user_email}")
    
    # Add preference indicators to session
    session.user_preferences = prefs


async def security_content_filter_callback(session, **kwargs):
    """Filter and modify content for security."""
    user_message = kwargs.get('user_message', {})
    
    if user_message and user_message.get('role') == 'user':
        content = user_message.get('content', '')
        
        # Example: Replace sensitive patterns
        sensitive_patterns = [
            (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]'),  # SSN pattern
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]'),  # Email
        ]
        
        import re
        modified = False
        for pattern, replacement in sensitive_patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                modified = True
        
        if modified:
            user_message['content'] = content
            logger.warning(f"Redacted sensitive content for user {session.user_email}")


# Example of how to register these callbacks:
"""
# In your main.py or startup code:
from custom_callbacks import (
    rate_limiting_callback,
    auto_tool_selection_callback, 
    conversation_summarization_callback,
    user_preference_callback,
    security_content_filter_callback
)

# Register the callbacks
session_manager.register_callback("before_message_processing", rate_limiting_callback)
session_manager.register_callback("before_message_processing", auto_tool_selection_callback)
session_manager.register_callback("before_llm_call", conversation_summarization_callback)
session_manager.register_callback("session_started", user_preference_callback)
session_manager.register_callback("after_user_message_added", security_content_filter_callback)
"""
