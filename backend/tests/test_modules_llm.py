"""
Comprehensive tests for the LLM module.
"""
import os
import sys
import json
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import requests

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from modules.llm import (
    LLMCaller,
    LLMResponse,
    llm_caller
)


class TestLLMResponse:
    """Test LLMResponse class."""
    
    def test_llm_response_initialization(self):
        """Test LLMResponse initialization."""
        response = LLMResponse(content="test response")
        assert response.content == "test response"
        assert response.tool_calls is None
        assert response.model_used == ""
        assert response.tokens_used == 0
    
    def test_llm_response_with_tool_calls(self):
        """Test LLMResponse with tool calls."""
        tool_calls = [{"function": {"name": "test_tool"}}]
        response = LLMResponse(
            content="test",
            tool_calls=tool_calls,
            model_used="gpt-4",
            tokens_used=100
        )
        assert response.tool_calls == tool_calls
        assert response.model_used == "gpt-4"
        assert response.tokens_used == 100
    
    def test_has_tool_calls_true(self):
        """Test has_tool_calls returns True when tool calls present."""
        tool_calls = [{"function": {"name": "test_tool"}}]
        response = LLMResponse(content="test", tool_calls=tool_calls)
        assert response.has_tool_calls() == True
    
    def test_has_tool_calls_false_none(self):
        """Test has_tool_calls returns False when tool calls None."""
        response = LLMResponse(content="test")
        assert response.has_tool_calls() == False
    
    def test_has_tool_calls_false_empty(self):
        """Test has_tool_calls returns False when tool calls empty."""
        response = LLMResponse(content="test", tool_calls=[])
        assert response.has_tool_calls() == False


