"""
Test for ExecutionContext initialization issue in agent mode.

This test reproduces the error where ExecutionContext.__init__() gets
an unexpected keyword argument 'session'.
"""

import pytest
from unittest.mock import MagicMock

from agent_executor import AgentContext
from tool_executor import ExecutionContext


class TestExecutionContextIssue:
    """Test the ExecutionContext initialization issue."""
    
    def test_execution_context_session_argument_fixed(self):
        """Test that ExecutionContext can now be initialized with session argument."""
        # Create an AgentContext similar to what would be created in agent mode
        mock_session = MagicMock()
        mock_session.user_email = "test@example.com"
        
        agent_context = AgentContext(
            user_email="test@example.com",
            model_name="gpt-4",
            max_steps=5,
            tools_schema=[],
            tool_mapping={},
            session=mock_session,
            messages=[]
        )
        
        # This should now work without error
        execution_context = agent_context.to_execution_context()
        assert execution_context.user_email == "test@example.com"
        assert execution_context.session == mock_session
        assert execution_context.agent_mode == True
    
    def test_execution_context_direct_initialization(self):
        """Test ExecutionContext direct initialization with session keyword."""
        mock_session = MagicMock()
        
        # This should now work
        exec_context = ExecutionContext(
            user_email="test@example.com",
            session=mock_session,
            agent_mode=True
        )
        
        assert exec_context.user_email == "test@example.com"
        assert exec_context.session == mock_session
        assert exec_context.agent_mode == True
    
    def test_execution_context_positional_initialization(self):
        """Test ExecutionContext with positional arguments (should work)."""
        mock_session = MagicMock()
        
        # This should work because session is assigned as a class attribute
        exec_context = ExecutionContext("test@example.com")
        exec_context.session = mock_session
        exec_context.agent_mode = True
        
        assert exec_context.user_email == "test@example.com"
        assert exec_context.session == mock_session
        assert exec_context.agent_mode == True
        assert exec_context.should_send_ui_updates() == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])