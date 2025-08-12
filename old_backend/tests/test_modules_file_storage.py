"""
Comprehensive tests for the File Storage module.
"""
import os
import sys
import base64
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import httpx

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from modules.file_storage import (
    S3StorageClient,
    FileManager,
    s3_client,
    file_manager
)


class TestS3StorageClient:
    """Test S3StorageClient class."""
    
    def test_s3_client_initialization_defaults(self):
        """Test S3StorageClient initialization with defaults."""
        with patch('modules.file_storage.s3_client.config_manager') as mock_config:
            mock_config.app_settings.s3_endpoint = "http://localhost:8003"
            mock_config.app_settings.s3_timeout = 30
            mock_config.app_settings.s3_use_mock = True
            
            client = S3StorageClient()
            assert client.base_url == "http://localhost:8003"
            assert client.timeout == 30
            assert client.use_mock == True
    
    def test_s3_client_initialization_custom(self):
        """Test S3StorageClient initialization with custom values."""
        client = S3StorageClient(
            s3_endpoint="http://custom:9000",
            s3_timeout=60,
            s3_use_mock=False
        )
        assert client.base_url == "http://custom:9000"
        assert client.timeout == 60
        assert client.use_mock == False
    
    def test_get_auth_headers_mock(self):
        """Test auth headers for mock service."""
        client = S3StorageClient(s3_use_mock=True)
        headers = client._get_auth_headers("test@example.com")
        assert headers["Authorization"] == "Bearer test@example.com"
    
    def test_get_auth_headers_real(self):
        """Test auth headers for real S3."""
        client = S3StorageClient(s3_use_mock=False)
        headers = client._get_auth_headers("test@example.com")
        # Real S3 headers not implemented yet
        assert headers == {}
    
    @pytest.mark.asyncio
    async def test_upload_file_success(self):
        """Test successful file upload."""
        client = S3StorageClient(s3_use_mock=True)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "key": "test-key-123",
            "size": 1024,
            "content_type": "text/plain"
        }
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_httpx.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await client.upload_file(
                user_email="test@example.com",
                filename="test.txt",
                content_base64="dGVzdCBjb250ZW50",  # "test content"
                content_type="text/plain"
            )
        
        assert result["key"] == "test-key-123"
        assert result["size"] == 1024
    
    @pytest.mark.asyncio
    async def test_upload_file_failure(self):
        """Test file upload failure."""
        client = S3StorageClient(s3_use_mock=True)
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_httpx.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            with pytest.raises(Exception, match="S3 upload failed"):
                await client.upload_file(
                    user_email="test@example.com",
                    filename="test.txt",
                    content_base64="dGVzdA==",
                    content_type="text/plain"
                )
    
    @pytest.mark.asyncio
    async def test_get_file_success(self):
        """Test successful file retrieval."""
        client = S3StorageClient(s3_use_mock=True)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "filename": "test.txt",
            "content_base64": "dGVzdCBjb250ZW50",
            "content_type": "text/plain"
        }
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await client.get_file("test@example.com", "test-key")
        
        assert result["filename"] == "test.txt"
        assert result["content_base64"] == "dGVzdCBjb250ZW50"
    
    @pytest.mark.asyncio
    async def test_get_file_not_found(self):
        """Test file retrieval when file not found."""
        client = S3StorageClient(s3_use_mock=True)
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await client.get_file("test@example.com", "nonexistent-key")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_list_files_success(self):
        """Test successful file listing."""
        client = S3StorageClient(s3_use_mock=True)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"filename": "file1.txt", "key": "key1", "size": 100},
            {"filename": "file2.jpg", "key": "key2", "size": 2048}
        ]
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await client.list_files("test@example.com")
        
        assert len(result) == 2
        assert result[0]["filename"] == "file1.txt"
    
    @pytest.mark.asyncio
    async def test_delete_file_success(self):
        """Test successful file deletion."""
        client = S3StorageClient(s3_use_mock=True)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_httpx.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_response)
            
            result = await client.delete_file("test@example.com", "test-key")
        
        assert result == True
    
    @pytest.mark.asyncio
    async def test_get_user_stats_success(self):
        """Test successful user stats retrieval."""
        client = S3StorageClient(s3_use_mock=True)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_files": 10,
            "total_size_bytes": 1024000,
            "user_files": 7,
            "tool_files": 3
        }
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_httpx.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await client.get_user_stats("test@example.com")
        
        assert result["total_files"] == 10
        assert result["user_files"] == 7


