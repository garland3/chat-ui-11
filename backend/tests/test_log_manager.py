"""Tests for log manager file operations and parsing."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from managers.admin.log_manager import LogManager
from managers.admin.admin_models import LogEntry


def test_parse_log_entry_handles_json_logs():
    """Test _parse_log_entry correctly parses structured JSON log entries."""
    json_log = json.dumps({
        "timestamp": "2024-01-01 12:00:00",
        "level": "ERROR", 
        "module": "test_module",
        "logger": "test.logger",
        "message": "Test error occurred",
        "trace_id": "abc123",
        "extra_field": "extra_value"
    })
    
    entry = LogManager._parse_log_entry(json_log)
    
    assert isinstance(entry, LogEntry)
    assert entry.level == "ERROR"
    assert entry.module == "test_module"
    assert entry.message == "Test error occurred"
    assert entry.trace_id == "abc123"
    assert entry.extras["extra_field"] == "extra_value"


def test_parse_log_entry_handles_plain_text_logs():
    """Test _parse_log_entry parses plain text logs with regex fallback."""
    # Standard formatted log line
    text_log = "2024-01-01 12:00:00 - INFO - auth_module - User login successful"
    
    entry = LogManager._parse_log_entry(text_log)
    
    assert isinstance(entry, LogEntry)
    assert entry.timestamp == "2024-01-01 12:00:00"
    assert entry.level == "INFO"
    assert entry.module == "auth_module"
    assert entry.message == "User login successful"
    assert entry.trace_id == ""  # Empty for plain text logs
    
    # Unstructured log line (fallback case)
    unstructured_log = "Some random log message without format"
    fallback_entry = LogManager._parse_log_entry(unstructured_log)
    
    assert fallback_entry.level == "INFO"  # Default level
    assert fallback_entry.module == "unknown"  # Default module
    assert fallback_entry.message == "Some random log message without format"


@patch.object(LogManager, '_locate_log_file')
def test_clear_logs_handles_multiple_files(mock_locate):
    """Test clear_logs processes multiple log file candidates and reports results."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create test log files
        log1 = tmp_path / "app.jsonl"
        log2 = tmp_path / "app.log"
        log1.write_text("existing log data\n")
        log2.write_text("more log data\n")
        
        # Mock _log_base_dir to return our temp directory
        with patch.object(LogManager, '_log_base_dir', return_value=tmp_path):
            cleared_files, message = LogManager.clear_logs()
        
        # Should clear both files
        assert len(cleared_files) == 2
        assert any("app.jsonl" in f for f in cleared_files)
        assert any("app.log" in f for f in cleared_files)
        assert message == "Log files cleared successfully"
        
        # Files should contain "NEW LOG\n"
        assert log1.read_text() == "NEW LOG\n"
        assert log2.read_text() == "NEW LOG\n"


@patch.object(LogManager, '_locate_log_file')
def test_get_log_file_for_download_handles_missing_file(mock_locate):
    """Test get_log_file_for_download raises appropriate errors for missing files."""
    mock_locate.side_effect = HTTPException(status_code=404, detail="Log file not found")
    
    with pytest.raises(HTTPException) as exc_info:
        LogManager.get_log_file_for_download()
    
    assert exc_info.value.status_code == 404
    assert "not found" in str(exc_info.value.detail)