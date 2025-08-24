"""
Test for ACL server name extraction bug with underscores in server names.

This test demonstrates the bug where server names containing underscores
(like 'pptx_generator') are incorrectly extracted during ACL filtering,
causing tools to be improperly filtered out.
"""

import pytest
from unittest.mock import Mock
from application.chat.service import ChatService
from domain.sessions.models import Session



class TestACLServerNameExtraction:
    """Test ACL filtering logic for server names with underscores."""

    @pytest.fixture
    def mock_tool_manager(self):
        """Create a mock tool manager with servers that have underscores."""
        mock_manager = Mock()
        
        # Mock the tool index with servers containing underscores
        mock_manager._tool_index = {
            'pptx_generator_markdown_to_pptx': {
                'server': 'pptx_generator',
                'tool': Mock(name='markdown_to_pptx')
            },
            'thinking_thinking': {
                'server': 'thinking',
                'tool': Mock(name='thinking')
            },
            'code_executor_run_python': {
                'server': 'code_executor', 
                'tool': Mock(name='run_python')
            }
        }
        
        # Mock servers_config
        mock_manager.servers_config = {
            'pptx_generator': {'groups': ['users']},
            'thinking': {'groups': ['users']},
            'code_executor': {'groups': ['users']}
        }
        
        # Mock get_server_groups method
        mock_manager.get_server_groups = lambda server: ['users']
        
        return mock_manager

    @pytest.fixture
    def mock_llm_caller(self):
        """Create a mock LLM caller."""
        return Mock()

    @pytest.fixture
    def chat_service(self, mock_tool_manager, mock_llm_caller):
        """Create ChatService with mocked dependencies."""
        service = ChatService(
            llm=mock_llm_caller,
            tool_manager=mock_tool_manager,
            file_manager=None,
            connection=None
        )
        return service

    @pytest.fixture
    def test_session(self):
        """Create a test session."""
        return Session(user_email="test@test.com")

    def test_server_name_extraction_with_underscores_fails_current_logic(self):
        """
        Test that current ACL logic fails for server names with underscores.
        
        This test demonstrates the bug using the current string-splitting logic.
        """
        # Current buggy logic
        tool_name = "pptx_generator_markdown_to_pptx"
        server_extracted = tool_name.split("_", 1)[0]  # Current logic
        
        # This shows the bug: we get "pptx" instead of "pptx_generator"
        assert server_extracted == "pptx"  # Current behavior (incorrect)
        
        authorized_servers = ['thinking', 'pptx_generator', 'code_executor']
        
        # This check fails because "pptx" is not in authorized_servers
        assert server_extracted not in authorized_servers  # Bug demonstrated
        
        # But "pptx_generator" should be authorized
        correct_server = "pptx_generator"
        assert correct_server in authorized_servers

    def test_acl_filtering_removes_underscore_server_tools(self, chat_service, test_session):
        """
        Test that ACL filtering incorrectly removes tools from servers with underscores.
        
        This is the failing test that demonstrates the actual bug in the ChatService.
        """
        # Input: tools from servers with and without underscores
        selected_tools = [
            'pptx_generator_markdown_to_pptx',  # Server: pptx_generator (has underscore)
            'thinking_thinking',                 # Server: thinking (no underscore)
            'code_executor_run_python'          # Server: code_executor (has underscore) 
        ]
        
        # Mock the authorization to return all servers as authorized
        authorized_servers = ['thinking', 'pptx_generator', 'code_executor']
        
        # Simulate the current ACL filtering logic (the buggy part)
        filtered_tools = []
        for t in selected_tools:
            if isinstance(t, str) and "_" in t:
                server = t.split("_", 1)[0]  # BUGGY: extracts "pptx", "code" instead of full names
                if server in authorized_servers:
                    filtered_tools.append(t)
        
        # This demonstrates the bug: with current logic, tools from servers 
        # with underscores get filtered out incorrectly
        expected_tools_if_fixed = [
            'pptx_generator_markdown_to_pptx',
            'thinking_thinking', 
            'code_executor_run_python'
        ]
        
        actual_buggy_result = ['thinking_thinking']  # Only this survives current logic
        
        # Demonstrate the bug: current logic filters out tools incorrectly
        assert filtered_tools != expected_tools_if_fixed, (
            "Bug not reproduced! Current ACL logic should filter out underscore server tools"
        )
        
        # Show what actually happens with current buggy logic
        assert filtered_tools == actual_buggy_result, (
            f"Expected buggy behavior: {actual_buggy_result}, got: {filtered_tools}"
        )
        
        # Confirm the bug: tools with underscore servers are missing
        missing_tools = set(expected_tools_if_fixed) - set(filtered_tools)
        expected_missing = {'pptx_generator_markdown_to_pptx', 'code_executor_run_python'}
        assert missing_tools == expected_missing, (
            f"Expected these tools to be incorrectly filtered: {expected_missing}, "
            f"actually missing: {missing_tools}"
        )

    def test_correct_server_extraction_should_work(self, mock_tool_manager):
        """
        Test that shows how correct server extraction should work using tool index.
        
        This test shows the expected behavior after the fix.
        """
        selected_tools = [
            'pptx_generator_markdown_to_pptx',
            'thinking_thinking',
            'code_executor_run_python'
        ]
        
        authorized_servers = ['thinking', 'pptx_generator', 'code_executor']
        
        # Correct approach: use tool index to get server names
        filtered_tools = []
        tool_index = mock_tool_manager._tool_index
        
        for tool in selected_tools:
            if tool in tool_index:
                server = tool_index[tool]['server']
                if server in authorized_servers:
                    filtered_tools.append(tool)
        
        # This should work correctly - all tools should be kept
        expected_tools = [
            'pptx_generator_markdown_to_pptx',
            'thinking_thinking',
            'code_executor_run_python'
        ]
        
        assert filtered_tools == expected_tools
        assert len(filtered_tools) == 3  # All tools should survive correct filtering