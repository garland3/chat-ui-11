"""Unit tests for SecurityHeadersMiddleware."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import Request
from starlette.responses import Response

from middleware.security_headers_middleware import SecurityHeadersMiddleware


class MockAppSettings:
    """Mock app settings for testing."""

    def __init__(self, **kwargs):
        self.security_nosniff_enabled = kwargs.get("security_nosniff_enabled", True)
        self.security_xfo_enabled = kwargs.get("security_xfo_enabled", True)
        self.security_xfo_value = kwargs.get("security_xfo_value", "SAMEORIGIN")
        self.security_referrer_policy_enabled = kwargs.get(
            "security_referrer_policy_enabled", True
        )
        self.security_referrer_policy_value = kwargs.get(
            "security_referrer_policy_value", "no-referrer"
        )
        self.security_csp_enabled = kwargs.get("security_csp_enabled", True)
        self.security_csp_value = kwargs.get("security_csp_value", "default-src 'self'")


class MockConfigManager:
    """Mock config manager for testing."""

    def __init__(self, **kwargs):
        self.app_settings = MockAppSettings(**kwargs)


@pytest.fixture
def mock_app():
    """Mock FastAPI app."""
    return MagicMock()


@pytest.fixture
def mock_request():
    """Mock request object."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/test"
    return request


@pytest.fixture
def mock_response():
    """Mock response object."""
    response = MagicMock(spec=Response)
    response.headers = {}
    return response


@pytest.fixture
def mock_call_next(mock_response):
    """Mock call_next function."""

    async def call_next(request):
        return mock_response

    return call_next


