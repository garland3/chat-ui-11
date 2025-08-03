"""Tests for admin routes functionality."""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from fastapi.testclient import TestClient
from fastapi import FastAPI

from admin_routes import admin_router, setup_configfilesadmin


def create_test_app():
    """Create a test app with mocked dependencies."""
    app = FastAPI()
    app.include_router(admin_router)
    return app


class TestAdminRoutes:
    """Test admin routes functionality."""
    
    def test_admin_dashboard_requires_auth(self):
        """Test that admin dashboard requires authentication."""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/admin/")
        assert response.status_code == 403  # Admin auth required
    
    def test_admin_dashboard_success(self):
        """Test successful admin dashboard access."""
        app = create_test_app()
        
        def mock_require_admin():
            return "admin@example.com"
        
        from admin_routes import require_admin
        app.dependency_overrides[require_admin] = mock_require_admin
        client = TestClient(app)
        
        response = client.get("/admin/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "available_endpoints" in data
    
    def test_get_banner_config(self):
        """Test getting banner configuration."""
        app = create_test_app()
        
        def mock_require_admin():
            return "admin@example.com"
        
        # Override the dependency for require_admin
        from admin_routes import require_admin
        app.dependency_overrides[require_admin] = mock_require_admin
        client = TestClient(app)
        
        with patch('admin_routes.get_file_content', return_value="Message 1\nMessage 2\n"):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.stat') as mock_stat:
                    mock_stat.return_value.st_mtime = 1640995200
                    
                    response = client.get("/admin/banners")
                    assert response.status_code == 200
                    data = response.json()
                    assert "messages" in data
                    assert data["messages"] == ["Message 1", "Message 2"]
    
    def test_update_banner_config(self):
        """Test updating banner configuration."""
        app = create_test_app()
        
        def mock_require_admin():
            return "admin@example.com"
        
        from admin_routes import require_admin
        app.dependency_overrides[require_admin] = mock_require_admin
        client = TestClient(app)
        
        with patch('admin_routes.write_file_content'):
            update_data = {"messages": ["New message 1", "New message 2"]}
            response = client.post("/admin/banners", json=update_data)
            assert response.status_code == 200
            
            data = response.json()
            assert "message" in data
            assert data["updated_by"] == "admin@example.com"
    
    def test_get_mcp_config(self):
        """Test getting MCP configuration.""" 
        app = create_test_app()
        
        def mock_require_admin():
            return "admin@example.com"
        
        from admin_routes import require_admin
        app.dependency_overrides[require_admin] = mock_require_admin
        client = TestClient(app)
        
        test_config = {"test_server": {"command": ["python", "test.py"]}}
        with patch('admin_routes.get_file_content', return_value=json.dumps(test_config, indent=2)):
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value.st_mtime = 1640995200
                
                response = client.get("/admin/mcp-config")
                assert response.status_code == 200
                data = response.json()
                assert "content" in data
                assert "parsed" in data
                assert data["parsed"] == test_config
    
    def test_update_mcp_config(self):
        """Test updating MCP configuration."""
        app = create_test_app()
        
        def mock_require_admin():
            return "admin@example.com"
        
        from admin_routes import require_admin
        app.dependency_overrides[require_admin] = mock_require_admin
        client = TestClient(app)
        
        test_config = {"new_server": {"command": ["python", "new.py"]}}
        with patch('admin_routes.write_file_content'):
            update_data = {
                "content": json.dumps(test_config, indent=2),
                "file_type": "json"
            }
            
            response = client.post("/admin/mcp-config", json=update_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["updated_by"] == "admin@example.com"
    
    def test_get_llm_config(self):
        """Test getting LLM configuration."""
        app = create_test_app()
        
        def mock_require_admin():
            return "admin@example.com"
        
        from admin_routes import require_admin
        app.dependency_overrides[require_admin] = mock_require_admin
        client = TestClient(app)
        
        test_yaml = "models:\n  gpt-4:\n    model_url: 'https://api.openai.com'"
        with patch('admin_routes.get_file_content', return_value=test_yaml):
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value.st_mtime = 1640995200
                
                response = client.get("/admin/llm-config")
                assert response.status_code == 200
                data = response.json()
                assert "content" in data
                assert "parsed" in data
    
    def test_update_llm_config(self):
        """Test updating LLM configuration."""
        app = create_test_app()
        
        def mock_require_admin():
            return "admin@example.com"
        
        from admin_routes import require_admin
        app.dependency_overrides[require_admin] = mock_require_admin
        client = TestClient(app)
        
        test_yaml = "models:\n  gpt-4:\n    model_url: 'https://api.openai.com'"
        with patch('admin_routes.write_file_content'):
            update_data = {
                "content": test_yaml,
                "file_type": "yaml"
            }
            
            response = client.post("/admin/llm-config", json=update_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["updated_by"] == "admin@example.com"
    
    def test_get_app_logs(self):
        """Test getting application logs with OpenTelemetry."""
        app = create_test_app()
        
        def mock_require_admin():
            return "admin@example.com"
        
        from admin_routes import require_admin
        app.dependency_overrides[require_admin] = mock_require_admin
        client = TestClient(app)
        
        # Setup OpenTelemetry for testing
        from otel_config import setup_opentelemetry
        otel_config = setup_opentelemetry("test-admin-logs", "1.0.0")
        
        # Add some test logs
        import logging
        logger = logging.getLogger("test_admin_logs")
        logger.info("Test log entry for admin interface")
        logger.warning("Test warning for admin interface")
        
        response = client.get("/admin/logs?lines=50")
        assert response.status_code == 200
        data = response.json()
        
        # Check new OpenTelemetry format
        assert "logs" in data
        assert "stats" in data
        assert "format" in data
        assert data["format"] == "json"
        assert isinstance(data["logs"], list)
        
        # Verify log structure if we have logs
        if data["logs"]:
            log_entry = data["logs"][0]
            assert "timestamp" in log_entry
            assert "level" in log_entry
            assert "logger" in log_entry
            assert "message" in log_entry
    
    def test_get_system_status(self):
        """Test getting system status."""
        app = create_test_app()
        
        def mock_require_admin():
            return "admin@example.com"
        
        from admin_routes import require_admin
        app.dependency_overrides[require_admin] = mock_require_admin
        client = TestClient(app)
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.iterdir', return_value=[Path("test.json")]):
                with patch('pathlib.Path.glob', return_value=[Path("test.json")]):
                    with patch('pathlib.Path.stat') as mock_stat:
                        mock_stat.return_value.st_size = 1024
                        mock_stat.return_value.st_mtime = 1640995200
                        
                        response = client.get("/admin/system-status")
                        assert response.status_code == 200
                        data = response.json()
                        assert "overall_status" in data
                        assert "components" in data
                        assert data["checked_by"] == "admin@example.com"
    
    def test_trigger_health_check(self):
        """Test triggering health check."""
        app = create_test_app()
        
        def mock_require_admin():
            return "admin@example.com"
        
        from admin_routes import require_admin
        app.dependency_overrides[require_admin] = mock_require_admin
        client = TestClient(app)
        
        response = client.post("/admin/trigger-health-check")
        assert response.status_code == 200
        data = response.json()
        assert data["triggered_by"] == "admin@example.com"
        assert "message" in data
    
    def test_reload_configuration(self):
        """Test reloading configuration."""
        app = create_test_app()
        
        def mock_require_admin():
            return "admin@example.com"
        
        from admin_routes import require_admin
        app.dependency_overrides[require_admin] = mock_require_admin
        client = TestClient(app)
        
        response = client.post("/admin/reload-config")
        assert response.status_code == 200
        data = response.json()
        assert data["reloaded_by"] == "admin@example.com"
        assert "message" in data


class TestAdminSetup:
    """Test admin setup functionality."""
    
    def test_setup_configfilesadmin_empty_directory(self):
        """Test setup when configfilesadmin is empty."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # Create source configfiles directory
                configfiles_dir = Path("configfiles")
                configfiles_dir.mkdir()
                
                # Create test files
                (configfiles_dir / "mcp.json").write_text('{"test": "config"}')
                (configfiles_dir / "llmconfig.yml").write_text('models:\n  test: config')
                
                # Run setup
                setup_configfilesadmin()
                
                # Check that files were copied
                admin_dir = Path("configfilesadmin")
                assert admin_dir.exists()
                assert (admin_dir / "mcp.json").exists()
                assert (admin_dir / "llmconfig.yml").exists()
                
                # Check content
                assert (admin_dir / "mcp.json").read_text() == '{"test": "config"}'
                
            finally:
                os.chdir(original_cwd)
    
    def test_setup_configfilesadmin_existing_files(self):
        """Test setup when configfilesadmin already has files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # Create source and admin directories
                configfiles_dir = Path("configfiles")
                admin_dir = Path("configfilesadmin")
                configfiles_dir.mkdir()
                admin_dir.mkdir()
                
                # Create files in both directories
                (configfiles_dir / "mcp.json").write_text('{"source": "config"}')
                (admin_dir / "existing.json").write_text('{"existing": "file"}')
                
                # Run setup
                setup_configfilesadmin()
                
                # Check that existing file is preserved and source is not copied
                assert (admin_dir / "existing.json").exists()
                assert not (admin_dir / "mcp.json").exists()
                assert (admin_dir / "existing.json").read_text() == '{"existing": "file"}'
                
            finally:
                os.chdir(original_cwd)


class TestAdminUtilities:
    """Test admin utility functions."""
    
    def test_get_admin_config_path(self):
        """Test getting admin config path."""
        from admin_routes import get_admin_config_path
        
        path = get_admin_config_path("test.json")
        assert str(path) == "configfilesadmin/test.json"
        assert isinstance(path, Path)
    
    def test_write_file_content_json_validation(self):
        """Test JSON validation in write_file_content.""" 
        from admin_routes import write_file_content
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Valid JSON should work
            write_file_content(temp_path, '{"valid": "json"}', "json")
            assert temp_path.read_text() == '{"valid": "json"}'
            
            # Invalid JSON should raise HTTPException
            with pytest.raises(Exception):  # HTTPException converted to generic exception in test
                write_file_content(temp_path, '{"invalid": json}', "json")
                
        finally:
            temp_path.unlink(missing_ok=True)
    
    def test_write_file_content_yaml_validation(self):
        """Test YAML validation in write_file_content."""
        from admin_routes import write_file_content
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Valid YAML should work
            write_file_content(temp_path, 'key: value\nlist:\n  - item1', "yaml")
            content = temp_path.read_text()
            assert 'key: value' in content
            
        finally:
            temp_path.unlink(missing_ok=True)