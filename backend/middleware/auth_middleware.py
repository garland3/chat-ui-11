"""FastAPI middleware for authentication and logging.
Uses shared security validation logic."""

import logging

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from middleware.security_validator import security_validator

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to handle authentication and logging."""

    def __init__(self, app, debug_mode: bool = False):
        super().__init__(app)
        self.debug_mode = debug_mode

    async def dispatch(self, request: Request, call_next) -> Response:
        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")

        # Skip auth for static files, auth endpoint, and assets
        if (
            request.url.path.startswith("/static")
            or request.url.path.startswith("/assets")
            or request.url.path == "/auth"
            or request.url.path in ["/", "/favicon.ico", "/vite.svg", "/logo.png"]
        ):
            return await call_next(request)

        # Use shared security validation
        headers = dict(request.headers)
        (
            auth_valid,
            user_email,
            auth_error,
        ) = await security_validator.validate_authentication(headers, self.debug_mode)

        if not auth_valid:
            logger.warning(f"Authentication failed: {auth_error}")
            return RedirectResponse(url="/auth", status_code=302)

        # Add user to request state
        request.state.user_email = user_email

        response = await call_next(request)
        return response