class TestFileManager:
    """Test FileManager class."""
    
    def test_file_manager_initialization(self):
        """Test FileManager initialization."""
        mock_s3_client = MagicMock()
        manager = FileManager(s3_client=mock_s3_client)
        assert manager.s3_client == mock_s3_client
    
    def test_get_content_type(self):
        """Test content type detection."""
        manager = FileManager()
        
        assert manager.get_content_type("test.txt") == "text/plain"
        assert manager.get_content_type("test.json") == "application/json"
        assert manager.get_content_type("test.py") == "text/x-python"
        assert manager.get_content_type("test.xyz") == "application/octet-stream"
        assert manager.get_content_type("noextension") == "application/octet-stream"
    
    def test_categorize_file_type(self):
        """Test file categorization."""
        manager = FileManager()
        
        assert manager.categorize_file_type("script.py") == "code"
        assert manager.categorize_file_type("image.png") == "image"
        assert manager.categorize_file_type("data.csv") == "data"
        assert manager.categorize_file_type("doc.pdf") == "document"
        assert manager.categorize_file_type("unknown.xyz") == "other"
    
    def test_get_file_extension(self):
        """Test file extension extraction."""
        manager = FileManager()
        
        assert manager.get_file_extension("test.txt") == ".txt"
        assert manager.get_file_extension("archive.tar.gz") == ".gz"
        assert manager.get_file_extension("noextension") == ""
    
    def test_get_canvas_file_type(self):
        """Test canvas file type determination."""
        manager = FileManager()
        
        assert manager.get_canvas_file_type(".png") == "image"
        assert manager.get_canvas_file_type(".pdf") == "pdf"
        assert manager.get_canvas_file_type(".html") == "html"
        assert manager.get_canvas_file_type(".py") == "text"
        assert manager.get_canvas_file_type(".xyz") == "other"
    
    def test_should_display_in_canvas(self):
        """Test canvas display determination."""
        manager = FileManager()
        
        # Should display
        assert manager.should_display_in_canvas("image.png") == True
        assert manager.should_display_in_canvas("script.py") == True
        assert manager.should_display_in_canvas("data.csv") == True
        assert manager.should_display_in_canvas("doc.pdf") == True
        
        # Should not display
        assert manager.should_display_in_canvas("binary.exe") == False
        assert manager.should_display_in_canvas("archive.zip") == False
    
    @pytest.mark.asyncio
    async def test_upload_file(self):
        """Test file upload through FileManager."""
        mock_s3_client = MagicMock()
        mock_s3_client.upload_file = AsyncMock(return_value={"key": "test-key"})
        
        manager = FileManager(s3_client=mock_s3_client)
        
        result = await manager.upload_file(
            user_email="test@example.com",
            filename="test.txt",
            content_base64="dGVzdA==",
            source_type="user"
        )
        
        assert result["key"] == "test-key"
        mock_s3_client.upload_file.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_multiple_files(self):
        """Test uploading multiple files."""
        mock_s3_client = MagicMock()
        mock_s3_client.upload_file = AsyncMock(side_effect=[
            {"key": "key1"}, {"key": "key2"}
        ])
        
        manager = FileManager(s3_client=mock_s3_client)
        
        files = {
            "file1.txt": "content1",
            "file2.py": "content2"
        }
        
        result = await manager.upload_multiple_files(
            user_email="test@example.com",
            files=files
        )
        
        assert result["file1.txt"] == "key1"
        assert result["file2.py"] == "key2"
        assert mock_s3_client.upload_file.call_count == 2
    
    def test_organize_files_metadata(self):
        """Test file metadata organization."""
        manager = FileManager()
        
        file_references = {
            "script.py": {
                "key": "key1",
                "size": 1024,
                "tags": {"source": "user"},
                "content_type": "text/x-python"
            },
            "image.png": {
                "key": "key2", 
                "size": 2048,
                "tags": {"source": "tool", "source_tool": "generator"},
                "content_type": "image/png"
            }
        }
        
        result = manager.organize_files_metadata(file_references)
        
        assert result["total_files"] == 2
        assert len(result["files"]) == 2
        assert len(result["categories"]["code"]) == 1
        assert len(result["categories"]["image"]) == 1
    
    def test_get_canvas_displayable_files(self):
        """Test canvas displayable files extraction."""
        manager = FileManager()
        
        result_dict = {
            "returned_files": [
                {"filename": "chart.png", "size": 1024},
                {"filename": "data.csv", "size": 512}
            ]
        }
        
        uploaded_files = {
            "chart.png": "s3-key-1",
            "data.csv": "s3-key-2"
        }
        
        canvas_files = manager.get_canvas_displayable_files(result_dict, uploaded_files)
        
        assert len(canvas_files) == 2
        assert canvas_files[0]["filename"] == "chart.png"
        assert canvas_files[0]["type"] == "image"
    
    @pytest.mark.asyncio
    async def test_get_file_content(self):
        """Test file content retrieval."""
        mock_s3_client = MagicMock()
        mock_s3_client.get_file = AsyncMock(return_value={
            "content_base64": "dGVzdCBjb250ZW50"
        })
        
        manager = FileManager(s3_client=mock_s3_client)
        
        result = await manager.get_file_content(
            user_email="test@example.com",
            filename="test.txt", 
            s3_key="test-key"
        )
        
        assert result == "dGVzdCBjb250ZW50"


class TestGlobalInstances:
    """Test global module instances."""
    
    def test_global_s3_client(self):
        """Test global s3_client instance."""
        assert s3_client is not None
        assert isinstance(s3_client, S3StorageClient)
    
    def test_global_file_manager(self):
        """Test global file_manager instance."""
        assert file_manager is not None
        assert isinstance(file_manager, FileManager)
        assert file_manager.s3_client == s3_client