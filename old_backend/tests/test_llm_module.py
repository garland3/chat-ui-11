"""
Tests for the LLM module (10 tests).
"""
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from modules.llm import LLMCaller, LLMResponse


class TestLLMModule:
    """Test LLM module with 10 focused tests."""
    
    def test_llm_response_initialization(self):
        """Test LLMResponse initialization."""
        response = LLMResponse(content="test response")
        assert response.content == "test response"
        assert response.tool_calls is None
        assert response.model_used == ""
        assert response.tokens_used == 0
    
    def test_llm_response_has_tool_calls(self):
        """Test has_tool_calls method."""
        # No tool calls
        response1 = LLMResponse(content="test")
        assert response1.has_tool_calls() == False
        
        # With tool calls
        tool_calls = [{"function": {"name": "test_tool"}}]
        response2 = LLMResponse(content="test", tool_calls=tool_calls)
        assert response2.has_tool_calls() == True
    
    def test_llm_caller_initialization(self):
        """Test LLMCaller initialization."""
        mock_config = MagicMock()
        caller = LLMCaller(llm_config=mock_config)
        assert caller.llm_config == mock_config
    
    @pytest.mark.asyncio
    async def test_call_plain_success(self):
        """Test successful plain LLM call."""
        # Mock config
        mock_model_config = MagicMock()
        mock_model_config.model_url = "https://api.test.com"
        mock_model_config.api_key = "test-key"
        mock_model_config.model_name = "test-model"
        mock_model_config.max_tokens = 1000
        mock_model_config.extra_headers = None
        
        mock_llm_config = MagicMock()
        mock_llm_config.models = {"test-model": mock_model_config}
        
        caller = LLMCaller(llm_config=mock_llm_config)
        
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        
        messages = [{"role": "user", "content": "Test message"}]
        
        with patch('requests.post', return_value=mock_response):
            result = await caller.call_plain("test-model", messages)
        
        assert result == "Test response"
    
    @pytest.mark.asyncio
    async def test_call_plain_model_not_found(self):
        """Test plain call with model not found."""
        mock_llm_config = MagicMock()
        mock_llm_config.models = {}
        
        caller = LLMCaller(llm_config=mock_llm_config)
        messages = [{"role": "user", "content": "Test"}]
        
        with pytest.raises(ValueError, match="Model nonexistent not found"):
            await caller.call_plain("nonexistent", messages)
    
    @pytest.mark.asyncio
    async def test_call_plain_api_error(self):
        """Test plain call with API error."""
        mock_model_config = MagicMock()
        mock_model_config.model_url = "https://api.test.com"
        mock_model_config.api_key = "test-key"
        mock_model_config.model_name = "test-model"
        mock_model_config.max_tokens = 1000
        mock_model_config.extra_headers = None
        
        mock_llm_config = MagicMock()
        mock_llm_config.models = {"test-model": mock_model_config}
        
        caller = LLMCaller(llm_config=mock_llm_config)
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        messages = [{"role": "user", "content": "Test"}]
        
        with patch('requests.post', return_value=mock_response):
            with pytest.raises(Exception, match="LLM API error: 500"):
                await caller.call_plain("test-model", messages)
    
    @pytest.mark.asyncio
    async def test_call_with_tools_no_tools(self):
        """Test call with tools when no tools provided."""
        mock_llm_config = MagicMock()
        caller = LLMCaller(llm_config=mock_llm_config)
        
        with patch.object(caller, 'call_plain', return_value="Plain response"):
            result = await caller.call_with_tools(
                "test-model",
                [{"role": "user", "content": "Test"}],
                []
            )
        
        assert isinstance(result, LLMResponse)
        assert result.content == "Plain response"
        assert result.model_used == "test-model"
    
    @pytest.mark.asyncio
    async def test_call_with_rag_no_sources(self):
        """Test RAG call with no data sources."""
        caller = LLMCaller()
        
        with patch.object(caller, 'call_plain', return_value="Plain response"):
            result = await caller.call_with_rag(
                "test-model",
                [{"role": "user", "content": "Test"}],
                [],
                "user@test.com"
            )
        
        assert result == "Plain response"
    
    @pytest.mark.asyncio
    async def test_call_with_rag_success(self):
        """Test successful RAG call."""
        caller = LLMCaller()
        
        # Mock RAG response
        mock_rag_response = MagicMock()
        mock_rag_response.content = "RAG context content"
        mock_rag_response.metadata = None
        
        mock_rag_client = MagicMock()
        mock_rag_client.query_rag = AsyncMock(return_value=mock_rag_response)
        
        with patch.object(caller, 'call_plain', return_value="Enhanced response"):
            result = await caller.call_with_rag(
                "test-model",
                [{"role": "user", "content": "Test"}],
                ["datasource1"],
                "user@test.com",
                rag_client=mock_rag_client
            )
        
        assert result == "Enhanced response"
        mock_rag_client.query_rag.assert_called_once()
    
    def test_format_rag_metadata_unavailable(self):
        """Test RAG metadata formatting when unavailable."""
        caller = LLMCaller()
        result = caller._format_rag_metadata("invalid_metadata")
        assert result == "Metadata unavailable"