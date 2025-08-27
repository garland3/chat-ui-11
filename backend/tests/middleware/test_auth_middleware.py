"""Unit tests for AuthMiddleware."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.responses import Response

from middleware.auth_middleware import AuthMiddleware


class MockAppFactory:
    """Mock app factory for testing."""

    def __init__(self, test_user="test@test.com"):
        self.config_manager = MagicMock()
        self.config_manager.app_settings.test_user = test_user

    def get_config_manager(self):
        return self.config_manager


@pytest.fixture
def mock_app():
    """Mock FastAPI app."""
    return MagicMock()


@pytest.fixture
def mock_request():
    """Mock request object."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/test"
    request.headers = {}
    request.state = MagicMock()
    return request


@pytest.fixture
def mock_call_next():
    """Mock call_next function."""

    async def call_next(request):
        response = MagicMock(spec=Response)
        response.status_code = 200
        return response

    return call_next


class TestAuthMiddleware:
    """Test cases for AuthMiddleware."""

    def test_init(self, mock_app):
        """Test middleware initialization."""
        middleware = AuthMiddleware(mock_app, debug_mode=True)
        assert middleware.debug_mode is True

        middleware = AuthMiddleware(mock_app, debug_mode=False)
        assert middleware.debug_mode is False

    @pytest.mark.asyncio
    async def test_static_files_bypass(self, mock_app, mock_request, mock_call_next):
        """Test that static files bypass auth."""
        middleware = AuthMiddleware(mock_app, debug_mode=False)
        mock_request.url.path = "/static/test.js"

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        # Should not set user_email since it bypassed auth (user_email won't be assigned)

    @pytest.mark.asyncio
    async def test_assets_bypass(self, mock_app, mock_request, mock_call_next):
        """Test that assets bypass auth."""
        middleware = AuthMiddleware(mock_app, debug_mode=False)
        mock_request.url.path = "/assets/main.css"

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_endpoint_bypass(self, mock_app, mock_request, mock_call_next):
        """Test that auth endpoint bypasses auth."""
        middleware = AuthMiddleware(mock_app, debug_mode=False)
        mock_request.url.path = "/auth"

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_root_path_bypass(self, mock_app, mock_request, mock_call_next):
        """Test that root path bypasses auth."""
        middleware = AuthMiddleware(mock_app, debug_mode=False)
        mock_request.url.path = "/"

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_favicon_bypass(self, mock_app, mock_request, mock_call_next):
        """Test that favicon bypasses auth."""
        middleware = AuthMiddleware(mock_app, debug_mode=False)
        mock_request.url.path = "/favicon.ico"

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_production_mode_with_header(
        self, mock_app, mock_request, mock_call_next
    ):
        """Test production mode with valid header."""
        middleware = AuthMiddleware(mock_app, debug_mode=False)
        mock_request.headers = {"X-User-Email": "user@example.com"}

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert mock_request.state.user_email == "user@example.com"

    @pytest.mark.asyncio
    async def test_production_mode_without_header(
        self, mock_app, mock_request, mock_call_next
    ):
        """Test production mode without header redirects to auth."""
        middleware = AuthMiddleware(mock_app, debug_mode=False)
        mock_request.headers = {}

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, RedirectResponse)
        assert response.status_code == 302
        assert "/auth" in str(response.headers.get("location", ""))

    @pytest.mark.asyncio
    async def test_production_mode_with_empty_header(
        self, mock_app, mock_request, mock_call_next
    ):
        """Test production mode with empty header."""
        middleware = AuthMiddleware(mock_app, debug_mode=False)
        mock_request.headers = {"X-User-Email": ""}

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, RedirectResponse)
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_production_mode_with_whitespace_header(
        self, mock_app, mock_request, mock_call_next
    ):
        """Test production mode with whitespace-only header redirects to auth."""
        middleware = AuthMiddleware(mock_app, debug_mode=False)
        mock_request.headers = {"X-User-Email": "   "}

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, RedirectResponse)
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_debug_mode_with_header(self, mock_app, mock_request, mock_call_next):
        """Test debug mode with header."""
        middleware = AuthMiddleware(mock_app, debug_mode=True)
        mock_request.headers = {"X-User-Email": "user@example.com"}

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert mock_request.state.user_email == "user@example.com"

    @pytest.mark.asyncio
    @patch("middleware.security_validator.app_factory")
    async def test_debug_mode_without_header_uses_test_user(
        self, mock_app_factory_module, mock_app, mock_request, mock_call_next
    ):
        """Test debug mode without header uses test user from config."""
        mock_factory = MockAppFactory("debug@test.com")
        mock_app_factory_module.get_config_manager.return_value = (
            mock_factory.config_manager
        )

        middleware = AuthMiddleware(mock_app, debug_mode=True)
        mock_request.headers = {}

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert mock_request.state.user_email == "debug@test.com"

    @pytest.mark.asyncio
    async def test_header_extraction_strips_whitespace(
        self, mock_app, mock_request, mock_call_next
    ):
        """Test that header extraction strips whitespace."""
        middleware = AuthMiddleware(mock_app, debug_mode=False)
        mock_request.headers = {"X-User-Email": "  user@example.com  "}

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert mock_request.state.user_email == "user@example.com"

    @pytest.mark.asyncio
    async def test_different_api_paths_require_auth(
        self, mock_app, mock_request, mock_call_next
    ):
        """Test that different API paths require auth."""
        middleware = AuthMiddleware(mock_app, debug_mode=False)

        test_paths = ["/api/test", "/admin/logs", "/config", "/webhook"]

        for path in test_paths:
            mock_request.url.path = path
            mock_request.headers = {}

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert isinstance(response, RedirectResponse), (
                f"Path {path} should require auth"
            )
            assert response.status_code == 302
