"""Simple in-memory rate limit middleware.

Fixed-window counter per client IP (and optionally per-path) to throttle requests.
Uses shared security validation logic.

# Production guidance when deployed behind a reverse proxy
# -------------------------------------------------------
# - request.client.host will be the proxy address. Configure your reverse proxy
#   to send a trusted client IP header (e.g., X-Forwarded-For or X-Real-IP) and
#   parse it server-side to obtain the real client IP. Only trust headers set by
#   your proxy (strip them from public traffic at the edge).
# - Prefer keying limits by authenticated user identity (e.g., X-User-Email or
#   a JWT subject) when available, falling back to the real client IP.
# - Consider moving rate limiting to a centralized store (e.g., Redis) or to
#   the proxy for accuracy across multiple app instances.
"""

import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from middleware.security_validator import security_validator

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract client info
        client_host = getattr(request.client, "host", "unknown") if request.client else "unknown"
        path = request.url.path
        
        # Use shared rate limit validation
        rate_valid, retry_after = security_validator.validate_rate_limit(client_host, path)
        
        if not rate_valid:
            logger.warning(f"Rate limit exceeded for {client_host}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later."
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)