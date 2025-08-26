"""Unit tests for Service Coordinator tool integration."""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4
from managers.service_coordinator.service_coordinator import ServiceCoordinator
from managers.tools.tool_models import ToolResult


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

        # Mock history with messages list for truncation logging
        mock_history = Mock()
        mock_message = Mock()
        mock_message.content = "Mock message content"
        mock_history.messages = [mock_message]
        mock_session.history = mock_history

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
    def mock_tool_orchestrator(self):
        """Create mock tool orchestrator."""
        mock = Mock()
        mock.orchestrate_tool_workflow = AsyncMock()
        return mock

    @pytest.fixture
    def service_coordinator(
        self,
        mock_session_manager,
        mock_llm_manager,
        mock_mcp_manager,
        mock_tool_caller,
        mock_tool_orchestrator,
    ):
        """Create service coordinator for testing."""
        return ServiceCoordinator(
            session_manager=mock_session_manager,
            llm_manager=mock_llm_manager,
            mcp_manager=mock_mcp_manager,
            tool_caller=mock_tool_caller,
            tool_orchestrator=mock_tool_orchestrator,
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
            selected_tool_map=None,  # No tools selected
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
        # Mock orchestrator returning response without tool calls
        service_coordinator.tool_orchestrator.orchestrate_tool_workflow.return_value = (
            "I can help with that, but don't need tools.",
            [],  # No tool results
        )

        result = await service_coordinator.handle_chat_message(
            session_id=uuid4(),
            content="What's the weather?",
            model="test-model",
            user_email="test@example.com",
            selected_tool_map={"weather": ["weather_tool"]},
        )

        # Should call orchestrator
        service_coordinator.tool_orchestrator.orchestrate_tool_workflow.assert_called_once()

        assert result["type"] == "chat_response"
        assert "don't need tools" in result["message"]

    @pytest.mark.asyncio
    async def test_handle_chat_with_tool_execution(self, service_coordinator):
        """Test complete tool execution flow."""
        # Mock tool execution result
        tool_result = ToolResult(
            tool_call_id="call_123", success=True, content="Sunny, 75°F in New York"
        )

        # Mock orchestrator returning final response with tool results
        service_coordinator.tool_orchestrator.orchestrate_tool_workflow.return_value = (
            "Based on the weather data, it's sunny and 75°F in New York.",
            [tool_result],
        )

        result = await service_coordinator.handle_chat_message(
            session_id=uuid4(),
            content="What's the weather in New York?",
            model="test-model",
            user_email="test@example.com",
            selected_tool_map={"weather": ["weather_tool"]},
        )

        # Verify orchestrator was called
        service_coordinator.tool_orchestrator.orchestrate_tool_workflow.assert_called_once()

        # Verify call arguments to orchestrator
        call_args = (
            service_coordinator.tool_orchestrator.orchestrate_tool_workflow.call_args
        )
        assert call_args.kwargs["model"] == "test-model"
        assert call_args.kwargs["user_email"] == "test@example.com"
        assert call_args.kwargs["selected_tool_map"] == {"weather": ["weather_tool"]}

        assert result["type"] == "chat_response"
        assert "sunny and 75°F" in result["message"]

    @pytest.mark.asyncio
    async def test_authorization_integration(self, service_coordinator):
        """Test that authorization is properly integrated into tool flow."""
        # Mock orchestrator returning simple response
        service_coordinator.tool_orchestrator.orchestrate_tool_workflow.return_value = (
            "Response",
            [],
        )

        await service_coordinator.handle_chat_message(
            session_id=uuid4(),
            content="Test message",
            model="test-model",
            user_email="test@example.com",
            selected_tool_map={"server": ["test_tool"]},
        )

        # Verify orchestrator was called with correct parameters
        service_coordinator.tool_orchestrator.orchestrate_tool_workflow.assert_called_once()
        call_args = (
            service_coordinator.tool_orchestrator.orchestrate_tool_workflow.call_args
        )

        # Check that parameters were passed correctly
        assert call_args.kwargs["user_email"] == "test@example.com"
        assert call_args.kwargs["selected_tool_map"] == {"server": ["test_tool"]}

    @pytest.mark.asyncio
    async def test_tool_callback_flow_success(self, service_coordinator):
        """Test that tool callbacks are sent during successful tool execution."""
        # Mock callback function - this will be called by orchestrator for tool callbacks + final response
        mock_callback = AsyncMock()

        # Mock tool execution result
        tool_result = ToolResult(
            tool_call_id="call_123", success=True, content="Tool executed successfully"
        )

        # Mock orchestrator returning response with tool results
        service_coordinator.tool_orchestrator.orchestrate_tool_workflow.return_value = (
            "Final response",
            [tool_result],
        )

        await service_coordinator.handle_chat_message(
            session_id=uuid4(),
            content="Execute a tool",
            model="test-model",
            user_email="test@example.com",
            selected_tool_map={"server": ["test_tool"]},
            update_callback=mock_callback,
        )

        # Verify orchestrator was called with the callback
        service_coordinator.tool_orchestrator.orchestrate_tool_workflow.assert_called_once()
        call_args = (
            service_coordinator.tool_orchestrator.orchestrate_tool_workflow.call_args
        )
        assert call_args.kwargs["update_callback"] == mock_callback

        # Verify final chat_response callback was sent
        assert mock_callback.call_count >= 1
        final_call = mock_callback.call_args_list[-1][0][
            0
        ]  # Last call should be chat_response
        assert final_call["type"] == "chat_response"

    @pytest.mark.asyncio
    async def test_tool_callback_flow_error(self, service_coordinator):
        """Test that tool error callbacks are sent when tool execution fails."""
        mock_callback = AsyncMock()

        # Mock failed tool result
        failed_result = ToolResult(
            tool_call_id="call_456",
            success=False,
            content="",
            error="Tool execution failed",
        )

        # Mock orchestrator returning response with failed tool results
        service_coordinator.tool_orchestrator.orchestrate_tool_workflow.return_value = (
            "Sorry, there was an error",
            [failed_result],
        )

        await service_coordinator.handle_chat_message(
            session_id=uuid4(),
            content="Execute a failing tool",
            model="test-model",
            user_email="test@example.com",
            selected_tool_map={"server": ["failing_tool"]},
            update_callback=mock_callback,
        )

        # Verify orchestrator was called with the callback
        service_coordinator.tool_orchestrator.orchestrate_tool_workflow.assert_called_once()
        call_args = (
            service_coordinator.tool_orchestrator.orchestrate_tool_workflow.call_args
        )
        assert call_args.kwargs["update_callback"] == mock_callback

        # Verify final chat_response callback was sent
        assert mock_callback.call_count >= 1
        final_call = mock_callback.call_args_list[-1][0][0]
        assert final_call["type"] == "chat_response"

    @pytest.mark.asyncio
    async def test_tool_callbacks_without_callback_function(self, service_coordinator):
        """Test that tool execution works normally without callback function."""
        # Mock orchestrator returning response
        service_coordinator.tool_orchestrator.orchestrate_tool_workflow.return_value = (
            "Final response",
            [],
        )

        # Should not raise any exceptions
        result = await service_coordinator.handle_chat_message(
            session_id=uuid4(),
            content="Execute a tool",
            model="test-model",
            user_email="test@example.com",
            selected_tool_map={"server": ["test_tool"]},
            update_callback=None,  # No callback
        )

        # Verify orchestrator was called with None callback
        call_args = (
            service_coordinator.tool_orchestrator.orchestrate_tool_workflow.call_args
        )
        assert call_args.kwargs["update_callback"] is None

        assert result["type"] == "chat_response"
        assert result["message"] == "Final response"

    @pytest.mark.asyncio
    async def test_callback_exception_handling(self, service_coordinator):
        """Test that callback exceptions don't break tool execution."""
        # Mock callback that raises exception - this will only be called by final chat_response
        mock_callback = AsyncMock(side_effect=Exception("Callback failed"))

        # Mock orchestrator returning response
        service_coordinator.tool_orchestrator.orchestrate_tool_workflow.return_value = (
            "Final response",
            [],
        )

        # Should complete successfully despite callback failures in final response
        result = await service_coordinator.handle_chat_message(
            session_id=uuid4(),
            content="Execute a tool",
            model="test-model",
            user_email="test@example.com",
            selected_tool_map={"server": ["test_tool"]},
            update_callback=mock_callback,
        )

        # Verify orchestrator was called with the failing callback
        call_args = (
            service_coordinator.tool_orchestrator.orchestrate_tool_workflow.call_args
        )
        assert call_args.kwargs["update_callback"] == mock_callback

        assert result["type"] == "chat_response"
        assert result["message"] == "Final response"
        # Final callback should have been called (and failed)
        assert mock_callback.call_count >= 1
