"""Unit tests for tool notification functions."""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from managers.ui_callback.tool_notifications import (
    notify_tool_start,
    notify_tool_complete,
    notify_tool_error,
)
from managers.tools.tool_models import ToolCall, ToolResult


class TestToolNotifications:
    """Test suite for tool notification functions."""

    @pytest.mark.asyncio
    async def test_notify_tool_start_with_callback(self):
        """Test notify_tool_start sends correct message."""
        mock_callback = AsyncMock()
        session_id = uuid4()

        tool_call = ToolCall(
            id="call_123",
            name="server_test_tool",
            arguments={"param": "value", "password": "secret"},
        )

        await notify_tool_start(tool_call, session_id, mock_callback)

        # Verify callback was called once
        mock_callback.assert_called_once()

        # Verify message structure
        message = mock_callback.call_args[0][0]
        assert message["type"] == "tool_start"
        assert message["tool_call_id"] == "call_123"
        assert message["tool_name"] == "test_tool"
        assert message["server_name"] == "server"
        assert message["arguments"]["param"] == "value"
        assert message["arguments"]["password"] == "***MASKED***"
        assert message["session_id"] == str(session_id)

    @pytest.mark.asyncio
    async def test_notify_tool_start_without_callback(self):
        """Test notify_tool_start handles None callback gracefully."""
        tool_call = ToolCall(id="call_123", name="test_tool", arguments={})
        session_id = uuid4()

        # Should not raise any exceptions
        await notify_tool_start(tool_call, session_id, None)

    @pytest.mark.asyncio
    async def test_notify_tool_complete_with_callback(self):
        """Test notify_tool_complete sends correct message."""
        mock_callback = AsyncMock()
        session_id = uuid4()

        tool_call = ToolCall(id="call_456", name="weather_get_forecast", arguments={})
        result = ToolResult(
            tool_call_id="call_456",
            success=True,
            content="Weather is sunny",
            meta_data={"temperature": "75F"},
        )

        await notify_tool_complete(tool_call, result, session_id, mock_callback)

        # Verify callback was called once
        mock_callback.assert_called_once()

        # Verify message structure
        message = mock_callback.call_args[0][0]
        assert message["type"] == "tool_complete"
        assert message["tool_call_id"] == "call_456"
        assert message["tool_name"] == "get_forecast"
        assert message["server_name"] == "weather"
        assert message["success"] is True
        assert message["result"]["content"] == "Weather is sunny"
        assert message["result"]["meta_data"]["temperature"] == "75F"

    @pytest.mark.asyncio
    async def test_notify_tool_complete_without_callback(self):
        """Test notify_tool_complete handles None callback gracefully."""
        tool_call = ToolCall(id="call_456", name="test_tool", arguments={})
        result = ToolResult(tool_call_id="call_456", success=True, content="OK")
        session_id = uuid4()

        # Should not raise any exceptions
        await notify_tool_complete(tool_call, result, session_id, None)

    @pytest.mark.asyncio
    async def test_notify_tool_error_with_callback(self):
        """Test notify_tool_error sends correct message."""
        mock_callback = AsyncMock()
        session_id = uuid4()

        tool_call = ToolCall(id="call_789", name="server_failing_tool", arguments={})
        error_message = "Connection timeout after 30 seconds"

        await notify_tool_error(tool_call, error_message, session_id, mock_callback)

        # Verify callback was called once
        mock_callback.assert_called_once()

        # Verify message structure
        message = mock_callback.call_args[0][0]
        assert message["type"] == "tool_error"
        assert message["tool_call_id"] == "call_789"
        assert message["tool_name"] == "failing_tool"
        assert message["server_name"] == "server"
        assert message["error"] == error_message

    @pytest.mark.asyncio
    async def test_notify_tool_error_truncates_long_error(self):
        """Test notify_tool_error truncates very long error messages."""
        mock_callback = AsyncMock()
        session_id = uuid4()

        tool_call = ToolCall(id="call_long", name="test_tool", arguments={})
        long_error = "x" * 600  # Longer than 500 char limit

        await notify_tool_error(tool_call, long_error, session_id, mock_callback)

        message = mock_callback.call_args[0][0]
        assert len(message["error"]) == 500
        assert message["error"] == "x" * 500

    @pytest.mark.asyncio
    async def test_notify_tool_error_without_callback(self):
        """Test notify_tool_error handles None callback gracefully."""
        tool_call = ToolCall(id="call_789", name="test_tool", arguments={})
        session_id = uuid4()

        # Should not raise any exceptions
        await notify_tool_error(tool_call, "Error message", session_id, None)

    @pytest.mark.asyncio
    async def test_callback_exceptions_are_logged(self):
        """Test that callback exceptions are caught and logged."""
        mock_callback = AsyncMock(side_effect=Exception("Callback failed"))
        session_id = uuid4()

        tool_call = ToolCall(id="call_robust", name="test_tool", arguments={})

        # These should not raise exceptions even if callback fails
        await notify_tool_start(tool_call, session_id, mock_callback)

        result = ToolResult(tool_call_id="call_robust", success=True, content="OK")
        await notify_tool_complete(tool_call, result, session_id, mock_callback)

        await notify_tool_error(tool_call, "Error", session_id, mock_callback)

        # Verify callback was attempted
        assert mock_callback.call_count == 3

    @pytest.mark.asyncio
    async def test_tool_name_parsing(self):
        """Test that tool name parsing works correctly in notifications."""
        mock_callback = AsyncMock()
        session_id = uuid4()

        # Test various tool name formats
        test_cases = [
            ("simple_tool", "simple", "tool"),
            ("server_complex_tool_name", "server", "complex_tool_name"),
            ("notool", "", "notool"),
        ]

        for tool_name, expected_server, expected_tool in test_cases:
            tool_call = ToolCall(id="call_test", name=tool_name, arguments={})

            await notify_tool_start(tool_call, session_id, mock_callback)

            message = mock_callback.call_args[0][0]
            assert message["server_name"] == expected_server
            assert message["tool_name"] == expected_tool

            mock_callback.reset_mock()
