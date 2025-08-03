"""Test OpenTelemetry admin routes functionality."""

import json
import logging
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock

# Add backend directory to Python path  
sys.path.insert(0, str(Path(__file__).parent.parent))

from otel_config import setup_opentelemetry, get_otel_config
import admin_routes

@pytest.fixture
def setup_otel():
    """Setup OpenTelemetry for testing."""
    return setup_opentelemetry("test-admin-routes", "1.0.0")

def test_otel_config_initialization(setup_otel):
    """Test OpenTelemetry configuration initialization."""
    otel_config = setup_otel
    
    assert otel_config is not None
    assert otel_config.service_name == "test-admin-routes"
    assert otel_config.service_version == "1.0.0"
    assert otel_config.log_file.name == "app.jsonl"

def test_structured_logging(setup_otel):
    """Test structured JSON logging."""
    otel_config = setup_otel
    logger = logging.getLogger("test_logging")
    
    # Generate test logs
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message", extra={"test_field": "test_value"})
    
    # Read logs back
    logs = otel_config.read_logs(10)
    
    # Verify we have logs
    assert len(logs) > 0
    
    # Check structure of most recent logs
    recent_logs = [log for log in logs if log['logger'] == 'test_logging']
    assert len(recent_logs) >= 3
    
    # Check required fields
    for log in recent_logs:
        assert 'timestamp' in log
        assert 'level' in log
        assert 'logger' in log
        assert 'message' in log
        assert 'module' in log
        assert 'function' in log
        assert 'line' in log
        assert log['logger'] == 'test_logging'

def test_log_stats(setup_otel):
    """Test log statistics functionality."""
    otel_config = setup_otel
    stats = otel_config.get_log_stats()
    
    assert 'file_exists' in stats
    assert 'file_size' in stats
    assert 'line_count' in stats
    assert 'file_path' in stats
    assert stats['file_exists'] is True
    assert stats['file_size'] > 0
    assert stats['line_count'] > 0

def test_otel_config_global_access():
    """Test global OpenTelemetry configuration access."""
    config = get_otel_config()
    assert config is not None
    assert config.service_name == "test-admin-routes"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])