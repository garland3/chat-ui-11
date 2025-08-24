"""
Comprehensive test suite for S3 file transfer infrastructure.

Tests the most critical functions for S3-based file handling including:
- S3 client operations (upload, download, delete, list)
- Capability token generation and validation
- File injection and URL transformation
- Route handlers for file operations
- Error handling and edge cases
"""

import base64
import time
import os
import sys
from typing import Dict, Any
import pytest
from fastapi.testclient import TestClient

# Setup path and stubs
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Stub LiteLLM to avoid external dependencies
import types
fake_litellm = types.ModuleType("modules.llm.litellm_caller")
class _FakeLLM:
    def __init__(self, *args, **kwargs):
        pass
    async def call_plain(self, model, messages):
        return "test response"
fake_litellm.LiteLLMCaller = _FakeLLM
sys.modules["modules.llm.litellm_caller"] = fake_litellm

from main import app
from core.capabilities import (
    generate_file_token, verify_file_token, create_download_url,
    _b64url_encode, _b64url_decode
)
from application.chat.utilities.tool_utils import (
    inject_context_into_args, tool_accepts_username
)


class MockS3Client:
    """Enhanced mock S3 client for testing."""
    
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self.base_url = "http://mock-s3:9000"
        self.use_mock = True
        self._next_key = 1
    
    async def upload_file(self, user_email: str, filename: str, content_base64: str, 
                         content_type: str = "application/octet-stream", tags=None, source_type: str = "user"):
        key = f"test_key_{self._next_key}"
        self._next_key += 1
        
        file_data = {
            "key": key,
            "filename": filename,
            "content_base64": content_base64,
            "content_type": content_type,
            "size": len(base64.b64decode(content_base64)),
            "last_modified": "2024-01-01T00:00:00Z",
            "etag": f"etag-{key}",
            "tags": tags or {"source": source_type},
            "user_email": user_email
        }
        self._store[key] = file_data
        return file_data
    
    async def get_file(self, user_email: str, file_key: str):
        file_data = self._store.get(file_key)
        if file_data and file_data["user_email"] == user_email:
            return file_data
        return None
    
    async def list_files(self, user_email: str, file_type: str = None, limit: int = 100):
        files = [f for f in self._store.values() if f["user_email"] == user_email]
        if file_type:
            files = [f for f in files if f["content_type"].startswith(file_type)]
        return files[:limit]
    
    async def delete_file(self, user_email: str, file_key: str) -> bool:
        if file_key in self._store and self._store[file_key]["user_email"] == user_email:
            del self._store[file_key]
            return True
        return False
    
    async def get_user_stats(self, user_email: str):
        user_files = [f for f in self._store.values() if f["user_email"] == user_email]
        return {
            "total_files": len(user_files),
            "total_size_bytes": sum(f["size"] for f in user_files),
            "file_types": list(set(f["content_type"] for f in user_files))
        }


@pytest.fixture
def mock_s3():
    return MockS3Client()


@pytest.fixture
def client(monkeypatch, mock_s3):
    """Test client with mocked S3 storage."""
    from infrastructure import app_factory
    monkeypatch.setattr(app_factory, "get_file_storage", lambda: mock_s3)
    return TestClient(app)


# Test 1: Capability token generation and parsing
def test_capability_token_generation_and_parsing():
    """Test capability token creation with proper claims."""
    user_email = "alice@example.com"
    file_key = "test-file-123"
    ttl_seconds = 3600
    
    token = generate_file_token(user_email, file_key, ttl_seconds)
    
    # Verify token structure
    assert "." in token
    body, signature = token.split(".", 1)
    assert len(body) > 0
    assert len(signature) > 0
    
    # Verify claims
    claims = verify_file_token(token)
    assert claims is not None
    assert claims["u"] == user_email
    assert claims["k"] == file_key
    assert claims["e"] > int(time.time())


# Test 2: Capability token expiration handling
def test_capability_token_expiration():
    """Test that expired tokens are properly rejected."""
    user_email = "bob@example.com"
    file_key = "expired-file"
    
    # Create already expired token
    expired_token = generate_file_token(user_email, file_key, ttl_seconds=-10)
    claims = verify_file_token(expired_token)
    
    assert claims is None


# Test 3: Capability token tampering detection
def test_capability_token_tampering_detection():
    """Test that tampered tokens are rejected."""
    token = generate_file_token("charlie@example.com", "secure-file", 3600)
    body, signature = token.split(".", 1)
    
    # Tamper with body
    tampered_body = body[:-1] + ("X" if body[-1] != "X" else "Y")
    tampered_token = f"{tampered_body}.{signature}"
    
    assert verify_file_token(tampered_token) is None
    
    # Tamper with signature
    tampered_signature = signature[:-1] + ("Z" if signature[-1] != "Z" else "A")
    tampered_token_2 = f"{body}.{tampered_signature}"
    
    assert verify_file_token(tampered_token_2) is None


