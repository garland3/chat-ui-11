"""Test for tool message formatting fix."""

from models.domain.messaging import Message, MessageRole


def test_tool_message_includes_tool_call_id_in_llm_format():
    """Test that tool messages include tool_call_id when formatted for LLM."""
    # Create a tool message with tool_call_id in metadata
    tool_call_id = "call_123456"
    message = Message(
        role=MessageRole.TOOL,
        content="Tool execution successful",
        metadata={"tool_name": "test_tool", "tool_call_id": tool_call_id},
    )

    # Format for LLM
    llm_format = message.to_llm_format()

    # Verify tool_call_id is included
    assert "tool_call_id" in llm_format
    assert llm_format["tool_call_id"] == tool_call_id
    assert llm_format["role"] == "tool"
    assert llm_format["content"] == "Tool execution successful"


def test_non_tool_message_does_not_include_tool_call_id():
    """Test that non-tool messages don't include tool_call_id even if in metadata."""
    message = Message(
        role=MessageRole.ASSISTANT,
        content="Regular assistant message",
        metadata={
            "tool_call_id": "call_123456"  # This should be ignored
        },
    )

    # Format for LLM
    llm_format = message.to_llm_format()

    # Verify tool_call_id is not included
    assert "tool_call_id" not in llm_format
    assert llm_format["role"] == "assistant"
    assert llm_format["content"] == "Regular assistant message"


def test_tool_message_without_tool_call_id_metadata():
    """Test that tool messages without tool_call_id in metadata work normally."""
    message = Message(
        role=MessageRole.TOOL, content="Tool execution result", metadata={}
    )

    # Format for LLM
    llm_format = message.to_llm_format()

    # Verify tool_call_id is not included when not in metadata
    assert "tool_call_id" not in llm_format
    assert llm_format["role"] == "tool"
    assert llm_format["content"] == "Tool execution result"
