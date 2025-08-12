"""
Tests for the File Storage module (10 tests).
"""
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from modules.file_storage import S3StorageClient, FileManager


class TestFileStorageModule:
    """Test File Storage module with 10 focused tests."""
    
    def test_s3_client_initialization(self):
        """Test S3StorageClient initialization with custom values."""
        client = S3StorageClient(
            s3_endpoint="http://test:9000",
            s3_timeout=60,
            s3_use_mock=False
        )
        assert client.base_url == "http://test:9000"
        assert client.timeout == 60
        assert client.use_mock == False
    
    def test_auth_headers_mock_service(self):
        """Test auth headers for mock service."""
        client = S3StorageClient(s3_use_mock=True)
        headers = client._get_auth_headers("test@example.com")
        assert headers["Authorization"] == "Bearer test@example.com"
    
    @pytest.mark.asyncio
    async def test_upload_file_success(self):
        """Test successful file upload."""
        client = S3StorageClient(s3_use_mock=True)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"key": "test-key-123", "size": 1024}
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_httpx.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await client.upload_file(
                user_email="test@example.com",
                filename="test.txt",
                content_base64="dGVzdA==",
                content_type="text/plain"
            )
        
        assert result["key"] == "test-key-123"
    
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
    
    def test_file_manager_content_type_detection(self):
        """Test content type detection."""
        manager = FileManager()
        assert manager.get_content_type("test.txt") == "text/plain"
        assert manager.get_content_type("test.json") == "application/json"
        assert manager.get_content_type("test.py") == "text/x-python"
        assert manager.get_content_type("unknown.xyz") == "application/octet-stream"
    
    def test_file_categorization(self):
        """Test file categorization."""
        manager = FileManager()
        assert manager.categorize_file_type("script.py") == "code"
        assert manager.categorize_file_type("image.png") == "image"
        assert manager.categorize_file_type("data.csv") == "data"
        assert manager.categorize_file_type("doc.pdf") == "document"
        assert manager.categorize_file_type("unknown.xyz") == "other"
    
    def test_canvas_display_determination(self):
        """Test canvas display determination."""
        manager = FileManager()
        assert manager.should_display_in_canvas("image.png") == True
        assert manager.should_display_in_canvas("script.py") == True
        assert manager.should_display_in_canvas("binary.exe") == False
    
    def test_file_extension_extraction(self):
        """Test file extension extraction."""
        manager = FileManager()
        assert manager.get_file_extension("test.txt") == ".txt"
        assert manager.get_file_extension("noextension") == ""
    
    @pytest.mark.asyncio
    async def test_upload_multiple_files(self):
        """Test uploading multiple files."""
        mock_s3_client = MagicMock()
        mock_s3_client.upload_file = AsyncMock(side_effect=[
            {"key": "key1"}, {"key": "key2"}
        ])
        
        manager = FileManager(s3_client=mock_s3_client)
        files = {"file1.txt": "content1", "file2.py": "content2"}
        
        result = await manager.upload_multiple_files("test@example.com", files)
        
        assert result["file1.txt"] == "key1"
        assert result["file2.py"] == "key2"
        assert mock_s3_client.upload_file.call_count == 2
    
    def test_organize_files_metadata(self):
        """Test file metadata organization."""
        manager = FileManager()
        
        file_references = {
            "script.py": {
                "key": "key1", "size": 1024, "tags": {"source": "user"}
            },
            "image.png": {
                "key": "key2", "size": 2048, "tags": {"source": "tool"}
            }
        }
        
        result = manager.organize_files_metadata(file_references)
        
        assert result["total_files"] == 2
        assert len(result["categories"]["code"]) == 1
        assert len(result["categories"]["image"]) == 1