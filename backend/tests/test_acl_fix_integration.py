"""
Integration test to verify the ACL server name extraction fix.

This test validates that the actual fix in ChatService correctly handles
server names with underscores during ACL filtering.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from application.chat.service import ChatService
from domain.sessions.models import Session
from core.auth_utils import create_authorization_manager
import asyncio


class TestACLFixIntegration:
    """Integration test for the actual ACL fix in ChatService."""

    @pytest.fixture
    def mock_tool_manager_with_index(self):
        """Create a mock tool manager with properly built tool index."""
        mock_manager = Mock()
        
        # Mock the internal tool index as it would be built by MCPToolManager
        mock_manager._tool_index = {
            'pptx_generator_markdown_to_pptx': {
                'server': 'pptx_generator',
                'schema': {
                    'type': 'function',
                    'function': {
                        'name': 'pptx_generator_markdown_to_pptx',
                        'description': 'Convert markdown to PPTX'
                    }
                }
            },
            'thinking_thinking': {
                'server': 'thinking', 
                'schema': {
                    'type': 'function',
                    'function': {
                        'name': 'thinking_thinking',
                        'description': 'Think about something'
                    }
                }
            },
            'code_executor_run_python': {
                'server': 'code_executor',
                'schema': {
                    'type': 'function', 
                    'function': {
                        'name': 'code_executor_run_python',
                        'description': 'Execute Python code'
                    }
                }
            }
        }
        
        # Mock servers_config for authorization  
        mock_manager.servers_config = {
            'pptx_generator': {'groups': []},
            'thinking': {'groups': []}, 
            'code_executor': {'groups': []}
        }
        
        # Mock get_server_groups method
        mock_manager.get_server_groups = Mock(return_value=[])
        
        return mock_manager

    @pytest.fixture  
    def mock_llm_caller(self):
        """Create a mock LLM caller that returns a simple response."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.has_tool_calls.return_value = False
        
        mock_llm.call_with_tools = AsyncMock(return_value=mock_response)
        return mock_llm

    @pytest.fixture
    def chat_service_with_fix(self, mock_tool_manager_with_index, mock_llm_caller):
        """Create ChatService with the ACL fix applied."""
        return ChatService(
            llm=mock_llm_caller,
            tool_manager=mock_tool_manager_with_index,
            file_manager=None,
            connection=None
        )

    @pytest.mark.asyncio
    async def test_acl_fix_allows_underscore_server_tools(self, chat_service_with_fix):
        """
        Test that the ACL fix correctly allows tools from servers with underscores.
        
        This is the key integration test that verifies the fix works end-to-end.
        """
        # Mock the authorization manager to return all servers as authorized
        with patch('application.chat.service.create_authorization_manager') as mock_auth:
            mock_auth_instance = Mock()
            mock_auth_instance.filter_authorized_servers.return_value = [
                'thinking', 'pptx_generator', 'code_executor'
            ]
            mock_auth.return_value = mock_auth_instance
            
            # Patch the safe_get_tools_schema to capture what tools get through ACL
            captured_tools = []
            
            async def capture_tools(tool_manager, selected_tools):
                captured_tools.extend(selected_tools)
                # Return mock schemas for the captured tools
                return [
                    {'type': 'function', 'function': {'name': tool}} 
                    for tool in selected_tools
                ]
                
            with patch('application.chat.utilities.error_utils.safe_get_tools_schema', 
                      side_effect=capture_tools):
                
                # Test with tools from servers that have underscores in names
                session = Session(user_email="test@test.com")
                
                response = await chat_service_with_fix.handle_chat_message(
                    session_id=session.id,
                    user_email="test@test.com", 
                    content="Test message",
                    model="test-model",
                    selected_tools=[
                        'pptx_generator_markdown_to_pptx',  # Server: pptx_generator 
                        'thinking_thinking',                 # Server: thinking
                        'code_executor_run_python'          # Server: code_executor
                    ],
                    tool_choice_required=False
                )
                
                # Verify the fix: all tools should survive ACL filtering
                expected_tools = [
                    'pptx_generator_markdown_to_pptx',
                    'thinking_thinking', 
                    'code_executor_run_python'
                ]
                
                assert set(captured_tools) == set(expected_tools), (
                    f"ACL fix failed! Expected tools {expected_tools} to survive filtering, "
                    f"but got {captured_tools}"
                )
                
                # Verify response was generated
                assert response is not None
                assert "message" in response

    @pytest.mark.asyncio  
    async def test_acl_fix_fallback_for_missing_tool_index(self, chat_service_with_fix):
        """
        Test that the ACL fix gracefully handles case where tool index is not available.
        """
        # Remove the tool index to test fallback behavior
        chat_service_with_fix.tool_manager._tool_index = None
        chat_service_with_fix.tool_manager.available_tools = {
            'thinking': {
                'tools': [Mock(name='thinking')]
            },
            'pptx_generator': {
                'tools': [Mock(name='markdown_to_pptx')]
            }
        }
        
        with patch('application.chat.service.create_authorization_manager') as mock_auth:
            mock_auth_instance = Mock()
            mock_auth_instance.filter_authorized_servers.return_value = [
                'thinking', 'pptx_generator'
            ]
            mock_auth.return_value = mock_auth_instance
            
            captured_tools = []
            
            async def capture_tools(tool_manager, selected_tools):
                captured_tools.extend(selected_tools)
                return [{'type': 'function', 'function': {'name': tool}} for tool in selected_tools]
                
            with patch('application.chat.utilities.error_utils.safe_get_tools_schema', 
                      side_effect=capture_tools):
                
                session = Session(user_email="test@test.com")
                
                await chat_service_with_fix.handle_chat_message(
                    session_id=session.id,
                    user_email="test@test.com",
                    content="Test fallback",
                    model="test-model", 
                    selected_tools=[
                        'pptx_generator_markdown_to_pptx',
                        'thinking_thinking'
                    ],
                    tool_choice_required=False
                )
                
                # With the fix, both tools should survive even when using fallback logic
                # that builds temporary tool index from available_tools
                assert 'pptx_generator_markdown_to_pptx' in captured_tools
                assert 'thinking_thinking' in captured_tools