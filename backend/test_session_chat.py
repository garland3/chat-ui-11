"""
Test file for session.py handle_chat_message method.

Tests both agent mode and regular mode functionality to ensure the refactored
architecture works correctly.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Import the classes we need to test
from session import ChatSession
from mcp_client import MCPToolManager


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.sent_messages = []
        self.client_state = MagicMock()
        self.client_state.name = "CONNECTED"
    
    async def send_text(self, data: str):
        """Mock send_text method."""
        self.sent_messages.append(json.loads(data))
    
    async def receive_text(self):
        """Mock receive_text method."""
        return '{"type": "test"}'


class MockMCPManager:
    """Mock MCP Tool Manager for testing."""
    
    def __init__(self):
        self.servers = ["test_server"]
    
    def get_tools_for_servers(self, servers):
        """Mock get_tools_for_servers."""
        return {
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "test_tool",
                        "description": "A test tool",
                        "parameters": {"type": "object", "properties": {}}
                    }
                }
            ],
            "mapping": {
                "test_tool": {
                    "server": "test_server",
                    "tool_name": "test_tool"
                }
            }
        }
    
    def is_server_exclusive(self, server_name: str) -> bool:
        """Mock is_server_exclusive."""
        return False
    
    async def call_tool(self, server_name: str, tool_name: str, args: Dict):
        """Mock call_tool."""
        return MagicMock(content=[MagicMock(text='{"result": "test_result"}')])


@pytest.fixture
def mock_websocket():
    """Fixture for mock WebSocket."""
    return MockWebSocket()


@pytest.fixture
def mock_mcp_manager():
    """Fixture for mock MCP manager."""
    return MockMCPManager()


@pytest.fixture
def mock_callbacks():
    """Fixture for mock callbacks."""
    return {}


@pytest.fixture
def chat_session(mock_websocket, mock_mcp_manager, mock_callbacks):
    """Fixture for ChatSession."""
    with patch('prompt_utils.load_system_prompt', return_value="Test system prompt"):
        session = ChatSession(
            websocket=mock_websocket,
            user_email="test@example.com",
            mcp_manager=mock_mcp_manager,
            callbacks=mock_callbacks
        )
    return session


class TestChatSessionRegularMode:
    """Test regular (non-agent) chat mode."""
    
    @pytest.mark.asyncio
    async def test_plain_llm_mode(self, chat_session):
        """Test plain LLM mode without tools or RAG."""
        message = {
            "content": "Hello, how are you?",
            "model": "gpt-4",
            "selected_tools": [],
            "selected_data_sources": [],
            "only_rag": False
        }
        
        # Mock the LLM response
        with patch('llm_processor.LLMProcessor.process_message') as mock_process:
            mock_result = MagicMock()
            mock_result.response = "I'm doing well, thank you!"
            mock_process.return_value = mock_result
            
            await chat_session.handle_chat_message(message)
            
            # Verify the message was processed
            assert mock_process.called
            
            # Check that response was sent
            sent_messages = chat_session.websocket.sent_messages
            assert len(sent_messages) > 0
            
            response_message = sent_messages[-1]
            assert response_message["type"] == "chat_response"
            assert response_message["message"] == "I'm doing well, thank you!"
            assert response_message["user"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_llm_with_tools_mode(self, chat_session):
        """Test LLM mode with tools enabled."""
        message = {
            "content": "Use the test tool",
            "model": "gpt-4", 
            "selected_tools": ["test_tool"],
            "selected_data_sources": [],
            "only_rag": False
        }
        
        with patch('llm_processor.LLMProcessor.process_message') as mock_process:
            mock_result = MagicMock()
            mock_result.response = "Tool executed successfully"
            mock_process.return_value = mock_result
            
            await chat_session.handle_chat_message(message)
            
            # Verify the message was processed with tools
            assert mock_process.called
            
            # Check the processing context passed to the processor
            call_args = mock_process.call_args[0][0]  # First argument (context)
            assert call_args.selected_tools == ["test_tool"]
            assert call_args.agent_mode == False
            
            # Check response was sent
            sent_messages = chat_session.websocket.sent_messages
            response_message = sent_messages[-1]
            assert response_message["type"] == "chat_response"
            assert response_message["message"] == "Tool executed successfully"
    
    @pytest.mark.asyncio
    async def test_rag_only_mode(self, chat_session):
        """Test RAG-only mode."""
        message = {
            "content": "What does the document say?",
            "model": "gpt-4",
            "selected_tools": [],
            "selected_data_sources": ["test_docs"],
            "only_rag": True
        }
        
        with patch('llm_processor.LLMProcessor.process_message') as mock_process:
            mock_result = MagicMock()
            mock_result.response = "According to the document..."
            mock_process.return_value = mock_result
            
            await chat_session.handle_chat_message(message)
            
            # Verify RAG processing
            assert mock_process.called
            call_args = mock_process.call_args[0][0]
            assert call_args.selected_data_sources == ["test_docs"]
            assert call_args.only_rag == True
    
    @pytest.mark.asyncio
    async def test_file_upload_handling(self, chat_session):
        """Test handling of file uploads."""
        message = {
            "content": "Analyze this file",
            "model": "gpt-4",
            "selected_tools": ["test_tool"],
            "files": {
                "test.pdf": "base64encodedcontent"
            }
        }
        
        with patch('llm_processor.LLMProcessor.process_message') as mock_process:
            mock_result = MagicMock()
            mock_result.response = "File analyzed"
            mock_process.return_value = mock_result
            
            await chat_session.handle_chat_message(message)
            
            # Check that files were stored in session
            assert "test.pdf" in chat_session.uploaded_files
            assert chat_session.uploaded_files["test.pdf"] == "base64encodedcontent"
            
            # Check that content was enhanced with file info
            call_args = mock_process.call_args[0][0]
            assert "test.pdf" in call_args.content


class TestChatSessionAgentMode:
    """Test agent mode functionality."""
    
    @pytest.mark.asyncio
    async def test_agent_mode_basic(self, chat_session):
        """Test basic agent mode execution."""
        message = {
            "content": "Solve this complex problem step by step",
            "model": "gpt-4",
            "selected_tools": ["test_tool"],
            "agent_mode": True
        }
        
        # Mock the agent executor result
        with patch.object(chat_session.message_processor, 'handle_agent_mode_message') as mock_agent:
            await chat_session.handle_chat_message(message)
            
            # Verify agent mode was triggered
            assert mock_agent.called
            call_args = mock_agent.call_args[0][0]
            assert call_args["content"] == "Solve this complex problem step by step"
            assert call_args["agent_mode"] == True
    
    @pytest.mark.asyncio 
    async def test_agent_mode_with_tools(self, chat_session):
        """Test agent mode with tools."""
        message = {
            "content": "Use tools to research and analyze",
            "model": "gpt-4",
            "selected_tools": ["test_tool", "another_tool"],
            "agent_mode": True
        }
        
        with patch.object(chat_session.message_processor, 'handle_agent_mode_message') as mock_agent:
            await chat_session.handle_chat_message(message)
            
            # Check that tools were passed correctly
            assert mock_agent.called
            call_args = mock_agent.call_args[0][0]
            assert "test_tool" in call_args["selected_tools"]
            assert "another_tool" in call_args["selected_tools"]
    
    @pytest.mark.asyncio
    async def test_agent_mode_file_handling(self, chat_session):
        """Test agent mode with file uploads."""
        message = {
            "content": "Analyze these files systematically",
            "model": "gpt-4",
            "selected_tools": ["file_analyzer"],
            "agent_mode": True,
            "files": {
                "report.pdf": "base64content1",
                "data.csv": "base64content2"
            }
        }
        
        with patch.object(chat_session.message_processor, 'handle_agent_mode_message') as mock_agent:
            await chat_session.handle_chat_message(message)
            
            # Files should be available in session
            assert "report.pdf" in chat_session.uploaded_files
            assert "data.csv" in chat_session.uploaded_files
            
            # Agent mode handler should be called
            assert mock_agent.called


class TestErrorHandling:
    """Test error handling in chat message processing."""
    
    @pytest.mark.asyncio
    async def test_missing_content_error(self, chat_session):
        """Test error when message content is missing."""
        message = {
            "model": "gpt-4"
            # Missing "content"
        }
        
        with patch.object(chat_session, 'send_error') as mock_send_error:
            await chat_session.handle_chat_message(message)
            
            # Should send an error message
            assert mock_send_error.called
            error_message = mock_send_error.call_args[0][0]
            assert "Error processing message" in error_message
    
    @pytest.mark.asyncio
    async def test_missing_model_error(self, chat_session):
        """Test error when model name is missing."""
        message = {
            "content": "Hello"
            # Missing "model"
        }
        
        with patch.object(chat_session, 'send_error') as mock_send_error:
            await chat_session.handle_chat_message(message)
            
            # Should send an error message
            assert mock_send_error.called
    
    @pytest.mark.asyncio
    async def test_processing_error_handling(self, chat_session):
        """Test handling of errors during message processing."""
        message = {
            "content": "Test message",
            "model": "gpt-4",
            "selected_tools": []
        }
        
        # Mock processor to raise an exception
        with patch('llm_processor.LLMProcessor.process_message') as mock_process:
            mock_process.side_effect = Exception("Processing failed")
            
            with patch.object(chat_session, 'send_error') as mock_send_error:
                await chat_session.handle_chat_message(message)
                
                # Should handle the error gracefully
                assert mock_send_error.called
                error_message = mock_send_error.call_args[0][0]
                assert "Error processing message" in error_message


class TestCallbacks:
    """Test callback system in chat message handling."""
    
    @pytest.mark.asyncio
    async def test_callback_triggering(self, mock_websocket, mock_mcp_manager):
        """Test that callbacks are triggered at the right times."""
        callback_calls = []
        
        async def test_callback(session, **kwargs):
            callback_calls.append(kwargs.get('event', 'unknown'))
        
        callbacks = {
            'before_message_processing': [test_callback],
            'after_response_send': [test_callback]
        }
        
        with patch('prompt_utils.load_system_prompt', return_value="Test system prompt"):
            session = ChatSession(
                websocket=mock_websocket,
                user_email="test@example.com", 
                mcp_manager=mock_mcp_manager,
                callbacks=callbacks
            )
        
        message = {
            "content": "Test",
            "model": "gpt-4",
            "selected_tools": []
        }
        
        with patch('llm_processor.LLMProcessor.process_message') as mock_process:
            mock_result = MagicMock()
            mock_result.response = "Test response"
            mock_process.return_value = mock_result
            
            await session.handle_chat_message(message)
            
            # Callbacks should have been triggered
            # Note: The actual callback mechanism would need to be tested
            # based on the specific implementation


def run_tests():
    """Run all tests."""
    print("Running ChatSession tests...")
    
    # Run with pytest
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "test_session_chat.py", 
        "-v", "--tb=short"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0


if __name__ == "__main__":
    # Example of how to run individual tests
    import asyncio
    
    async def run_sample_test():
        """Run a sample test to verify the setup."""
        websocket = MockWebSocket()
        mcp_manager = MockMCPManager()
        callbacks = {}
        
        with patch('prompt_utils.load_system_prompt', return_value="Test system prompt"):
            session = ChatSession(
                websocket=websocket,
                user_email="test@example.com",
                mcp_manager=mcp_manager,
                callbacks=callbacks
            )
        
        # Test regular mode
        message = {
            "content": "Hello!",
            "model": "gpt-4",
            "selected_tools": []
        }
        
        with patch('llm_processor.LLMProcessor.process_message') as mock_process:
            mock_result = MagicMock()
            mock_result.response = "Hello! How can I help you?"
            mock_process.return_value = mock_result
            
            await session.handle_chat_message(message)
            
            print("✅ Regular mode test passed")
            print(f"Response sent: {websocket.sent_messages[-1]['message']}")
        
        # Test agent mode
        agent_message = {
            "content": "Solve this step by step",
            "model": "gpt-4", 
            "selected_tools": ["test_tool"],
            "agent_mode": True
        }
        
        with patch.object(session.message_processor, 'handle_agent_mode_message') as mock_agent:
            await session.handle_chat_message(agent_message)
            print("✅ Agent mode test passed")
            print(f"Agent mode triggered: {mock_agent.called}")
    
    # Run the sample test
    asyncio.run(run_sample_test())
    print("\n" + "="*50)
    print("To run all tests, use: python -m pytest test_session_chat.py -v")