# Test 4: Base64 URL encoding/decoding
def test_base64_url_encoding_decoding():
    """Test base64 URL-safe encoding and decoding utilities."""
    test_data = b"Hello, World! This is a test with special chars: +/="
    
    encoded = _b64url_encode(test_data)
    decoded = _b64url_decode(encoded)
    
    assert decoded == test_data
    assert "+" not in encoded  # URL-safe encoding
    assert "/" not in encoded
    assert "=" not in encoded  # Padding removed


# Test 5: Download URL creation with and without tokens
def test_download_url_creation():
    """Test download URL generation with capability tokens."""
    file_key = "report.pdf"
    user_email = "david@example.com"
    
    # With user email (should include token)
    url_with_token = create_download_url(file_key, user_email)
    assert url_with_token.startswith(f"/api/files/download/{file_key}")
    assert "?token=" in url_with_token
    
    # Without user email (no token)
    url_without_token = create_download_url(file_key, None)
    assert url_without_token == f"/api/files/download/{file_key}"
    assert "?token=" not in url_without_token


# Test 6: S3 client file upload
@pytest.mark.asyncio
async def test_s3_client_file_upload(mock_s3):
    """Test S3 client file upload functionality."""
    user_email = "eve@example.com"
    filename = "test-document.pdf"
    content = b"PDF content here"
    content_b64 = base64.b64encode(content).decode("utf-8")
    
    result = await mock_s3.upload_file(
        user_email=user_email,
        filename=filename,
        content_base64=content_b64,
        content_type="application/pdf",
        tags={"source": "test"}
    )
    
    assert result["filename"] == filename
    assert result["content_type"] == "application/pdf"
    assert result["user_email"] == user_email
    assert result["size"] == len(content)
    assert "key" in result


# Test 7: S3 client file retrieval
@pytest.mark.asyncio
async def test_s3_client_file_retrieval(mock_s3):
    """Test S3 client file retrieval with access control."""
    user_email = "frank@example.com"
    other_user = "mallory@example.com"
    filename = "private-doc.txt"
    content_b64 = base64.b64encode(b"Private content").decode("utf-8")
    
    # Upload file
    upload_result = await mock_s3.upload_file(user_email, filename, content_b64)
    file_key = upload_result["key"]
    
    # Retrieve as owner
    retrieved = await mock_s3.get_file(user_email, file_key)
    assert retrieved is not None
    assert retrieved["filename"] == filename
    assert retrieved["content_base64"] == content_b64
    
    # Try to retrieve as different user (should fail)
    unauthorized = await mock_s3.get_file(other_user, file_key)
    assert unauthorized is None


# Test 8: S3 client file deletion
@pytest.mark.asyncio
async def test_s3_client_file_deletion(mock_s3):
    """Test S3 client file deletion with proper authorization."""
    user_email = "grace@example.com"
    other_user = "hacker@example.com"
    content_b64 = base64.b64encode(b"Delete me").decode("utf-8")
    
    upload_result = await mock_s3.upload_file(user_email, "delete-test.txt", content_b64)
    file_key = upload_result["key"]
    
    # Try to delete as wrong user (should fail)
    delete_failed = await mock_s3.delete_file(other_user, file_key)
    assert delete_failed is False
    
    # Delete as owner (should succeed)
    delete_success = await mock_s3.delete_file(user_email, file_key)
    assert delete_success is True
    
    # Verify file is gone
    retrieved = await mock_s3.get_file(user_email, file_key)
    assert retrieved is None


# Test 9: S3 client file listing
@pytest.mark.asyncio
async def test_s3_client_file_listing(mock_s3):
    """Test S3 client file listing with user isolation."""
    user1 = "henry@example.com"
    user2 = "iris@example.com"
    
    # Upload files for user1
    await mock_s3.upload_file(user1, "file1.txt", base64.b64encode(b"content1").decode())
    await mock_s3.upload_file(user1, "file2.pdf", base64.b64encode(b"content2").decode())
    
    # Upload file for user2
    await mock_s3.upload_file(user2, "file3.doc", base64.b64encode(b"content3").decode())
    
    # List files for user1
    user1_files = await mock_s3.list_files(user1, limit=10)
    assert len(user1_files) == 2
    filenames = [f["filename"] for f in user1_files]
    assert "file1.txt" in filenames
    assert "file2.pdf" in filenames
    assert "file3.doc" not in filenames
    
    # List files for user2
    user2_files = await mock_s3.list_files(user2, limit=10)
    assert len(user2_files) == 1
    assert user2_files[0]["filename"] == "file3.doc"


# Test 10: S3 client user statistics
@pytest.mark.asyncio
async def test_s3_client_user_statistics(mock_s3):
    """Test S3 client user statistics calculation."""
    user_email = "jack@example.com"
    
    # Upload different types of files
    await mock_s3.upload_file(user_email, "doc1.txt", base64.b64encode(b"text").decode(), "text/plain")
    await mock_s3.upload_file(user_email, "doc2.pdf", base64.b64encode(b"pdf content").decode(), "application/pdf")
    await mock_s3.upload_file(user_email, "img1.png", base64.b64encode(b"image data").decode(), "image/png")
    
    stats = await mock_s3.get_user_stats(user_email)
    
    assert stats["total_files"] == 3
    assert stats["total_size_bytes"] == 4 + 11 + 10  # lengths of content
    assert "text/plain" in stats["file_types"]
    assert "application/pdf" in stats["file_types"]
    assert "image/png" in stats["file_types"]


