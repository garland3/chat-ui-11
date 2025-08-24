"""
Tests for the Direct S3 Reference Pipeline implementation.

These tests verify that the backend properly handles MCP v2 artifacts with S3 URLs
without re-uploading the files to S3.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from application.chat.utilities.file_utils import (
    ingest_v2_artifacts,
    extract_file_key_from_s3_url,
    validate_user_file_access
)
from modules.file_storage.manager import FileManager


class TestDirectS3ReferencePipeline:
    """Test the direct S3 reference pipeline implementation."""

    @pytest.fixture
    def mock_file_manager(self):
        """Create a mock file manager."""
        file_manager = Mock(spec=FileManager)
        file_manager.s3_client = AsyncMock()
        file_manager.upload_files_from_base64 = AsyncMock()
        file_manager.organize_files_metadata = Mock()
        return file_manager

    @pytest.fixture
    def mock_tool_result(self):
        """Create a mock tool result with artifacts."""
        tool_result = Mock()
        tool_result.artifacts = [
            {
                "name": "test_file.csv",
                "url": "/api/files/download/users/test@example.com/generated/1234567890_abc123_test_file.csv",
                "mime": "text/csv",
                "size": 1024
            },
            {
                "name": "test_report.txt",
                "b64": "dGVzdCBjb250ZW50",
                "mime": "text/plain",
                "size": 12
            }
        ]
        return tool_result

    @pytest.mark.asyncio
    async def test_extract_file_key_from_s3_url(self):
        """Test extracting file key from S3 URL."""
        # Test valid URL
        url = "/api/files/download/users/test@example.com/generated/1234567890_abc123_test_file.csv"
        expected_key = "users/test@example.com/generated/1234567890_abc123_test_file.csv"
        assert extract_file_key_from_s3_url(url) == expected_key

        # Test URL with query parameters
        url_with_params = "/api/files/download/users/test@example.com/generated/1234567890_abc123_test_file.csv?token=xyz"
        assert extract_file_key_from_s3_url(url_with_params) == expected_key

        # Test invalid URL
        invalid_url = "/some/other/path/file.csv"
        assert extract_file_key_from_s3_url(invalid_url) is None

        # Test empty URL
        assert extract_file_key_from_s3_url("") is None
        assert extract_file_key_from_s3_url(None) is None

    @pytest.mark.asyncio
    async def test_validate_user_file_access_success(self, mock_file_manager):
        """Test validating user file access with valid file."""
        user_email = "test@example.com"
        file_key = "users/test@example.com/generated/1234567890_abc123_test_file.csv"
        
        # Mock successful file access
        mock_file_manager.s3_client.get_file.return_value = {
            "key": file_key,
            "content_type": "text/csv",
            "size": 1024
        }
        
        result = await validate_user_file_access(user_email, file_key, mock_file_manager)
        assert result is True
        mock_file_manager.s3_client.get_file.assert_called_once_with(user_email, file_key)

    @pytest.mark.asyncio
    async def test_validate_user_file_access_failure(self, mock_file_manager):
        """Test validating user file access with invalid file."""
        user_email = "test@example.com"
        file_key = "users/other@example.com/generated/1234567890_abc123_test_file.csv"
        
        # Mock failed file access
        mock_file_manager.s3_client.get_file.return_value = None
        
        result = await validate_user_file_access(user_email, file_key, mock_file_manager)
        assert result is False
        mock_file_manager.s3_client.get_file.assert_called_once_with(user_email, file_key)

    @pytest.mark.asyncio
    async def test_ingest_v2_artifacts_with_s3_url(self, mock_file_manager, mock_tool_result):
        """Test ingesting v2 artifacts with S3 URL."""
        session_context = {"user_email": "test@example.com"}
        user_email = "test@example.com"
        
        # Mock successful file access validation
        mock_file_manager.s3_client.get_file.return_value = {
            "key": "users/test@example.com/generated/1234567890_abc123_test_file.csv",
            "content_type": "text/csv",
            "size": 1024
        }
        
        # Mock file upload for base64 content
        mock_file_manager.upload_files_from_base64.return_value = {
            "test_report.txt": {
                "key": "users/test@example.com/generated/0987654321_def456_test_report.txt",
                "content_type": "text/plain",
                "size": 12,
                "source": "tool"
            }
        }
        
        # Mock organize_files_metadata
        mock_file_manager.organize_files_metadata.return_value = {
            "files": [
                {
                    "filename": "test_file.csv",
                    "s3_key": "users/test@example.com/generated/1234567890_abc123_test_file.csv",
                    "size": 1024,
                    "type": "data",
                    "source": "mcp_s3_direct"
                },
                {
                    "filename": "test_report.txt",
                    "s3_key": "users/test@example.com/generated/0987654321_def456_test_report.txt",
                    "size": 12,
                    "type": "data",
                    "source": "tool"
                }
            ]
        }
        
        result = await ingest_v2_artifacts(
            session_context=session_context,
            tool_result=mock_tool_result,
            user_email=user_email,
            file_manager=mock_file_manager
        )
        
        # Verify that the S3 URL was processed without re-uploading
        assert "test_file.csv" in result["files"]
        assert result["files"]["test_file.csv"]["key"] == "users/test@example.com/generated/1234567890_abc123_test_file.csv"
        assert result["files"]["test_file.csv"]["source"] == "mcp_s3_direct"
        
        # Verify that the base64 content was uploaded
        assert "test_report.txt" in result["files"]
        assert result["files"]["test_report.txt"]["source"] == "tool"
        
        # Verify that S3 client get_file was called for URL validation
        mock_file_manager.s3_client.get_file.assert_called_once_with(
            user_email, 
            "users/test@example.com/generated/1234567890_abc123_test_file.csv"
        )
        
        # Verify that upload_files_from_base64 was called for base64 content
        mock_file_manager.upload_files_from_base64.assert_called_once()
        
        # Verify that organize_files_metadata was called
        mock_file_manager.organize_files_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_v2_artifacts_with_invalid_s3_url(self, mock_file_manager):
        """Test ingesting v2 artifacts with invalid S3 URL."""
        session_context = {"user_email": "test@example.com"}
        user_email = "test@example.com"
        
        # Create tool result with invalid S3 URL
        tool_result = Mock()
        tool_result.artifacts = [
            {
                "name": "invalid_file.csv",
                "url": "/api/files/download/users/other@example.com/generated/1234567890_abc123_test_file.csv",
                "mime": "text/csv",
                "size": 1024
            }
        ]
        
        # Mock failed file access validation
        mock_file_manager.s3_client.get_file.return_value = None
        
        result = await ingest_v2_artifacts(
            session_context=session_context,
            tool_result=tool_result,
            user_email=user_email,
            file_manager=mock_file_manager
        )
        
        # Verify that the invalid S3 URL was not added to session context
        assert "invalid_file.csv" not in result["files"]
        
        # Verify that S3 client get_file was called for URL validation
        mock_file_manager.s3_client.get_file.assert_called_once_with(
            user_email,
            "users/other@example.com/generated/1234567890_abc123_test_file.csv"
        )

    @pytest.mark.asyncio
    async def test_ingest_v2_artifacts_without_artifacts(self, mock_file_manager):
        """Test ingesting v2 artifacts when no artifacts are present."""
        session_context = {"user_email": "test@example.com"}
        user_email = "test@example.com"
        
        # Create tool result without artifacts
        tool_result = Mock()
        tool_result.artifacts = None
        
        result = await ingest_v2_artifacts(
            session_context=session_context,
            tool_result=tool_result,
            user_email=user_email,
            file_manager=mock_file_manager
        )
        
        # Verify that the session context is unchanged
        assert result == session_context


if __name__ == "__main__":
    pytest.main([__file__])
