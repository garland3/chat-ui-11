"""
Test for agent prompt loading functionality.
"""

import pytest
from unittest.mock import MagicMock

from agent_executor import AgentExecutor, AgentContext
from llm_caller import LLMCaller
from tool_executor import ToolExecutor


class TestAgentPromptLoading:
    """Test agent prompt loading from file."""
    
    def test_load_agent_summary_prompt(self):
        """Test that the agent summary prompt loads correctly from file."""
        # Create agent executor
        mock_llm_caller = MagicMock(spec=LLMCaller)
        mock_tool_executor = MagicMock(spec=ToolExecutor)
        agent_executor = AgentExecutor(mock_llm_caller, mock_tool_executor)
        
        # Test the prompt loading function
        formatted_prompt = agent_executor._load_agent_summary_prompt(
            original_prompt="Test the file upload feature",
            step_count=3,
            summary="Step 1: Analyzed requirements\nStep 2: Implemented solution\nStep 3: Tested functionality",
            final_response="File upload feature has been successfully implemented and tested."
        )
        
        # Verify the prompt was loaded and formatted correctly
        assert "Test the file upload feature" in formatted_prompt
        assert "3 steps" in formatted_prompt
        assert "Step 1: Analyzed requirements" in formatted_prompt
        assert "File upload feature has been successfully implemented" in formatted_prompt
        
        # Verify the template structure is preserved
        assert "Please provide a comprehensive summary" in formatted_prompt
        assert "1. What was requested and what was accomplished" in formatted_prompt
        assert "2. Key results and findings" in formatted_prompt
        assert "3. The overall outcome" in formatted_prompt
        assert "4. Any important details" in formatted_prompt
        
    def test_load_agent_summary_prompt_fallback(self):
        """Test that fallback works when prompt file is not available."""
        # Create agent executor
        mock_llm_caller = MagicMock(spec=LLMCaller)
        mock_tool_executor = MagicMock(spec=ToolExecutor)
        agent_executor = AgentExecutor(mock_llm_caller, mock_tool_executor)
        
        # Mock the file path to a non-existent location to test fallback
        import os
        original_dirname = os.path.dirname
        
        def mock_dirname(path):
            return "/nonexistent/path"
        
        # Temporarily replace os.path.dirname to simulate file not found
        os.path.dirname = mock_dirname
        
        try:
            formatted_prompt = agent_executor._load_agent_summary_prompt(
                original_prompt="Test prompt",
                step_count=2,
                summary="Some summary",
                final_response="Some response"
            )
            
            # Should fall back to hardcoded prompt
            assert "Test prompt" in formatted_prompt
            assert "2 steps" in formatted_prompt
            assert "Some summary" in formatted_prompt
            assert "Some response" in formatted_prompt
            assert "Please provide a comprehensive summary" in formatted_prompt
            
        finally:
            # Restore original function
            os.path.dirname = original_dirname


if __name__ == "__main__":
    pytest.main([__file__, "-v"])