# Test 11: File upload via API route
def test_file_upload_api_route(client):
    """Test file upload through API endpoint."""
    content = base64.b64encode(b"API upload test content").decode()
    
    response = client.post("/api/files", json={
        "filename": "api-test.txt",
        "content_base64": content,
        "content_type": "text/plain",
        "tags": {"source": "api_test"}
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "api-test.txt"
    assert data["content_type"] == "text/plain"
    assert data["size"] == len(b"API upload test content")
    assert "key" in data


# Test 12: File download via API route with token
def test_file_download_api_route_with_token(client, mock_s3):
    """Test file download through API endpoint using capability token."""
    user_email = "kevin@example.com"
    content = b"Download test content"
    content_b64 = base64.b64encode(content).decode()
    
    # Upload file directly to mock S3
    mock_s3._store["direct_key"] = {
        "key": "direct_key",
        "filename": "download-test.txt",
        "content_base64": content_b64,
        "content_type": "text/plain",
        "size": len(content),
        "user_email": user_email,
        "last_modified": "2024-01-01T00:00:00Z",
        "etag": "test-etag",
        "tags": {"source": "test"}
    }
    
    # Generate capability token
    token = generate_file_token(user_email, "direct_key", 3600)
    
    # Download with token
    response = client.get(f"/api/files/download/direct_key", params={"token": token})
    
    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-disposition"].startswith("inline")


# Test 13: Tool argument injection for single filename
def test_tool_argument_injection_single_file():
    """Test filename injection transforms single file to download URL."""
    session_context = {
        "user_email": "laura@example.com",
        "files": {
            "data.csv": {"key": "csv_key_123", "content_type": "text/csv"}
        }
    }
    
    args = {"filename": "data.csv", "other_param": "value"}
    injected = inject_context_into_args(args, session_context)
    
    assert injected["username"] == "laura@example.com"
    assert injected["original_filename"] == "data.csv"
    assert injected["filename"].startswith("/api/files/download/csv_key_123")
    assert "?token=" in injected["filename"]
    assert injected["file_url"] == injected["filename"]
    assert injected["other_param"] == "value"  # Other params preserved


# Test 14: Tool argument injection for multiple filenames
def test_tool_argument_injection_multiple_files():
    """Test filename injection transforms multiple files to download URLs."""
    session_context = {
        "user_email": "mike@example.com", 
        "files": {
            "file1.txt": {"key": "key1", "content_type": "text/plain"},
            "file2.pdf": {"key": "key2", "content_type": "application/pdf"},
            "missing.doc": None  # Not in storage
        }
    }
    
    args = {"file_names": ["file1.txt", "file2.pdf", "nonexistent.doc"]}
    injected = inject_context_into_args(args, session_context)
    
    assert injected["username"] == "mike@example.com"
    assert injected["original_file_names"] == ["file1.txt", "file2.pdf", "nonexistent.doc"]
    
    # Check URLs
    assert len(injected["file_names"]) == 3
    assert injected["file_names"][0].startswith("/api/files/download/key1")
    assert injected["file_names"][1].startswith("/api/files/download/key2")
    assert injected["file_names"][2] == "nonexistent.doc"  # Unmapped file kept as-is
    
    assert injected["file_urls"] == injected["file_names"]


# Test 15: Tool schema validation for username injection
def test_tool_username_injection_schema_validation():
    """Test username injection only occurs for tools that define username parameter."""
    # Mock tool manager
    class MockToolManager:
        def get_tools_schema(self, tool_names):
            if tool_names == ["tool_with_username"]:
                return [{
                    "function": {
                        "name": "tool_with_username",
                        "parameters": {
                            "properties": {
                                "filename": {"type": "string"},
                                "username": {"type": "string"}
                            }
                        }
                    }
                }]
            elif tool_names == ["tool_without_username"]:
                return [{
                    "function": {
                        "name": "tool_without_username", 
                        "parameters": {
                            "properties": {
                                "filename": {"type": "string"}
                            }
                        }
                    }
                }]
            return []
    
    mock_manager = MockToolManager()
    session_context = {"user_email": "nancy@example.com", "files": {}}
    
    # Tool WITH username parameter - should inject
    args1 = {"filename": "test.txt"}
    injected1 = inject_context_into_args(args1, session_context, "tool_with_username", mock_manager)
    assert injected1["username"] == "nancy@example.com"
    
    # Tool WITHOUT username parameter - should NOT inject
    args2 = {"filename": "test.txt"}  
    injected2 = inject_context_into_args(args2, session_context, "tool_without_username", mock_manager)
    assert "username" not in injected2
    
    # Verify helper function
    assert tool_accepts_username("tool_with_username", mock_manager) is True
    assert tool_accepts_username("tool_without_username", mock_manager) is False