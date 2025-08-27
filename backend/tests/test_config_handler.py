"""Tests for config handler file operations and validation."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from managers.admin.config_handler import ConfigHandler


def test_write_file_content_validates_json():
    """Test write_file_content properly validates JSON content before writing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "test.json"
        
        # Valid JSON should succeed
        valid_json = '{"key": "value", "number": 42}'
        ConfigHandler.write_file_content(test_file, valid_json, "json")
        assert test_file.exists()
        assert json.loads(test_file.read_text()) == {"key": "value", "number": 42}
        
        # Invalid JSON should raise HTTPException
        invalid_json = '{"key": "value", "missing_quote: 42}'
        with pytest.raises(HTTPException) as exc_info:
            ConfigHandler.write_file_content(test_file, invalid_json, "json")
        assert exc_info.value.status_code == 400
        assert "Invalid JSON" in str(exc_info.value.detail)


def test_get_file_content_handles_missing_files():
    """Test get_file_content raises appropriate errors for missing files."""
    non_existent_file = Path("/tmp/does_not_exist.txt")
    
    with pytest.raises(HTTPException) as exc_info:
        ConfigHandler.get_file_content(non_existent_file)
    
    assert exc_info.value.status_code == 404
    assert "not found" in str(exc_info.value.detail)


@patch("managers.admin.config_handler.config_manager")
def test_get_all_configs_view_masks_sensitive_data(mock_config_manager):
    """Test get_all_configs_view properly masks sensitive configuration data."""
    # Mock app settings with sensitive data
    mock_app_settings = Mock()
    mock_app_settings.model_dump.return_value = {
        "api_key": "secret-key-123",
        "database_password": "super-secret",
        "debug_mode": True,
        "app_name": "test-app"
    }
    
    # Mock LLM config with API keys
    mock_llm_model = Mock()
    mock_llm_model.model_dump.return_value = {
        "name": "gpt-4",
        "api_key": "sk-secret123",
        "temperature": 0.7
    }
    mock_llm_config = Mock()
    mock_llm_config.models = [mock_llm_model]
    
    # Mock MCP config with servers attribute that has len()
    mock_mcp_config = Mock()
    mock_mcp_config.model_dump.return_value = {"servers": []}
    mock_mcp_config.servers = []  # Add servers attribute for len() check
    
    mock_config_manager.app_settings = mock_app_settings
    mock_config_manager.llm_config = mock_llm_config
    mock_config_manager.get_mcp_config.return_value = mock_mcp_config
    
    result = ConfigHandler.get_all_configs_view()
    
    # Sensitive fields should be masked
    assert result["app_settings"]["api_key"] == "***MASKED***"
    assert result["app_settings"]["database_password"] == "***MASKED***"
    # Non-sensitive fields should remain
    assert result["app_settings"]["debug_mode"] is True
    assert result["app_settings"]["app_name"] == "test-app"
    
    # LLM config API keys should be masked
    assert result["llm_config"]["models"][0]["api_key"] == "***MASKED***"
    assert result["llm_config"]["models"][0]["name"] == "gpt-4"