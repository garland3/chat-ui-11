"""Unit tests for Service Coordinator tool integration."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from managers.service_coordinator.service_coordinator import ServiceCoordinator
from managers.tools.tool_models import ToolCall, ToolResult


class TestServiceCoordinatorTools:
    """Test suite for Service Coordinator tool integration."""
    
    @pytest.fixture
    def mock_session_manager(self):
        """Create mock session manager."""
        mock = Mock()
        mock_session = Mock()
        mock_session.add_user_message.return_value = Mock(id=uuid4())
        mock_session.add_assistant_message.return_value = Mock(id=uuid4())
        mock_session.add_tool_message.return_value = Mock(id=uuid4())
        mock_session.history = Mock()
        mock.get_or_create_session.return_value = mock_session
        mock.update_session.return_value = None
        return mock
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        mock = Mock()
        mock.call_with_tools = AsyncMock()
        mock.call_plain = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_mcp_manager(self):
        """Create mock MCP manager."""
        mock = Mock()
        mock.get_authorized_servers.return_value = ["test_server"]
        return mock
    
    @pytest.fixture
    def mock_tool_caller(self):
        """Create mock tool caller."""
        mock = Mock()
        mock.get_authorized_tools_for_user.return_value = [
            {"function": {"name": "test_tool"}}
        ]
        mock.execute_tool = AsyncMock()
        return mock
    
    @pytest.fixture
    def service_coordinator(self, mock_session_manager, mock_llm_manager, mock_mcp_manager, mock_tool_caller):
        """Create service coordinator for testing."""
        return ServiceCoordinator(
            session_manager=mock_session_manager,
            llm_manager=mock_llm_manager,
            mcp_manager=mock_mcp_manager,
            tool_caller=mock_tool_caller
        )
    
    @pytest.mark.asyncio
    async def test_handle_chat_without_tools_uses_plain_llm(self, service_coordinator):
        """Test that chat without selected tools uses plain LLM call."""
        service_coordinator.llm_manager.call_plain.return_value = "Plain response"
        
        result = await service_coordinator.handle_chat_message(
            session_id=uuid4(),
            content="Hello",
            model="test-model",
            user_email="test@example.com",
            selected_tool_map=None  # No tools selected
        )
        
        # Should call plain LLM, not tools
        service_coordinator.llm_manager.call_plain.assert_called_once()
        service_coordinator.llm_manager.call_with_tools.assert_not_called()
        service_coordinator.tool_caller.get_authorized_tools_for_user.assert_not_called()
        
        assert result["type"] == "chat_response"
        assert result["message"] == "Plain response"
    
    @pytest.mark.asyncio
    async def test_handle_chat_with_tools_no_tool_calls(self, service_coordinator):
        """Test chat with tools where LLM doesn't make tool calls."""
        service_coordinator.llm_manager.call_with_tools.return_value = {
            "content": "I can help with that, but don't need tools.",
            "tool_calls": []
        }
        
        result = await service_coordinator.handle_chat_message(
            session_id=uuid4(),
            content="What's the weather?",
            model="test-model", 
            user_email="test@example.com",
            selected_tool_map={"weather": ["weather_tool"]}
        )
        
        # Should call tools API but not execute any tools
        service_coordinator.tool_caller.get_authorized_tools_for_user.assert_called_once()
        service_coordinator.llm_manager.call_with_tools.assert_called_once()
        service_coordinator.tool_caller.execute_tool.assert_not_called()
        
        assert result["type"] == "chat_response"
        assert "don't need tools" in result["message"]
    
    @pytest.mark.asyncio 
    async def test_handle_chat_with_tool_execution(self, service_coordinator):
        """Test complete tool execution flow."""
        # Mock LLM response with tool calls
        service_coordinator.llm_manager.call_with_tools.return_value = {
            "content": "I'll check the weather for you.",
            "tool_calls": [
                {
                    "id": "call_123",
                    "name": "weather_tool", 
                    "arguments": {"location": "New York"}
                }
            ]
        }
        
        # Mock tool execution result
        tool_result = ToolResult(
            tool_call_id="call_123",
            success=True,
            content="Sunny, 75°F in New York"
        )
        service_coordinator.tool_caller.execute_tool.return_value = tool_result
        
        # Mock final LLM response after tool execution
        service_coordinator.llm_manager.call_plain.return_value = "Based on the weather data, it's sunny and 75°F in New York."
        
        result = await service_coordinator.handle_chat_message(
            session_id=uuid4(),
            content="What's the weather in New York?",
            model="test-model",
            user_email="test@example.com", 
            selected_tool_map={"weather": ["weather_tool"]}
        )
        
        # Verify complete flow
        service_coordinator.tool_caller.get_authorized_tools_for_user.assert_called_once()
        service_coordinator.llm_manager.call_with_tools.assert_called_once()
        service_coordinator.tool_caller.execute_tool.assert_called_once()
        service_coordinator.llm_manager.call_plain.assert_called_once()  # Final response
        
        # Verify tool call was properly constructed
        tool_call_arg = service_coordinator.tool_caller.execute_tool.call_args[0][0]
        assert isinstance(tool_call_arg, ToolCall)
        assert tool_call_arg.id == "call_123"
        assert tool_call_arg.name == "weather_tool"
        assert tool_call_arg.arguments == {"location": "New York"}
        
        assert result["type"] == "chat_response"
        assert "sunny and 75°F" in result["message"]
    
    @pytest.mark.asyncio
    async def test_authorization_integration(self, service_coordinator):
        """Test that authorization is properly integrated into tool flow."""
        service_coordinator.llm_manager.call_with_tools.return_value = {
            "content": "Response",
            "tool_calls": []
        }
        
        with patch('managers.service_coordinator.service_coordinator.is_user_in_group') as mock_auth:
            mock_auth.return_value = True
            
            await service_coordinator.handle_chat_message(
                session_id=uuid4(),
                content="Test message",
                model="test-model",
                user_email="test@example.com",
                selected_tool_map={"server": ["test_tool"]}
            )
            
            # Verify authorization function was passed correctly
            service_coordinator.tool_caller.get_authorized_tools_for_user.assert_called_once()
            call_args = service_coordinator.tool_caller.get_authorized_tools_for_user.call_args
            
            # Check that username and is_user_in_group function were passed
            assert call_args.kwargs["username"] == "test@example.com"  # username
            assert call_args.kwargs["selected_tool_map"] == {"server": ["test_tool"]}
            assert callable(call_args.kwargs["is_user_in_group"])  # is_user_in_group function