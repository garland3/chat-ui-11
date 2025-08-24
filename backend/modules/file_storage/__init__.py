"""File storage module for the chat backend.

This module provides:
- S3 storage client for file operations
- File management utilities
- Content type detection and categorization
- CLI tools for file operations

Note: Do not instantiate clients at import time to avoid side effects during
test collection (e.g., requiring boto3). Import classes only; the app factory
creates instances when needed.
"""

from .s3_client import S3StorageClient
from .manager import FileManager

__all__ = [
    "S3StorageClient",
    "FileManager",
]