"""Test banner functionality for both config routes and admin routes."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from managers.admin.config_handler import ConfigHandler
from managers.admin.admin_models import BannerMessageUpdate


class TestBannerFunctionality:
    """Test banner message reading and writing functionality."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for config testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @patch('managers.admin.config_handler.ConfigHandler._config_base_dir')
    def test_banner_messages_write_and_read(self, mock_config_dir, temp_config_dir):
        """Test that banner messages can be written and read correctly."""
        mock_config_dir.return_value = temp_config_dir
        
        # Test writing messages
        test_messages = ["System maintenance scheduled", "New features available", ""]
        ConfigHandler.update_banner_messages(test_messages)
        
        # Verify file was created and has correct content
        messages_file = temp_config_dir / "messages.txt"
        assert messages_file.exists()
        
        # Test reading messages
        messages, file_path, last_modified = ConfigHandler.get_banner_messages()
        
        # Should filter out empty lines
        expected_messages = ["System maintenance scheduled", "New features available"]
        assert messages == expected_messages
        assert file_path == messages_file
        assert last_modified > 0

    @patch('managers.admin.config_handler.ConfigHandler._config_base_dir')
    def test_banner_messages_empty_list(self, mock_config_dir, temp_config_dir):
        """Test that empty message list creates empty file."""
        mock_config_dir.return_value = temp_config_dir
        
        # Test writing empty messages
        ConfigHandler.update_banner_messages([])
        
        # Verify file was created but is empty
        messages_file = temp_config_dir / "messages.txt"
        assert messages_file.exists()
        assert messages_file.read_text() == ""
        
        # Test reading empty messages
        messages, _, _ = ConfigHandler.get_banner_messages()
        assert messages == []

    @patch('managers.admin.config_handler.ConfigHandler._config_base_dir')
    def test_banner_messages_auto_create(self, mock_config_dir, temp_config_dir):
        """Test that messages file is created with default content if it doesn't exist."""
        mock_config_dir.return_value = temp_config_dir
        
        # Ensure file doesn't exist
        messages_file = temp_config_dir / "messages.txt"
        assert not messages_file.exists()
        
        # Reading should create default file
        messages, file_path, _ = ConfigHandler.get_banner_messages()
        
        assert messages_file.exists()
        assert messages == ["System status: All services operational"]
        assert file_path == messages_file

    def test_banner_message_update_model(self):
        """Test BannerMessageUpdate model validation."""
        # Valid update
        update = BannerMessageUpdate(messages=["Test message", "Another message"])
        assert len(update.messages) == 2
        assert update.messages[0] == "Test message"
        
        # Empty update
        empty_update = BannerMessageUpdate(messages=[])
        assert empty_update.messages == []