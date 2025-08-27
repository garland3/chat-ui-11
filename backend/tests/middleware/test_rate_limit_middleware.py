"""Unit tests for RateLimitMiddleware."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import Request
from starlette.responses import JSONResponse, Response

from middleware.rate_limit_middleware import RateLimitMiddleware


@pytest.fixture
def mock_app():
    """Mock FastAPI app."""
    return MagicMock()


@pytest.fixture
def mock_request():
    """Mock request object."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/test"
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def mock_call_next():
    """Mock call_next function."""

    async def call_next(request):
        response = MagicMock(spec=Response)
        response.status_code = 200
        return response

    return call_next


class TestRateLimitMiddleware:
    """Test cases for RateLimitMiddleware."""

    def test_init(self, mock_app):
        """Test middleware initialization."""
        middleware = RateLimitMiddleware(mock_app)
        # Since we use shared security validator, no attributes to check
        assert hasattr(middleware, "app")

    @patch("middleware.rate_limit_middleware.security_validator")
    @pytest.mark.asyncio
    async def test_request_allowed(
        self, mock_validator, mock_app, mock_request, mock_call_next
    ):
        """Test that allowed request passes through."""
        mock_validator.validate_rate_limit.return_value = (True, None)

        middleware = RateLimitMiddleware(mock_app)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        mock_validator.validate_rate_limit.assert_called_once_with(
            "127.0.0.1", "/api/test"
        )

    @patch("middleware.rate_limit_middleware.security_validator")
    @pytest.mark.asyncio
    async def test_request_rate_limited(
        self, mock_validator, mock_app, mock_request, mock_call_next
    ):
        """Test that rate limited request is rejected."""
        mock_validator.validate_rate_limit.return_value = (False, 30)

        middleware = RateLimitMiddleware(mock_app)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "30"
        mock_validator.validate_rate_limit.assert_called_once_with(
            "127.0.0.1", "/api/test"
        )

    @patch("middleware.rate_limit_middleware.security_validator")
    @pytest.mark.asyncio
    async def test_request_no_client(self, mock_validator, mock_app, mock_call_next):
        """Test request with no client info."""
        mock_validator.validate_rate_limit.return_value = (True, None)

        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.client = None

        middleware = RateLimitMiddleware(mock_app)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        mock_validator.validate_rate_limit.assert_called_once_with(
            "unknown", "/api/test"
        )

    @patch("middleware.rate_limit_middleware.security_validator")
    @pytest.mark.asyncio
    async def test_request_no_host_attribute(
        self, mock_validator, mock_app, mock_call_next
    ):
        """Test request with client but no host attribute."""
        mock_validator.validate_rate_limit.return_value = (True, None)

        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.client = MagicMock()
        # Remove host attribute to simulate error
        delattr(request.client, "host")

        middleware = RateLimitMiddleware(mock_app)
        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200
        mock_validator.validate_rate_limit.assert_called_once_with(
            "unknown", "/api/test"
        )
