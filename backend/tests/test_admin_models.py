"""Tests for admin models validation and serialization."""

import pytest
from pydantic import ValidationError

from managers.admin.admin_models import (
    AdminConfigUpdate,
    BannerMessageUpdate,
    LogEntry,
)


def test_admin_config_update_validation():
    """Test AdminConfigUpdate model validates required fields and types."""
    # Valid data
    valid_update = AdminConfigUpdate(content='{"test": "value"}', file_type="json")
    assert valid_update.content == '{"test": "value"}'
    assert valid_update.file_type == "json"

    # Missing required fields
    with pytest.raises(ValidationError):
        AdminConfigUpdate(content='{"test": "value"}')  # Missing file_type

    with pytest.raises(ValidationError):
        AdminConfigUpdate(file_type="json")  # Missing content


def test_banner_message_update_handles_empty_lists():
    """Test BannerMessageUpdate correctly handles empty and populated message lists."""
    # Empty messages
    empty_update = BannerMessageUpdate(messages=[])
    assert empty_update.messages == []

    # Multiple messages
    multi_update = BannerMessageUpdate(messages=["Alert 1", "Alert 2", "Status OK"])
    assert len(multi_update.messages) == 3
    assert multi_update.messages[0] == "Alert 1"

    # Single message
    single_update = BannerMessageUpdate(messages=["Single alert"])
    assert len(single_update.messages) == 1


def test_log_entry_model_serialization():
    """Test LogEntry model properly serializes structured and minimal log data."""
    # Full structured log entry
    full_entry = LogEntry(
        timestamp="2024-01-01 12:00:00",
        level="ERROR",
        module="test_module",
        logger="test.logger",
        function="test_function",
        message="Test error message",
        trace_id="abc123",
        span_id="def456",
        line="100",
        thread_name="MainThread",
        extras={"extra_field": "extra_value"},
    )

    # Should serialize all fields
    serialized = full_entry.model_dump()
    assert serialized["level"] == "ERROR"
    assert serialized["message"] == "Test error message"
    assert serialized["extras"]["extra_field"] == "extra_value"

    # Minimal log entry (common for fallback parsing)
    minimal_entry = LogEntry(
        timestamp="",
        level="INFO",
        module="unknown",
        logger="unknown",
        function="",
        message="Raw log line",
        trace_id="",
        span_id="",
        line="",
        thread_name="",
        extras={},
    )

    minimal_serialized = minimal_entry.model_dump()
    assert minimal_serialized["level"] == "INFO"
    assert minimal_serialized["message"] == "Raw log line"
    assert minimal_serialized["extras"] == {}
