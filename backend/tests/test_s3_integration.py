"""
Tests for S3 storage integration including client and session functionality.

These tests verify that the S3 storage system works correctly for file
upload, download, listing, deletion, and user authorization.
"""

import asyncio
import base64
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

import httpx
from s3_client import S3StorageClient, s3_client
from session import ChatSession
from mcp_client import MCPToolManager


class TestS3StorageClient:
    """Test cases for the S3StorageClient."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = MagicMock()
        config.s3_endpoint = "http://localhost:8003"
        config.s3_use_mock = True
        config.s3_timeout = 30
        return config
    
    @pytest.fixture
    def s3_client_instance(self, mock_config):
        """Create S3 client instance with mocked config."""
        with patch('s3_client.config_manager.app_settings', mock_config):
            return S3StorageClient()
    
    @pytest.mark.asyncio
    async def test_upload_file_success(self, s3_client_instance):
        """Test successful file upload to S3."""
        # Mock HTTP response
        mock_response = {
            "key": "users/test@example.com/uploads/123_test.txt",
            "filename": "test.txt",
            "size": 12,
            "content_type": "text/plain",
            "last_modified": datetime.utcnow().isoformat(),
            "etag": "abc123",
            "tags": {"source": "user"},
            "user_email": "test@example.com"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response_obj
            
            result = await s3_client_instance.upload_file(
                user_email="test@example.com",
                filename="test.txt",
                content_base64=base64.b64encode(b"Hello World!").decode(),
                content_type="text/plain",
                source_type="user"
            )
            
            assert result["key"] == "users/test@example.com/uploads/123_test.txt"
            assert result["filename"] == "test.txt"
            assert result["user_email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_get_file_success(self, s3_client_instance):
        """Test successful file retrieval from S3."""
        mock_response = {
            "key": "users/test@example.com/uploads/123_test.txt",
            "filename": "test.txt",
            "content_base64": base64.b64encode(b"Hello World!").decode(),
            "content_type": "text/plain",
            "size": 12,
            "last_modified": datetime.utcnow().isoformat(),
            "etag": "abc123",
            "tags": {"source": "user"}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response_obj
            
            result = await s3_client_instance.get_file(
                user_email="test@example.com",
                file_key="users/test@example.com/uploads/123_test.txt"
            )
            
            assert result["filename"] == "test.txt"
            assert result["content_base64"] == base64.b64encode(b"Hello World!").decode()
    
    @pytest.mark.asyncio
    async def test_get_file_not_found(self, s3_client_instance):
        """Test file retrieval when file doesn't exist."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 404
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response_obj
            
            result = await s3_client_instance.get_file(
                user_email="test@example.com",
                file_key="nonexistent_key"
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_list_files_success(self, s3_client_instance):
        """Test successful file listing."""
        mock_response = [
            {
                "key": "users/test@example.com/uploads/123_test1.txt",
                "filename": "test1.txt",
                "size": 10,
                "content_type": "text/plain",
                "last_modified": datetime.utcnow().isoformat(),
                "etag": "abc123",
                "tags": {"source": "user"},
                "user_email": "test@example.com"
            },
            {
                "key": "users/test@example.com/generated/456_test2.png",
                "filename": "test2.png", 
                "size": 1024,
                "content_type": "image/png",
                "last_modified": datetime.utcnow().isoformat(),
                "etag": "def456",
                "tags": {"source": "tool", "source_tool": "plot"},
                "user_email": "test@example.com"
            }
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response_obj
            
            result = await s3_client_instance.list_files(user_email="test@example.com")
            
            assert len(result) == 2
            assert result[0]["filename"] == "test1.txt"
            assert result[1]["filename"] == "test2.png"
    
    @pytest.mark.asyncio
    async def test_delete_file_success(self, s3_client_instance):
        """Test successful file deletion."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            
            mock_client.return_value.__aenter__.return_value.delete.return_value = mock_response_obj
            
            result = await s3_client_instance.delete_file(
                user_email="test@example.com",
                file_key="users/test@example.com/uploads/123_test.txt"
            )
            
            assert result is True


class TestSessionS3Integration:
    """Test cases for ChatSession S3 integration."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket for testing."""
        mock_ws = MagicMock()
        mock_ws.client_state.name = "CONNECTED"
        return mock_ws
    
    @pytest.fixture
    def mock_mcp_manager(self):
        """Mock MCP manager for testing."""
        return MagicMock(spec=MCPToolManager)
    
    @pytest.fixture
    def session(self, mock_websocket, mock_mcp_manager):
        """Create a ChatSession instance for testing."""
        with patch('session.load_system_prompt', return_value="System prompt"):
            return ChatSession(
                websocket=mock_websocket,
                user_email="test@example.com",
                mcp_manager=mock_mcp_manager,
                callbacks={}
            )
    
    @pytest.mark.asyncio
    async def test_upload_files_to_s3(self, session):
        """Test uploading files to S3 through session."""
        # Mock S3 client upload
        mock_upload_response = {
            "key": "users/test@example.com/uploads/123_test.txt",
            "filename": "test.txt",
            "size": 12,
            "content_type": "text/plain",
            "last_modified": datetime.utcnow().isoformat(),
            "etag": "abc123",
            "tags": {"source": "user"},
            "user_email": "test@example.com"
        }
        
        with patch.object(session, 'send_files_update') as mock_send_update:
            with patch('s3_client.s3_client.upload_file', return_value=mock_upload_response) as mock_upload:
                files = {"test.txt": base64.b64encode(b"Hello World!").decode()}
                
                await session.upload_files_to_s3_async(files)
                
                # Verify file was uploaded to S3
                mock_upload.assert_called_once_with(
                    user_email="test@example.com",
                    filename="test.txt",
                    content_base64=base64.b64encode(b"Hello World!").decode(),
                    content_type="text/plain",
                    source_type="user"
                )
                
                # Verify session state was updated
                assert "test.txt" in session.uploaded_files
                assert session.uploaded_files["test.txt"] == "users/test@example.com/uploads/123_test.txt"
                assert "test.txt" in session.file_references
                
                # Verify UI was updated
                mock_send_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_generated_file(self, session):
        """Test storing tool-generated files."""
        mock_upload_response = {
            "key": "users/test@example.com/generated/456_plot.png",
            "filename": "plot.png",
            "size": 1024,
            "content_type": "image/png",
            "last_modified": datetime.utcnow().isoformat(),
            "etag": "def456",
            "tags": {"source": "tool", "source_tool": "plot"},
            "user_email": "test@example.com"
        }
        
        with patch.object(session, 'send_files_update') as mock_send_update:
            with patch('s3_client.s3_client.upload_file', return_value=mock_upload_response) as mock_upload:
                s3_key = await session.store_generated_file_in_s3(
                    filename="plot.png",
                    content_base64=base64.b64encode(b"fake_image_data").decode(),
                    source_tool="plot"
                )
                
                # Verify file was uploaded with correct parameters
                mock_upload.assert_called_once_with(
                    user_email="test@example.com",
                    filename="plot.png",
                    content_base64=base64.b64encode(b"fake_image_data").decode(),
                    content_type="image/png",
                    tags={"source_tool": "plot"},
                    source_type="tool"
                )
                
                # Verify return value
                assert s3_key == "users/test@example.com/generated/456_plot.png"
                
                # Verify session state
                assert "plot.png" in session.uploaded_files
                assert session.uploaded_files["plot.png"] == s3_key
    
    @pytest.mark.asyncio
    async def test_get_file_content_by_name(self, session):
        """Test retrieving file content by filename."""
        # Set up session state
        session.uploaded_files["test.txt"] = "users/test@example.com/uploads/123_test.txt"
        
        mock_file_data = {
            "key": "users/test@example.com/uploads/123_test.txt",
            "filename": "test.txt",
            "content_base64": base64.b64encode(b"Hello World!").decode(),
            "content_type": "text/plain",
            "size": 12
        }
        
        with patch('s3_client.s3_client.get_file', return_value=mock_file_data) as mock_get:
            content = await session.get_file_content_by_name("test.txt")
            
            mock_get.assert_called_once_with(
                "test@example.com",
                "users/test@example.com/uploads/123_test.txt"
            )
            
            assert content == base64.b64encode(b"Hello World!").decode()
    
    @pytest.mark.asyncio 
    async def test_get_file_content_not_found(self, session):
        """Test retrieving content for non-existent file."""
        content = await session.get_file_content_by_name("nonexistent.txt")
        assert content is None
    
    def test_get_content_type(self, session):
        """Test content type detection."""
        assert session._get_content_type("test.txt") == "text/plain"
        assert session._get_content_type("image.png") == "image/png"
        assert session._get_content_type("data.json") == "application/json"
        assert session._get_content_type("unknown.xyz") == "application/octet-stream"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__])