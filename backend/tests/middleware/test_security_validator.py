"""Unit tests for SecurityValidator."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import WebSocket

from middleware.security_validator import (
    SecurityValidator,
    extract_headers_from_websocket,
    get_client_host_from_websocket,
    validate_websocket_security,
)


class MockAppSettings:
    """Mock app settings for testing."""

    def __init__(self, **kwargs):
        self.debug_mode = kwargs.get("debug_mode", False)
        self.test_user = kwargs.get("test_user", "test@test.com")
        self.rate_limit_rpm = kwargs.get("rate_limit_rpm", 600)
        self.rate_limit_window_seconds = kwargs.get("rate_limit_window_seconds", 60)
        self.rate_limit_per_path = kwargs.get("rate_limit_per_path", False)


class MockConfigManager:
    """Mock config manager for testing."""

    def __init__(self, **kwargs):
        self.app_settings = MockAppSettings(**kwargs)


@pytest.fixture
def mock_websocket():
    """Mock WebSocket object."""
    websocket = MagicMock(spec=WebSocket)
    websocket.scope = {
        "headers": [
            (b"x-user-email", b"user@example.com"),
            (b"user-agent", b"test-agent"),
        ],
        "client": ("192.168.1.1", 12345),
    }
    websocket.client = MagicMock()
    websocket.client.host = "192.168.1.1"
    websocket.query_params = {}
    return websocket


class TestSecurityValidator:
    """Test cases for SecurityValidator."""

    def test_init(self):
        """Test validator initialization."""
        validator = SecurityValidator()
        assert validator._buckets == {}

    @patch("middleware.security_validator.app_factory")
    @pytest.mark.asyncio
    async def test_validate_authentication_debug_mode_with_header(
        self, mock_app_factory
    ):
        """Test authentication validation in debug mode with header."""
        mock_config_manager = MockConfigManager(
            debug_mode=True, test_user="debug@test.com"
        )
        mock_app_factory.get_config_manager.return_value = mock_config_manager

        validator = SecurityValidator()
        headers = {"x-user-email": "user@example.com"}

        is_valid, user_email, error = await validator.validate_authentication(
            headers, debug_mode=True
        )

        assert is_valid is True
        assert user_email == "user@example.com"
        assert error is None

    @patch("middleware.security_validator.app_factory")
    @pytest.mark.asyncio
    async def test_validate_authentication_debug_mode_without_header(
        self, mock_app_factory
    ):
        """Test authentication validation in debug mode without header."""
        mock_config_manager = MockConfigManager(
            debug_mode=True, test_user="debug@test.com"
        )
        mock_app_factory.get_config_manager.return_value = mock_config_manager

        validator = SecurityValidator()
        headers = {}

        is_valid, user_email, error = await validator.validate_authentication(
            headers, debug_mode=True
        )

        assert is_valid is True
        assert user_email == "debug@test.com"
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_authentication_production_mode_valid(self):
        """Test authentication validation in production mode with valid header."""
        validator = SecurityValidator()
        headers = {"x-user-email": "user@example.com"}

        is_valid, user_email, error = await validator.validate_authentication(
            headers, debug_mode=False
        )

        assert is_valid is True
        assert user_email == "user@example.com"
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_authentication_production_mode_invalid(self):
        """Test authentication validation in production mode without header."""
        validator = SecurityValidator()
        headers = {}

        is_valid, user_email, error = await validator.validate_authentication(
            headers, debug_mode=False
        )

        assert is_valid is False
        assert user_email is None
        assert "Missing or empty X-User-Email header" in error

    @patch("middleware.security_validator.app_factory")
    def test_validate_rate_limit_first_request(self, mock_app_factory):
        """Test rate limit validation for first request."""
        mock_config_manager = MockConfigManager(
            rate_limit_rpm=10, rate_limit_window_seconds=60
        )
        mock_app_factory.get_config_manager.return_value = mock_config_manager

        validator = SecurityValidator()

        is_allowed, retry_after = validator.validate_rate_limit("192.168.1.1")

        assert is_allowed is True
        assert retry_after is None
        assert "192.168.1.1" in validator._buckets

    @patch("middleware.security_validator.app_factory")
    @patch("middleware.security_validator.time")
    def test_validate_rate_limit_exceeded(self, mock_time, mock_app_factory):
        """Test rate limit validation when limit is exceeded."""
        mock_config_manager = MockConfigManager(
            rate_limit_rpm=2, rate_limit_window_seconds=60
        )
        mock_app_factory.get_config_manager.return_value = mock_config_manager
        mock_time.time.return_value = 1000.0

        validator = SecurityValidator()

        # First two requests should pass
        for i in range(2):
            is_allowed, retry_after = validator.validate_rate_limit("192.168.1.1")
            assert is_allowed is True

        # Third request should be blocked
        is_allowed, retry_after = validator.validate_rate_limit("192.168.1.1")

        assert is_allowed is False
        assert retry_after is not None
        assert retry_after > 0

    @patch("middleware.security_validator.app_factory")
    def test_validate_rate_limit_per_path(self, mock_app_factory):
        """Test per-path rate limiting."""
        mock_config_manager = MockConfigManager(
            rate_limit_rpm=1, rate_limit_window_seconds=60, rate_limit_per_path=True
        )
        mock_app_factory.get_config_manager.return_value = mock_config_manager

        validator = SecurityValidator()

        # Request to first path should pass
        is_allowed, _ = validator.validate_rate_limit("192.168.1.1", "/api/test1")
        assert is_allowed is True

        # Request to different path should also pass
        is_allowed, _ = validator.validate_rate_limit("192.168.1.1", "/api/test2")
        assert is_allowed is True


class TestWebSocketHelpers:
    """Test cases for WebSocket helper functions."""

    def test_extract_headers_from_websocket(self, mock_websocket):
        """Test header extraction from WebSocket."""
        headers = extract_headers_from_websocket(mock_websocket)

        assert headers["x-user-email"] == "user@example.com"
        assert headers["user-agent"] == "test-agent"

    def test_extract_headers_with_query_params(self, mock_websocket):
        """Query parameters should NOT affect identity headers."""
        mock_websocket.query_params = {"user_email": "query@example.com"}

        headers = extract_headers_from_websocket(mock_websocket)
        # Should still reflect the header value, not the query param
        assert headers["x-user-email"] == "user@example.com"

    def test_get_client_host_from_websocket(self, mock_websocket):
        """Test client host extraction from WebSocket."""
        host = get_client_host_from_websocket(mock_websocket)
        assert host == "192.168.1.1"

    def test_get_client_host_fallback_to_scope(self):
        """Test client host extraction fallback to scope."""
        websocket = MagicMock(spec=WebSocket)
        websocket.client = None
        websocket.scope = {"client": ("192.168.1.2", 12345)}

        host = get_client_host_from_websocket(websocket)
        assert host == "192.168.1.2"

    def test_get_client_host_unknown_fallback(self):
        """Test client host extraction with unknown fallback."""
        websocket = MagicMock(spec=WebSocket)
        websocket.client = None
        websocket.scope = {}

        host = get_client_host_from_websocket(websocket)
        assert host == "unknown"


class TestWebSocketSecurity:
    """Test cases for WebSocket security validation."""

    @patch("middleware.security_validator.app_factory")
    @pytest.mark.asyncio
    async def test_validate_websocket_security_success(
        self, mock_app_factory, mock_websocket
    ):
        """Test successful WebSocket security validation."""
        mock_config_manager = MockConfigManager(
            debug_mode=True, test_user="debug@test.com"
        )
        mock_app_factory.get_config_manager.return_value = mock_config_manager

        is_valid, user_email, error = await validate_websocket_security(mock_websocket)

        assert is_valid is True
        assert user_email == "user@example.com"  # From mock websocket headers
        assert error is None

    @patch("middleware.security_validator.app_factory")
    @pytest.mark.asyncio
    async def test_validate_websocket_security_auth_failure(self, mock_app_factory):
        """Test WebSocket security validation with auth failure."""
        mock_config_manager = MockConfigManager(debug_mode=False)
        mock_app_factory.get_config_manager.return_value = mock_config_manager

        # Create websocket without auth headers
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.scope = {"headers": [], "client": ("192.168.1.1", 12345)}
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = "192.168.1.1"
        mock_websocket.query_params = {}

        is_valid, user_email, error = await validate_websocket_security(mock_websocket)

        assert is_valid is False
        assert user_email is None
        assert "Authentication failed" in error

    @patch("middleware.security_validator.app_factory")
    @patch("middleware.security_validator.security_validator")
    @pytest.mark.asyncio
    async def test_validate_websocket_security_rate_limit_failure(
        self, mock_validator, mock_app_factory, mock_websocket
    ):
        """Test WebSocket security validation with rate limit failure."""
        mock_config_manager = MockConfigManager(
            debug_mode=True, test_user="debug@test.com"
        )
        mock_app_factory.get_config_manager.return_value = mock_config_manager

        # Mock successful auth but failed rate limit
        from unittest.mock import AsyncMock

        mock_validator.validate_authentication = AsyncMock(
            return_value=(True, "user@example.com", None)
        )
        mock_validator.validate_rate_limit.return_value = (False, 30)

        is_valid, user_email, error = await validate_websocket_security(mock_websocket)

        assert is_valid is False
        assert user_email is None
        assert "Rate limit exceeded. Retry after 30 seconds" in error
