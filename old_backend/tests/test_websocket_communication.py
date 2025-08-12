"""
Simple tests for WebSocket communication patterns.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock


class MockWebSocket:
    """Simple mock WebSocket for testing."""
    
    def __init__(self):
        self.sent_messages = []
        self.is_connected = True
    
    async def send_text(self, data: str):
        """Mock sending text data."""
        if not self.is_connected:
            raise ConnectionError("WebSocket not connected")
        self.sent_messages.append(data)
    
    async def receive_text(self):
        """Mock receiving text data."""
        if not self.is_connected:
            raise ConnectionError("WebSocket not connected")
        return '{"type": "ping"}'
    
    def disconnect(self):
        """Mock disconnection."""
        self.is_connected = False


class TestWebSocketCommunication:
    """Test WebSocket communication patterns."""

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending a message through WebSocket."""
        ws = MockWebSocket()
        message = {"type": "user_message", "content": "Hello"}
        
        await ws.send_text(json.dumps(message))
        
        assert len(ws.sent_messages) == 1
        sent_data = json.loads(ws.sent_messages[0])
        assert sent_data["type"] == "user_message"
        assert sent_data["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_receive_message(self):
        """Test receiving a message through WebSocket."""
        ws = MockWebSocket()
        
        received = await ws.receive_text()
        data = json.loads(received)
        
        assert data["type"] == "ping"

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test handling connection errors."""
        ws = MockWebSocket()
        ws.disconnect()
        
        with pytest.raises(ConnectionError):
            await ws.send_text("test message")

    @pytest.mark.asyncio
    async def test_multiple_messages(self):
        """Test sending multiple messages."""
        ws = MockWebSocket()
        messages = [
            {"type": "message", "content": "First"},
            {"type": "message", "content": "Second"},
            {"type": "message", "content": "Third"}
        ]
        
        for msg in messages:
            await ws.send_text(json.dumps(msg))
        
        assert len(ws.sent_messages) == 3
        
        for i, sent in enumerate(ws.sent_messages):
            data = json.loads(sent)
            assert data["content"] == messages[i]["content"]

    def test_message_queue(self):
        """Test message queuing functionality."""
        queue = []
        
        # Add messages to queue
        queue.append({"type": "message", "content": "First"})
        queue.append({"type": "message", "content": "Second"})
        
        assert len(queue) == 2
        
        # Process messages
        first = queue.pop(0)
        assert first["content"] == "First"
        assert len(queue) == 1

    def test_message_types(self):
        """Test different message types."""
        message_types = [
            {"type": "user_message", "content": "Hello"},
            {"type": "assistant_response", "content": "Hi there"},
            {"type": "system_message", "content": "Connected"},
            {"type": "error", "message": "Something failed"},
            {"type": "ping", "timestamp": "2024-01-01T00:00:00Z"}
        ]
        
        for msg in message_types:
            assert "type" in msg
            assert msg["type"] in ["user_message", "assistant_response", "system_message", "error", "ping"]