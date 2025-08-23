"""Unit tests for MCPToolManager refactored methods."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

from modules.mcp_tools.client import MCPToolManager
from domain.messages.models import ToolCall, ToolResult


class TestMCPToolManagerRefactoring:
    """Test suite for MCPToolManager refactored methods."""

    @pytest.fixture
    def mock_tool_manager(self):
        """Create a mock MCPToolManager instance with necessary setup."""
        manager = MCPToolManager()
        manager.servers_config = {
            "test_server": {"command": ["python", "test_script.py"]},
            "canvas": {}
        }
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "A test tool"
        mock_tool.inputSchema = {"type": "object"}
        
        manager.available_tools = {
            "test_server": {
                "tools": [mock_tool],
                "config": manager.servers_config["test_server"]
            },
            "canvas": {
                "tools": [],
                "config": manager.servers_config["canvas"]
            }
        }
        manager.clients = {
            "test_server": Mock()
        }
        return manager

    def test_ensure_tool_index_builds_index_once(self, mock_tool_manager):
        """Test that _ensure_tool_index builds index once and reuses it."""
        # First call should build the index
        index1 = mock_tool_manager._ensure_tool_index()
        
        # Second call should return the same cached index
        index2 = mock_tool_manager._ensure_tool_index()
        
        assert index1 is index2
        assert "test_server_test_tool" in index1
        assert "canvas_canvas" in index1
        assert index1["test_server_test_tool"]["server"] == "test_server"
        assert index1["canvas_canvas"]["server"] == "canvas"

    def test_log_tool_call_input_stage(self, mock_tool_manager):
        """Test that _log_tool_call properly logs input stage."""
        tool_call = ToolCall(
            id="test_id",
            name="test_tool", 
            arguments={"param1": "value1", "param2": "value2"}
        )
        
        with patch('modules.mcp_tools.client.logger') as mock_logger:
            mock_tool_manager._log_tool_call(
                tool_call, "test_server", "test_tool", "input"
            )
            
            # Should call logger.info with input format
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "TOOL_CALL_INPUT" in call_args
            assert "server=test_server" in call_args
            assert "tool=test_tool" in call_args
            assert "call_id=test_id" in call_args

    def test_log_tool_call_output_stage(self, mock_tool_manager):
        """Test that _log_tool_call properly logs output stage."""
        tool_call = ToolCall(
            id="test_id",
            name="test_tool",
            arguments={}
        )
        raw_result = {"results": "test output"}
        
        with patch('modules.mcp_tools.client.logger') as mock_logger:
            mock_tool_manager._log_tool_call(
                tool_call, "test_server", "test_tool", "output", raw_result
            )
            
            # Should call logger.info with output format
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "TOOL_CALL_OUTPUT" in call_args
            assert "server=test_server" in call_args
            assert "tool=test_tool" in call_args
            assert "success=True" in call_args

    def test_handle_canvas_tool(self, mock_tool_manager):
        """Test that _handle_canvas_tool returns proper ToolResult."""
        tool_call = ToolCall(
            id="canvas_test",
            name="canvas_canvas",
            arguments={"content": "Test canvas content"}
        )
        
        with patch.object(mock_tool_manager, '_log_tool_call') as mock_log:
            result = mock_tool_manager._handle_canvas_tool(tool_call)
            
            # Verify logging was called
            mock_log.assert_called_once_with(
                tool_call, "canvas", "canvas", "input"
            )
            
            # Verify result structure
            assert isinstance(result, ToolResult)
            assert result.tool_call_id == "canvas_test"
            assert result.success is True
            assert "Canvas content displayed" in result.content
            assert "Test canvas content" in result.content

    @pytest.mark.asyncio
    async def test_call_tool_with_canvas(self, mock_tool_manager):
        """Test that call_tool handles canvas tool correctly."""
        tool_call = ToolCall(
            id="canvas_test",
            name="canvas_canvas", 
            arguments={"content": "Test content"}
        )
        
        with patch.object(mock_tool_manager, '_handle_canvas_tool') as mock_handle:
            mock_handle.return_value = ToolResult(
                tool_call_id="canvas_test",
                content="Canvas handled",
                success=True
            )
            
            result = await mock_tool_manager.call_tool(tool_call)
            
            # Should delegate to _handle_canvas_tool
            mock_handle.assert_called_once_with(tool_call)
            assert result.content == "Canvas handled"
            assert result.success is True

    @pytest.mark.asyncio  
    async def test_call_tool_with_regular_tool(self, mock_tool_manager):
        """Test that call_tool handles regular MCP tools correctly."""
        tool_call = ToolCall(
            id="test_id",
            name="test_server_test_tool",
            arguments={"param": "value"}
        )
        
        # Mock the _call_mcp_tool method
        mock_result = {"results": "mocked output"}
        
        with patch.object(mock_tool_manager, '_call_mcp_tool', new_callable=AsyncMock) as mock_call_mcp, \
             patch.object(mock_tool_manager, '_log_tool_call') as mock_log, \
             patch.object(mock_tool_manager, '_create_progress_handler') as mock_progress, \
             patch.object(mock_tool_manager, '_normalize_mcp_tool_result') as mock_normalize, \
             patch.object(mock_tool_manager, '_extract_tool_result_components') as mock_extract:
            
            mock_call_mcp.return_value = mock_result
            mock_progress.return_value = AsyncMock()
            mock_normalize.return_value = {"results": "normalized"}
            mock_extract.return_value = ([], None, None)  # artifacts, display_config, meta_data
            
            result = await mock_tool_manager.call_tool(tool_call)
            
            # Verify method calls
            mock_call_mcp.assert_called_once()
            assert mock_log.call_count == 2  # Called twice - input and output
            mock_normalize.assert_called_once_with(mock_result)
            mock_extract.assert_called_once_with(mock_result)
            
            # Verify result
            assert isinstance(result, ToolResult)
            assert result.tool_call_id == "test_id"
            assert result.success is True
            content = json.loads(result.content)
            assert content["results"] == "normalized"

    def test_sanitize_tool_response_removes_sensitive_data(self, mock_tool_manager):
        """Test that _sanitize_tool_response removes base64 and large content."""
        # Test with structured_content attribute
        raw_result = Mock()
        raw_result.structured_content = {
            "results": "clean data",
            "returned_file_contents": "base64data...",
            "artifacts": ["artifact1"],
            "secret_b64": "encoded_secret"
        }
        
        sanitized = mock_tool_manager._sanitize_tool_response(raw_result)
        
        # Should remove sensitive fields and truncate
        assert "clean data" in sanitized
        assert "returned_file_contents" not in sanitized
        assert "artifacts" not in sanitized
        assert "secret_b64" not in sanitized
        assert len(sanitized) <= 500

    def test_extract_tool_result_components_parses_v2_response(self, mock_tool_manager):
        """Test that _extract_tool_result_components extracts v2 MCP components."""
        raw_result = {
            "artifacts": [
                {"name": "test.png", "b64": "base64data"}
            ],
            "display": {"type": "image"},
            "meta_data": {"source": "test"}
        }
        
        artifacts, display_config, meta_data = mock_tool_manager._extract_tool_result_components(raw_result)
        
        assert len(artifacts) == 1
        assert artifacts[0]["name"] == "test.png"
        assert display_config["type"] == "image"
        assert meta_data["source"] == "test"