class TestSecurityHeadersMiddleware:
    """Test cases for SecurityHeadersMiddleware."""

    @patch("middleware.security_headers_middleware.config_manager")
    def test_init(self, mock_config_manager, mock_app):
        """Test middleware initialization."""
        mock_config_manager.app_settings = MockAppSettings()

        middleware = SecurityHeadersMiddleware(mock_app)

        assert middleware.settings is mock_config_manager.app_settings

    @patch("middleware.security_headers_middleware.config_manager")
    @pytest.mark.asyncio
    async def test_all_headers_enabled_default(
        self, mock_config_manager, mock_app, mock_request, mock_call_next, mock_response
    ):
        """Test all security headers are added with default settings."""
        mock_config_manager.app_settings = MockAppSettings()

        middleware = SecurityHeadersMiddleware(mock_app)
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check all default headers are set
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["Content-Security-Policy"] == "default-src 'self'"

    @patch("middleware.security_headers_middleware.config_manager")
    @pytest.mark.asyncio
    async def test_custom_header_values(
        self, mock_config_manager, mock_app, mock_request, mock_call_next, mock_response
    ):
        """Test custom header values are used."""
        custom_csp = "default-src 'self'; script-src 'unsafe-inline'"
        mock_config_manager.app_settings = MockAppSettings(
            security_xfo_value="DENY",
            security_referrer_policy_value="strict-origin-when-cross-origin",
            security_csp_value=custom_csp,
        )

        middleware = SecurityHeadersMiddleware(mock_app)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert response.headers["Content-Security-Policy"] == custom_csp

    @patch("middleware.security_headers_middleware.config_manager")
    @pytest.mark.asyncio
    async def test_nosniff_disabled(
        self, mock_config_manager, mock_app, mock_request, mock_call_next, mock_response
    ):
        """Test X-Content-Type-Options header is not set when disabled."""
        mock_config_manager.app_settings = MockAppSettings(
            security_nosniff_enabled=False
        )

        middleware = SecurityHeadersMiddleware(mock_app)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "X-Content-Type-Options" not in response.headers
        # Other headers should still be set
        assert "X-Frame-Options" in response.headers

    @patch("middleware.security_headers_middleware.config_manager")
    @pytest.mark.asyncio
    async def test_xfo_disabled(
        self, mock_config_manager, mock_app, mock_request, mock_call_next, mock_response
    ):
        """Test X-Frame-Options header is not set when disabled."""
        mock_config_manager.app_settings = MockAppSettings(security_xfo_enabled=False)

        middleware = SecurityHeadersMiddleware(mock_app)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "X-Frame-Options" not in response.headers
        # Other headers should still be set
        assert "X-Content-Type-Options" in response.headers

    @patch("middleware.security_headers_middleware.config_manager")
    @pytest.mark.asyncio
    async def test_referrer_policy_disabled(
        self, mock_config_manager, mock_app, mock_request, mock_call_next, mock_response
    ):
        """Test Referrer-Policy header is not set when disabled."""
        mock_config_manager.app_settings = MockAppSettings(
            security_referrer_policy_enabled=False
        )

        middleware = SecurityHeadersMiddleware(mock_app)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "Referrer-Policy" not in response.headers
        # Other headers should still be set
        assert "X-Content-Type-Options" in response.headers

    @patch("middleware.security_headers_middleware.config_manager")
    @pytest.mark.asyncio
    async def test_csp_disabled(
        self, mock_config_manager, mock_app, mock_request, mock_call_next, mock_response
    ):
        """Test Content-Security-Policy header is not set when disabled."""
        mock_config_manager.app_settings = MockAppSettings(security_csp_enabled=False)

        middleware = SecurityHeadersMiddleware(mock_app)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "Content-Security-Policy" not in response.headers
        # Other headers should still be set
        assert "X-Content-Type-Options" in response.headers

    @patch("middleware.security_headers_middleware.config_manager")
    @pytest.mark.asyncio
    async def test_csp_empty_value(
        self, mock_config_manager, mock_app, mock_request, mock_call_next, mock_response
    ):
        """Test CSP header is not set when value is empty or None."""
        mock_config_manager.app_settings = MockAppSettings(
            security_csp_enabled=True, security_csp_value=""
        )

        middleware = SecurityHeadersMiddleware(mock_app)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "Content-Security-Policy" not in response.headers

    @patch("middleware.security_headers_middleware.config_manager")
    @pytest.mark.asyncio
    async def test_csp_none_value(
        self, mock_config_manager, mock_app, mock_request, mock_call_next, mock_response
    ):
        """Test CSP header is not set when value is None."""
        mock_config_manager.app_settings = MockAppSettings(
            security_csp_enabled=True, security_csp_value=None
        )

        middleware = SecurityHeadersMiddleware(mock_app)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "Content-Security-Policy" not in response.headers

    @patch("middleware.security_headers_middleware.config_manager")
    @pytest.mark.asyncio
    async def test_existing_headers_not_overwritten(
        self, mock_config_manager, mock_app, mock_request, mock_call_next
    ):
        """Test that existing headers are not overwritten."""
        mock_config_manager.app_settings = MockAppSettings()

        # Mock response with existing headers
        response = MagicMock(spec=Response)
        response.headers = {
            "X-Content-Type-Options": "existing-value",
            "X-Frame-Options": "existing-xfo",
            "Referrer-Policy": "existing-referrer",
            "Content-Security-Policy": "existing-csp",
        }

        async def call_next_with_existing_headers(request):
            return response

        middleware = SecurityHeadersMiddleware(mock_app)
        result = await middleware.dispatch(
            mock_request, call_next_with_existing_headers
        )

        # Existing headers should not be changed
        assert result.headers["X-Content-Type-Options"] == "existing-value"
        assert result.headers["X-Frame-Options"] == "existing-xfo"
        assert result.headers["Referrer-Policy"] == "existing-referrer"
        assert result.headers["Content-Security-Policy"] == "existing-csp"

    @patch("middleware.security_headers_middleware.config_manager")
    @pytest.mark.asyncio
    async def test_partial_existing_headers(
        self, mock_config_manager, mock_app, mock_request, mock_call_next
    ):
        """Test that only missing headers are added when some already exist."""
        mock_config_manager.app_settings = MockAppSettings()

        # Mock response with some existing headers
        response = MagicMock(spec=Response)
        response.headers = {
            "X-Content-Type-Options": "existing-nosniff",
            "Custom-Header": "custom-value",
        }

        async def call_next_with_partial_headers(request):
            return response

        middleware = SecurityHeadersMiddleware(mock_app)
        result = await middleware.dispatch(mock_request, call_next_with_partial_headers)

        # Existing header should not be changed
        assert result.headers["X-Content-Type-Options"] == "existing-nosniff"
        # Missing headers should be added
        assert result.headers["X-Frame-Options"] == "SAMEORIGIN"
        assert result.headers["Referrer-Policy"] == "no-referrer"
        assert result.headers["Content-Security-Policy"] == "default-src 'self'"
        # Custom header should remain
        assert result.headers["Custom-Header"] == "custom-value"

    @patch("middleware.security_headers_middleware.config_manager")
    @pytest.mark.asyncio
    async def test_all_headers_disabled(
        self, mock_config_manager, mock_app, mock_request, mock_call_next, mock_response
    ):
        """Test no headers are added when all are disabled."""
        mock_config_manager.app_settings = MockAppSettings(
            security_nosniff_enabled=False,
            security_xfo_enabled=False,
            security_referrer_policy_enabled=False,
            security_csp_enabled=False,
        )

        middleware = SecurityHeadersMiddleware(mock_app)
        response = await middleware.dispatch(mock_request, mock_call_next)

        # No security headers should be added
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Referrer-Policy",
            "Content-Security-Policy",
        ]
        for header in security_headers:
            assert header not in response.headers

    @patch("middleware.security_headers_middleware.config_manager")
    @pytest.mark.asyncio
    async def test_getattr_fallbacks(
        self, mock_config_manager, mock_app, mock_request, mock_call_next, mock_response
    ):
        """Test that getattr fallbacks work when settings don't have attributes."""

        # Create a minimal settings object that returns default values for missing attributes
        class MinimalSettings:
            def __getattr__(self, name):
                defaults = {
                    "security_nosniff_enabled": True,
                    "security_xfo_enabled": True,
                    "security_xfo_value": "SAMEORIGIN",
                    "security_referrer_policy_enabled": True,
                    "security_referrer_policy_value": "no-referrer",
                    "security_csp_enabled": True,
                    "security_csp_value": None,
                }
                return defaults.get(name, True)

        mock_config_manager.app_settings = MinimalSettings()

        middleware = SecurityHeadersMiddleware(mock_app)
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should use default values when attributes don't exist
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
        assert response.headers.get("Referrer-Policy") == "no-referrer"
        # CSP should not be set when value is None
        assert "Content-Security-Policy" not in response.headers
