"""
Test to verify agent tool call logging works correctly.
"""

import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from agent_executor import AgentExecutor, AgentContext
from llm_caller import LLMCaller, LLMResponse  
from tool_executor import ToolExecutor


class TestAgentLogging:
    """Test agent executor logging functionality."""
    
    @pytest.mark.asyncio
    async def test_agent_tool_call_logging(self, caplog):
        """Test that agent tool calls are properly logged."""
        
        # Create mock components
        mock_llm_caller = MagicMock(spec=LLMCaller)
        mock_tool_executor = MagicMock(spec=ToolExecutor)
        
        # Create agent executor
        agent_executor = AgentExecutor(mock_llm_caller, mock_tool_executor)
        
        # Create agent context
        context = AgentContext(
            user_email="test@example.com",
            model_name="gpt-4",
            max_steps=2,
            tools_schema=[{
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool",
                    "parameters": {"type": "object", "properties": {}}
                }
            }],
            tool_mapping={"test_tool": {"server": "test", "tool_name": "test_tool"}},
            session=None,
            messages=[]
        )
        
        # Mock LLM response with tool call
        mock_tool_call = {
            "id": "test_call_123",
            "function": {
                "name": "test_tool",
                "arguments": '{"param1": "value1", "param2": 42}'
            }
        }
        
        mock_llm_response = MagicMock(spec=LLMResponse)
        mock_llm_response.content = "I'll use the test tool."
        mock_llm_response.tool_calls = [mock_tool_call]
        mock_llm_response.has_tool_calls.return_value = True
        
        mock_llm_caller.call_with_tools = AsyncMock(return_value=mock_llm_response)
        
        # Mock tool execution result
        mock_tool_result = MagicMock()
        mock_tool_result.content = "Tool executed successfully"
        mock_tool_result.tool_call_id = "test_call_123"
        
        mock_tool_executor.execute_tool_calls = AsyncMock(return_value=[mock_tool_result])
        
        # Mock second step with completion tool
        mock_completion_call = {
            "id": "completion_call_456", 
            "function": {
                "name": "all_work_done",
                "arguments": '{}'
            }
        }
        
        mock_completion_response = MagicMock(spec=LLMResponse)
        mock_completion_response.content = "I'll mark this as complete."
        mock_completion_response.tool_calls = [mock_completion_call]
        mock_completion_response.has_tool_calls.return_value = True
        
        # Mock final text response after completion tool
        mock_final_response = MagicMock(spec=LLMResponse)
        mock_final_response.content = "Task completed successfully!"
        mock_final_response.tool_calls = []
        mock_final_response.has_tool_calls.return_value = False
        
        # Set up the LLM caller to return different responses on subsequent calls
        mock_llm_caller.call_with_tools.side_effect = [
            mock_llm_response,        # First call returns tool call
            mock_completion_response, # Second call returns completion tool
            mock_final_response       # Follow-up call after completion for final text
        ]
        
        # Mock completion tool result
        mock_completion_result = MagicMock()
        mock_completion_result.content = "Agent completion acknowledged: Work completed"
        mock_completion_result.tool_call_id = "completion_call_456"
        
        mock_tool_executor.execute_tool_calls.side_effect = [
            [mock_tool_result],      # First tool execution
            [mock_completion_result] # Completion tool execution
        ]
        
        # Capture logs at INFO level
        with caplog.at_level(logging.INFO):
            result = await agent_executor.execute_agent_loop(
                "Please use the test tool to complete this task",
                context
            )
        
        # Verify the result
        assert result.completion_reason.value == "completion_tool_used"
        assert result.steps_taken == 2  # Two steps: regular tool, then completion
        
        # Check that tool call logging appears in logs
        log_messages = [record.message for record in caplog.records if record.levelname == 'INFO']
        
        # Should see tool call logging
        tool_call_logs = [msg for msg in log_messages if "Tool call" in msg]
        tool_args_logs = [msg for msg in log_messages if "Tool arguments" in msg]
        
        assert len(tool_call_logs) >= 2, f"Expected at least 2 tool call logs, got: {log_messages}"
        assert len(tool_args_logs) >= 2, f"Expected at least 2 tool arguments logs, got: {log_messages}"
        
        # Verify specific tool call details are logged
        assert any("test_tool" in msg for msg in tool_call_logs)
        assert any("param1" in msg and "value1" in msg for msg in tool_args_logs)
        assert any("all_work_done" in msg for msg in tool_call_logs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])