class TestLLMCaller:
    """Test LLMCaller class."""
    
    def test_llm_caller_initialization_default(self):
        """Test LLMCaller initialization with default config."""
        with patch('modules.llm.caller.config_manager') as mock_config:
            mock_config.llm_config.models = {"gpt-4": MagicMock()}
            caller = LLMCaller()
            assert caller.llm_config == mock_config.llm_config
    
    def test_llm_caller_initialization_custom(self):
        """Test LLMCaller initialization with custom config."""
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
        
        # Mock requests response
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
        
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        messages = [{"role": "user", "content": "Test"}]
        
        with patch('requests.post', return_value=mock_response):
            with pytest.raises(Exception, match="LLM API error: 500"):
                await caller.call_plain("test-model", messages)
    
    @pytest.mark.asyncio
    async def test_call_plain_with_extra_headers(self):
        """Test plain call with extra headers."""
        mock_model_config = MagicMock()
        mock_model_config.model_url = "https://api.test.com"
        mock_model_config.api_key = "test-key"
        mock_model_config.model_name = "test-model"
        mock_model_config.max_tokens = 1000
        mock_model_config.extra_headers = {"X-Custom": "value", "X-Env": "${TEST_VAR}"}
        
        mock_llm_config = MagicMock()
        mock_llm_config.models = {"test-model": mock_model_config}
        
        caller = LLMCaller(llm_config=mock_llm_config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        
        messages = [{"role": "user", "content": "Test"}]
        
        with patch.dict(os.environ, {"TEST_VAR": "resolved_value"}):
            with patch('requests.post', return_value=mock_response) as mock_post:
                await caller.call_plain("test-model", messages)
                
                # Check headers were added
                call_args = mock_post.call_args
                headers = call_args[1]["headers"]
                assert "X-Custom" in headers
                assert headers["X-Custom"] == "value"
                assert headers["X-Env"] == "resolved_value"
    
    @pytest.mark.asyncio
    async def test_call_with_tools_no_tools(self):
        """Test call with tools when no tools provided."""
        mock_model_config = MagicMock()
        mock_llm_config = MagicMock()
        mock_llm_config.models = {"test-model": mock_model_config}
        
        caller = LLMCaller(llm_config=mock_llm_config)
        
        # Mock the call_plain method
        with patch.object(caller, 'call_plain', return_value="Plain response") as mock_plain:
            result = await caller.call_with_tools(
                "test-model",
                [{"role": "user", "content": "Test"}],
                []
            )
        
        assert isinstance(result, LLMResponse)
        assert result.content == "Plain response"
        assert result.model_used == "test-model"
    
    @pytest.mark.asyncio
    async def test_call_with_tools_success(self):
        """Test successful call with tools."""
        mock_model_config = MagicMock()
        mock_model_config.model_url = "https://api.test.com"
        mock_model_config.api_key = "test-key"
        mock_model_config.model_name = "test-model"
        mock_model_config.max_tokens = 1000
        mock_model_config.extra_headers = None
        
        mock_llm_config = MagicMock()
        mock_llm_config.models = {"test-model": mock_model_config}
        
        caller = LLMCaller(llm_config=mock_llm_config)
        
        # Mock response with tool call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "I'll help with that calculation.",
                    "tool_calls": [{"function": {"name": "calculator"}}]
                }
            }]
        }
        
        tools_schema = [{"type": "function", "function": {"name": "calculator"}}]
        messages = [{"role": "user", "content": "Calculate 2+2"}]
        
        with patch('requests.post', return_value=mock_response):
            result = await caller.call_with_tools("test-model", messages, tools_schema)
        
        assert isinstance(result, LLMResponse)
        assert result.content == "I'll help with that calculation."
        assert result.has_tool_calls() == True
    
    @pytest.mark.asyncio
    async def test_call_with_rag_no_sources(self):
        """Test RAG call with no data sources."""
        caller = LLMCaller()
        
        with patch.object(caller, 'call_plain', return_value="Plain response") as mock_plain:
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
        
        # Mock RAG client
        mock_rag_response = MagicMock()
        mock_rag_response.content = "RAG context content"
        mock_rag_response.metadata = None
        
        mock_rag_client = MagicMock()
        mock_rag_client.query_rag = AsyncMock(return_value=mock_rag_response)
        
        with patch.object(caller, 'call_plain', return_value="Enhanced response") as mock_plain:
            result = await caller.call_with_rag(
                "test-model",
                [{"role": "user", "content": "Test"}],
                ["datasource1"],
                "user@test.com",
                rag_client=mock_rag_client
            )
        
        assert result == "Enhanced response"
        mock_rag_client.query_rag.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_with_rag_fallback(self):
        """Test RAG call fallback to plain call."""
        caller = LLMCaller()
        
        # Mock RAG client that raises exception
        mock_rag_client = MagicMock()
        mock_rag_client.query_rag = AsyncMock(side_effect=Exception("RAG error"))
        
        with patch.object(caller, 'call_plain', return_value="Fallback response") as mock_plain:
            result = await caller.call_with_rag(
                "test-model",
                [{"role": "user", "content": "Test"}],
                ["datasource1"],
                "user@test.com",
                rag_client=mock_rag_client
            )
        
        assert result == "Fallback response"
    
    @pytest.mark.asyncio
    async def test_call_with_rag_and_tools_no_sources(self):
        """Test RAG+tools call with no data sources."""
        caller = LLMCaller()
        
        mock_response = LLMResponse(content="Tools response")
        
        with patch.object(caller, 'call_with_tools', return_value=mock_response) as mock_tools:
            result = await caller.call_with_rag_and_tools(
                "test-model",
                [{"role": "user", "content": "Test"}],
                [],
                [{"type": "function"}],
                "user@test.com"
            )
        
        assert result == mock_response
    
    @pytest.mark.asyncio
    async def test_call_with_rag_and_tools_success(self):
        """Test successful RAG+tools call."""
        caller = LLMCaller()
        
        # Mock RAG response
        mock_rag_response = MagicMock()
        mock_rag_response.content = "RAG context"
        mock_rag_response.metadata = None
        
        mock_rag_client = MagicMock()
        mock_rag_client.query_rag = AsyncMock(return_value=mock_rag_response)
        
        # Mock LLM response
        llm_response = LLMResponse(content="Enhanced response with tools")
        
        with patch.object(caller, 'call_with_tools', return_value=llm_response) as mock_tools:
            result = await caller.call_with_rag_and_tools(
                "test-model",
                [{"role": "user", "content": "Test"}],
                ["datasource1"],
                [{"type": "function"}],
                "user@test.com",
                rag_client=mock_rag_client
            )
        
        assert result == llm_response
        mock_rag_client.query_rag.assert_called_once()
    
    def test_format_rag_metadata_unavailable(self):
        """Test RAG metadata formatting when unavailable."""
        caller = LLMCaller()
        result = caller._format_rag_metadata("invalid_metadata")
        assert result == "Metadata unavailable"
    
    def test_format_rag_metadata_import_error(self):
        """Test RAG metadata formatting with import error."""
        caller = LLMCaller()
        
        # Mock import error for RAGMetadata
        with patch('modules.llm.caller.RAGMetadata', side_effect=ImportError):
            result = caller._format_rag_metadata(MagicMock())
            assert result == "Metadata unavailable"


class TestGlobalLLMCaller:
    """Test global llm_caller instance."""
    
    def test_global_llm_caller_exists(self):
        """Test that global llm_caller exists."""
        assert llm_caller is not None
        assert isinstance(llm_caller, LLMCaller)
    
    def test_global_llm_caller_has_config(self):
        """Test that global llm_caller has config."""
        assert hasattr(llm_caller, 'llm_config')
        assert llm_caller.llm_config is not None