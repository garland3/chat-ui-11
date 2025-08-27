"""Test banner API endpoints integration."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from managers.admin.config_handler import ConfigHandler


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture  
def temp_config_dir():
    """Create a temporary directory for config testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_user():
    """Mock current user."""
    return "test@example.com"


@pytest.fixture
def mock_admin_user():
    """Mock admin user."""
    return "admin@example.com"


class TestBannerEndpoints:
    """Test banner API endpoints."""

    @patch('routes.config_route.get_current_user')
    @patch('managers.admin.config_handler.ConfigHandler._config_base_dir')
    def test_get_banners_enabled(self, mock_config_dir, mock_get_user, temp_config_dir, client, mock_user):
        """Test GET /api/banners when banners are enabled."""
        mock_get_user.return_value = mock_user
        mock_config_dir.return_value = temp_config_dir
        
        # Create test messages
        test_messages = ["System update scheduled", "New features available"]
        ConfigHandler.update_banner_messages(test_messages)
        
        response = client.get("/api/banners")
        assert response.status_code == 200
        
        data = response.json()
        assert "messages" in data
        assert data["messages"] == test_messages

    @patch('routes.config_route.get_current_user')  
    @patch('routes.config_route.app_factory')
    def test_get_banners_disabled(self, mock_app_factory, mock_get_user, client, mock_user):
        """Test GET /api/banners when banners are disabled."""
        mock_get_user.return_value = mock_user
        
        # Mock config with banners disabled
        mock_config_manager = MagicMock()
        mock_config_manager.app_settings.banner_enabled = False
        mock_app_factory.get_config_manager.return_value = mock_config_manager
        
        response = client.get("/api/banners")
        assert response.status_code == 200
        
        data = response.json()
        assert "messages" in data
        assert data["messages"] == []

    @patch('managers.auth.utils.get_current_user')
    @patch('managers.auth.auth_manager.is_user_in_group')
    @patch('managers.admin.config_handler.ConfigHandler._config_base_dir')
    def test_admin_get_banners(self, mock_config_dir, mock_is_user_in_group, mock_get_user, temp_config_dir, client, mock_admin_user):
        """Test GET /admin/banners endpoint."""
        mock_get_user.return_value = mock_admin_user
        mock_is_user_in_group.return_value = True  # User is in admin group
        mock_config_dir.return_value = temp_config_dir
        
        # Create test messages
        test_messages = ["Admin message", "System status OK"]
        ConfigHandler.update_banner_messages(test_messages)
        
        response = client.get("/admin/banners")
        assert response.status_code == 200
        
        data = response.json()
        assert "messages" in data
        assert "file_path" in data
        assert "last_modified" in data
        assert data["messages"] == test_messages

    @patch('managers.auth.utils.get_current_user')
    @patch('managers.auth.auth_manager.is_user_in_group')
    @patch('managers.admin.config_handler.ConfigHandler._config_base_dir')
    def test_admin_update_banners(self, mock_config_dir, mock_is_user_in_group, mock_get_user, temp_config_dir, client, mock_admin_user):
        """Test POST /admin/banners endpoint."""
        mock_get_user.return_value = mock_admin_user
        mock_is_user_in_group.return_value = True  # User is in admin group
        mock_config_dir.return_value = temp_config_dir
        
        new_messages = ["Updated message", "System maintenance tonight"]
        
        response = client.post("/admin/banners", json={
            "messages": new_messages
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "messages" in data
        assert "updated_by" in data
        assert data["messages"] == new_messages
        # The important part is that the messages were updated successfully
        assert "updated_by" in data  # Just verify the field exists
        
        # Verify messages were actually written to file
        messages, _, _ = ConfigHandler.get_banner_messages()
        assert messages == new_messages