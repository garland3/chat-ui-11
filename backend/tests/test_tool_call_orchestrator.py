"""Unit tests for ToolCallOrchestrator."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from managers.agent.tool_call_orchestrator import ToolCallOrchestrator
from managers.tools.tool_models import ToolResult


class TestToolCallOrchestrator:
    """Test suite for ToolCallOrchestrator."""

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
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        mock = Mock()
        mock.call_with_tools = AsyncMock()
        mock.call_plain = AsyncMock()
        return mock

    @pytest.fixture
    def orchestrator(self, mock_tool_caller, mock_llm_manager):
        """Create orchestrator for testing."""
        return ToolCallOrchestrator(mock_tool_caller, mock_llm_manager)

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        mock = Mock()
        # Mock history with messages list for truncation logging
        mock_history = Mock()
        mock_message = Mock()
        mock_message.content = "Mock message content"
        mock_history.messages = [mock_message]
        mock.history = mock_history
        mock.add_tool_message = Mock()
        return mock

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(
        self, mock_tool_caller, mock_llm_manager
    ):
        """Test orchestrator initialization."""
        orchestrator = ToolCallOrchestrator(mock_tool_caller, mock_llm_manager)

        assert orchestrator.tool_caller == mock_tool_caller
        assert orchestrator.llm_manager == mock_llm_manager

    @pytest.mark.asyncio
    async def test_orchestrate_workflow_without_tool_calls(
        self, orchestrator, mock_session
    ):
        """Test workflow when LLM doesn't make tool calls."""
        session_id = uuid4()

        # Mock LLM response with no tool calls
        orchestrator.llm_manager.call_with_tools.return_value = {
            "content": "I can help with that, but don't need tools.",
            "tool_calls": [],
        }

        final_response, tool_results = await orchestrator.orchestrate_tool_workflow(
            session=mock_session,
            session_id=session_id,
            model="test-model",
            temperature=0.7,
            selected_tool_map={"server": ["test_tool"]},
            user_email="test@example.com",
        )

        # Verify flow
        orchestrator.tool_caller.get_authorized_tools_for_user.assert_called_once()
        orchestrator.llm_manager.call_with_tools.assert_called_once()
        orchestrator.llm_manager.call_plain.assert_not_called()  # No final call needed

        assert final_response == "I can help with that, but don't need tools."
        assert tool_results == []

    @pytest.mark.asyncio
    async def test_orchestrate_workflow_with_successful_tool_calls(
        self, orchestrator, mock_session
    ):
        """Test complete workflow with successful tool execution."""
        session_id = uuid4()

        # Mock LLM response with tool calls
        orchestrator.llm_manager.call_with_tools.return_value = {
            "content": "I'll execute the tool.",
            "tool_calls": [
                {
                    "id": "call_123",
                    "name": "server_test_tool",
                    "arguments": {"param": "value"},
                }
            ],
        }

        # Mock tool execution result
        tool_result = ToolResult(
            tool_call_id="call_123", success=True, content="Tool executed successfully"
        )
        orchestrator.tool_caller.execute_tool.return_value = tool_result

        # Mock final LLM response
        orchestrator.llm_manager.call_plain.return_value = (
            "Based on the tool result, here's the final answer."
        )

        final_response, tool_results = await orchestrator.orchestrate_tool_workflow(
            session=mock_session,
            session_id=session_id,
            model="test-model",
            temperature=0.7,
            selected_tool_map={"server": ["test_tool"]},
            user_email="test@example.com",
        )

        # Verify complete flow
        orchestrator.tool_caller.get_authorized_tools_for_user.assert_called_once()
        orchestrator.llm_manager.call_with_tools.assert_called_once()
        orchestrator.tool_caller.execute_tool.assert_called_once()
        orchestrator.llm_manager.call_plain.assert_called_once()  # Final call made
        mock_session.add_tool_message.assert_called_once()

        assert final_response == "Based on the tool result, here's the final answer."
        assert len(tool_results) == 1
        assert tool_results[0] == tool_result

    @pytest.mark.asyncio
    async def test_orchestrate_workflow_with_tool_error(
        self, orchestrator, mock_session
    ):
        """Test workflow when tool execution fails."""
        session_id = uuid4()

        # Mock LLM response with tool calls
        orchestrator.llm_manager.call_with_tools.return_value = {
            "content": "I'll try to execute the tool.",
            "tool_calls": [
                {
                    "id": "call_456",
                    "name": "server_failing_tool",
                    "arguments": {"param": "value"},
                }
            ],
        }

        # Mock tool execution failure
        orchestrator.tool_caller.execute_tool.side_effect = Exception(
            "Tool execution failed"
        )

        # Mock final LLM response
        orchestrator.llm_manager.call_plain.return_value = (
            "Sorry, there was an error with the tool."
        )

        final_response, tool_results = await orchestrator.orchestrate_tool_workflow(
            session=mock_session,
            session_id=session_id,
            model="test-model",
            temperature=0.7,
            selected_tool_map={"server": ["failing_tool"]},
            user_email="test@example.com",
        )

        # Verify flow handled error correctly
        orchestrator.tool_caller.execute_tool.assert_called_once()
        orchestrator.llm_manager.call_plain.assert_called_once()
        mock_session.add_tool_message.assert_called_once()

        assert final_response == "Sorry, there was an error with the tool."
        assert len(tool_results) == 1
        assert tool_results[0].success is False
        assert tool_results[0].error == "Tool execution failed"

    @pytest.mark.asyncio
    async def test_orchestrate_workflow_with_callbacks(
        self, orchestrator, mock_session
    ):
        """Test that UI callbacks are properly sent during workflow."""
        session_id = uuid4()
        mock_callback = AsyncMock()

        # Mock LLM response with tool calls
        orchestrator.llm_manager.call_with_tools.return_value = {
            "content": "Executing tool.",
            "tool_calls": [
                {
                    "id": "call_789",
                    "name": "server_callback_test",
                    "arguments": {"test": "value"},
                }
            ],
        }

        # Mock successful tool execution
        tool_result = ToolResult(
            tool_call_id="call_789", success=True, content="Success"
        )
        orchestrator.tool_caller.execute_tool.return_value = tool_result
        orchestrator.llm_manager.call_plain.return_value = "Final response"

        final_response, tool_results = await orchestrator.orchestrate_tool_workflow(
            session=mock_session,
            session_id=session_id,
            model="test-model",
            temperature=0.7,
            selected_tool_map={"server": ["callback_test"]},
            user_email="test@example.com",
            update_callback=mock_callback,
        )

        # Verify callbacks were sent
        assert mock_callback.call_count == 2  # tool_start and tool_complete

        # Check tool_start callback
        tool_start_call = mock_callback.call_args_list[0][0][0]
        assert tool_start_call["type"] == "tool_start"
        assert tool_start_call["tool_call_id"] == "call_789"

        # Check tool_complete callback
        tool_complete_call = mock_callback.call_args_list[1][0][0]
        assert tool_complete_call["type"] == "tool_complete"
        assert tool_complete_call["success"] is True

    @pytest.mark.asyncio
    async def test_authorization_integration(self, orchestrator, mock_session):
        """Test that authorization is properly integrated."""
        session_id = uuid4()

        orchestrator.llm_manager.call_with_tools.return_value = {
            "content": "Response",
            "tool_calls": [],
        }

        with patch(
            "managers.agent.tool_call_orchestrator.is_user_in_group"
        ) as mock_auth:
            mock_auth.return_value = True

            await orchestrator.orchestrate_tool_workflow(
                session=mock_session,
                session_id=session_id,
                model="test-model",
                temperature=0.7,
                selected_tool_map={"server": ["test_tool"]},
                user_email="test@example.com",
            )

            # Verify authorization function was passed correctly
            orchestrator.tool_caller.get_authorized_tools_for_user.assert_called_once()
            call_args = orchestrator.tool_caller.get_authorized_tools_for_user.call_args

            assert call_args.kwargs["username"] == "test@example.com"
            assert call_args.kwargs["selected_tool_map"] == {"server": ["test_tool"]}
            assert callable(call_args.kwargs["is_user_in_group"])

    @pytest.mark.asyncio
    async def test_multiple_tool_calls(self, orchestrator, mock_session):
        """Test workflow with multiple tool calls."""
        session_id = uuid4()

        # Mock LLM response with multiple tool calls
        orchestrator.llm_manager.call_with_tools.return_value = {
            "content": "I'll use multiple tools.",
            "tool_calls": [
                {"id": "call_1", "name": "server_tool1", "arguments": {"a": "1"}},
                {"id": "call_2", "name": "server_tool2", "arguments": {"b": "2"}},
            ],
        }

        # Mock tool execution results
        result1 = ToolResult(tool_call_id="call_1", success=True, content="Result 1")
        result2 = ToolResult(tool_call_id="call_2", success=True, content="Result 2")
        orchestrator.tool_caller.execute_tool.side_effect = [result1, result2]

        orchestrator.llm_manager.call_plain.return_value = "Combined final response"

        final_response, tool_results = await orchestrator.orchestrate_tool_workflow(
            session=mock_session,
            session_id=session_id,
            model="test-model",
            temperature=0.7,
            selected_tool_map={"server": ["tool1", "tool2"]},
            user_email="test@example.com",
        )

        # Verify both tools were executed
        assert orchestrator.tool_caller.execute_tool.call_count == 2
        assert len(tool_results) == 2
        assert tool_results[0] == result1
        assert tool_results[1] == result2

        # Verify session was updated for both tools
        assert mock_session.add_tool_message.call_count == 2
