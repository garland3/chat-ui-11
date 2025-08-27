"""Tests for log manager file operations and parsing."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse

from managers.admin.log_manager import LogManager
from managers.admin.admin_models import LogEntry


def test_parse_json_log_handles_valid_json():
    """Test _parse_json_log correctly parses structured JSON log entries."""
    json_log = json.dumps({
        "timestamp": "2024-01-01 12:00:00",
        "level": "ERROR",
        "module": "test_module",
        "message": "Test error occurred",
        "trace_id": "abc123",
        "extra_field": "extra_value"
    })

    entry = LogManager._parse_json_log(json_log)

    assert isinstance(entry, LogEntry)
    assert entry.level == "ERROR"
    assert entry.module == "test_module"
    assert entry.message == "Test error occurred"
    assert entry.trace_id == "abc123"
    assert entry.extras["extra_field"] == "extra_value"

def test_parse_json_log_handles_malformed_json():
    """Test _parse_json_log handles malformed JSON lines gracefully."""
    malformed_log = "this is not json"
    entry = LogManager._parse_json_log(malformed_log)

    assert isinstance(entry, LogEntry)
    assert entry.level == "ERROR"
    assert entry.module == "log_parser"
    assert "Failed to parse log line" in entry.message

@patch("managers.admin.log_manager.LogManager._get_log_file")
def test_clear_logs_success(mock_get_log_file):
    """Test clear_logs successfully clears the log file."""
    # Create a temporary file to act as our log file
    temp_log_file = Path("temp_log.jsonl")
    temp_log_file.write_text("existing log data")
    
    # Make the mock return the path to our temporary file
    mock_get_log_file.return_value = temp_log_file

    cleared_files, message = LogManager.clear_logs()

    assert str(temp_log_file) in cleared_files
    assert message == "Log file cleared successfully"
    assert temp_log_file.read_text() == "NEW LOG\n"
    
    # Clean up the temporary file
    temp_log_file.unlink()

@patch("managers.admin.log_manager.LogManager._get_log_file")
def test_get_log_file_for_download_not_found(mock_get_log_file):
    """Test get_log_file_for_download raises HTTPException when file not found."""
    # Configure the mock to simulate the file not being found
    mock_get_log_file.side_effect = HTTPException(status_code=404, detail="Log file not found")

    with pytest.raises(HTTPException) as exc_info:
        LogManager.get_log_file_for_download()

    assert exc_info.value.status_code == 404
    assert "Log file not found" in exc_info.value.detail

@patch("managers.admin.log_manager.LogManager._get_log_file")
def test_get_log_file_for_download_success(mock_get_log_file):
    """Test get_log_file_for_download returns a FileResponse on success."""
    # Create a temporary file
    temp_log_file = Path("temp_log_download.jsonl")
    temp_log_file.write_text("some log data")

    mock_get_log_file.return_value = temp_log_file

    response = LogManager.get_log_file_for_download()

    assert isinstance(response, FileResponse)
    assert response.path == str(temp_log_file)
    
    # Clean up
    temp_log_file.unlink()
