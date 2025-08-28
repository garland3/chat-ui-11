"""
Tests for utility functions.
"""

import shutil
import tempfile
from pathlib import Path

from mcp_enhanced.utils import (
    cleanup_user_files,
    ensure_user_directory,
    get_file_info,
    list_user_files,
    secure_output_path,
)


class TestUtils:
    def test_secure_output_path(self):
        """Test secure output path generation"""
        path = secure_output_path("testuser", "output.txt")

        assert "/tmp/testuser/output.txt" in path
        assert Path(path).parent.exists()  # Directory should be created

    def test_secure_output_path_with_unsafe_names(self):
        """Test that unsafe filenames are sanitized"""
        path = secure_output_path("../baduser", "../../etc/passwd")

        # Should be sanitized - the '../baduser' becomes '__baduser'
        assert "../baduser" not in path  # No directory traversal
        assert "passwd" in path  # filename preserved but path sanitized
        assert "/tmp/" in path

    def test_list_user_files(self):
        """Test listing files in user directory"""
        username = "testuser"

        # Create test files
        user_dir = Path(f"/tmp/{username}")
        user_dir.mkdir(parents=True, exist_ok=True)

        test_files = ["file1.txt", "file2.csv", "other.json"]
        for filename in test_files:
            (user_dir / filename).write_text("test content")

        try:
            # List all files
            all_files = list_user_files(username)
            assert len(all_files) == 3

            # List with pattern
            csv_files = list_user_files(username, "*.csv")
            assert len(csv_files) == 1
            assert "file2.csv" in csv_files[0]

        finally:
            shutil.rmtree(user_dir)

    def test_list_user_files_nonexistent(self):
        """Test listing files for non-existent user"""
        files = list_user_files("nonexistentuser")
        assert files == []

    def test_get_file_info(self):
        """Test getting file information"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_path = f.name

        try:
            info = get_file_info(temp_path)

            assert "name" in info
            assert "size_bytes" in info
            assert "modified_time" in info
            assert info["is_file"] is True
            assert info["suffix"] == ".txt"

        finally:
            Path(temp_path).unlink()

    def test_get_file_info_nonexistent(self):
        """Test getting info for non-existent file"""
        info = get_file_info("/nonexistent/file.txt")
        assert "error" in info

    def test_ensure_user_directory(self):
        """Test ensuring user directory exists"""
        username = "newuser"
        user_dir = ensure_user_directory(username)

        assert Path(user_dir).exists()
        assert Path(user_dir).is_dir()
        assert f"/tmp/{username}" in user_dir

        # Clean up
        shutil.rmtree(user_dir)

    def test_cleanup_user_files(self):
        """Test cleaning up user files"""
        username = "cleanupuser"
        user_dir = Path(f"/tmp/{username}")
        user_dir.mkdir(parents=True, exist_ok=True)

        # Create test files
        test_files = ["file1.txt", "file2.txt"]
        for filename in test_files:
            (user_dir / filename).write_text("test content")

        # Verify files exist
        assert len(list(user_dir.glob("*"))) == 2

        # Clean up all files
        cleanup_user_files(username, keep_recent_hours=0)

        # Directory should be empty or removed
        if user_dir.exists():
            assert len(list(user_dir.glob("*"))) == 0
