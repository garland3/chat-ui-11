"""Unit tests for LLM Manager tool calling functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from managers.llm.llm_manager import LLMManager
from common.models.common_models import ConversationHistory, Message, MessageRole


class TestLLMManagerTools:
    """Test suite for LLM Manager tool calling functionality."""

    @pytest.fixture
    def mock_llm_config(self):
        """Create mock LLM configuration."""
        config = Mock()
        config.models = [
            Mock(
                model_name="test-model",
                max_tokens=1000,
                api_key="test-key",
                model_url="https://api.openai.com",
            )
        ]
        return config

    @pytest.fixture
    def llm_manager(self, mock_llm_config):
        """Create LLM Manager instance for testing."""
        return LLMManager(llm_config=mock_llm_config)

    @pytest.fixture
    def conversation_history(self):
        """Create sample conversation history."""
        history = ConversationHistory()
        history.add_message(Message(role=MessageRole.USER, content="What's 2+2?"))
        return history

    @pytest.fixture
    def sample_tools(self):
        """Create sample tool schemas."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Perform calculations",
                    "parameters": {
                        "type": "object",
                        "properties": {"expression": {"type": "string"}},
                    },
                },
            }
        ]

    def test_call_with_tools_without_litellm_returns_mock(
        self, llm_manager, conversation_history, sample_tools
    ):
        """Test that call_with_tools returns mock response when LiteLLM unavailable."""
        # Patch LITELLM_AVAILABLE to False
        with patch("managers.llm.llm_manager.LITELLM_AVAILABLE", False):
            result = llm_manager._get_mock_response(
                [{"content": "test message"}], with_tools=True
            )

            assert "content" in result
            assert "tool_calls" in result
            assert result["tool_calls"] == []
            assert "Mock LLM response with tools" in result["content"]

    @pytest.mark.asyncio
    async def test_call_with_tools_success_no_tool_calls(
        self, llm_manager, conversation_history, sample_tools
    ):
        """Test successful LLM call with tools that doesn't use tools."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "The answer is 4"
        mock_response.choices[0].message.tool_calls = None

        with patch("managers.llm.llm_manager.LITELLM_AVAILABLE", True):
            with patch(
                "managers.llm.llm_manager.acompletion", new_callable=AsyncMock
            ) as mock_completion:
                mock_completion.return_value = mock_response

                result = await llm_manager.call_with_tools(
                    "test-model", conversation_history, sample_tools
                )

                assert result["content"] == "The answer is 4"
                assert result["tool_calls"] == []

                # Verify tools were passed to LiteLLM
                mock_completion.assert_called_once()
                call_kwargs = mock_completion.call_args[1]
                assert call_kwargs["tools"] == sample_tools
                assert call_kwargs["tool_choice"] == "auto"

    @pytest.mark.asyncio
    async def test_call_with_tools_with_tool_calls(
        self, llm_manager, conversation_history, sample_tools
    ):
        """Test successful LLM call that returns tool calls."""
        # Mock tool call response
        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "calculator"
        mock_tool_call.function.arguments = '{"expression": "2+2"}'

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "I'll calculate that for you."
        mock_response.choices[0].message.tool_calls = [mock_tool_call]

        with patch("managers.llm.llm_manager.LITELLM_AVAILABLE", True):
            with patch(
                "managers.llm.llm_manager.acompletion", new_callable=AsyncMock
            ) as mock_completion:
                mock_completion.return_value = mock_response

                result = await llm_manager.call_with_tools(
                    "test-model", conversation_history, sample_tools
                )

                assert result["content"] == "I'll calculate that for you."
                assert len(result["tool_calls"]) == 1

                tool_call = result["tool_calls"][0]
                assert tool_call["id"] == "call_123"
                assert tool_call["name"] == "calculator"
                assert tool_call["arguments"] == {
                    "expression": "2+2"
                }  # Should be parsed JSON

    @pytest.mark.asyncio
    async def test_tool_arguments_json_parsing_failure(
        self, llm_manager, conversation_history, sample_tools
    ):
        """Test handling of malformed JSON in tool call arguments."""
        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "calculator"
        mock_tool_call.function.arguments = "invalid json{"  # Malformed JSON

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "I'll calculate that."
        mock_response.choices[0].message.tool_calls = [mock_tool_call]

        with patch("managers.llm.llm_manager.LITELLM_AVAILABLE", True):
            with patch(
                "managers.llm.llm_manager.acompletion", new_callable=AsyncMock
            ) as mock_completion:
                mock_completion.return_value = mock_response

                result = await llm_manager.call_with_tools(
                    "test-model", conversation_history, sample_tools
                )

                # Should handle malformed JSON gracefully
                tool_call = result["tool_calls"][0]
                assert tool_call["arguments"] == {}  # Should fallback to empty dict
