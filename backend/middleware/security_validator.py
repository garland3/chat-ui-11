"""
Reusable security validation logic for both HTTP middleware and WebSocket endpoints.
"""

import time
import logging
from typing import Optional, Tuple, Dict
from fastapi import WebSocket

from managers.app_factory.app_factory import app_factory
from managers.auth.utils import get_user_from_header

logger = logging.getLogger(__name__)


class SecurityValidator:
    """Centralized security validation for authentication and rate limiting."""

    def __init__(self):
        self._buckets: Dict[str, Tuple[float, int]] = {}

    async def validate_authentication(
        self, headers: Dict[str, str], debug_mode: bool = False
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate authentication for both HTTP and WebSocket requests.

        Returns:
            (is_valid, user_email, error_message)
        """
        try:
            x_email_header = headers.get("X-User-Email") or headers.get("x-user-email")

            if debug_mode:
                if x_email_header:
                    user_email = get_user_from_header(x_email_header)
                else:
                    config_manager = app_factory.get_config_manager()
                    user_email = config_manager.app_settings.test_user

                return True, user_email or "test@test.com", None
            else:
                # Production mode - require valid header
                user_email = get_user_from_header(x_email_header)
                if not user_email:
                    return False, None, "Missing or empty X-User-Email header"

                return True, user_email, None

        except Exception as e:
            logger.error(f"Authentication validation error: {e}", exc_info=True)
            return False, None, f"Authentication error: {str(e)}"

    def validate_rate_limit(
        self, client_host: str, path: str = ""
    ) -> Tuple[bool, Optional[int]]:
        """
        Validate rate limits for both HTTP and WebSocket requests.

        Returns:
            (is_allowed, retry_after_seconds)
        """
        try:
            config_manager = app_factory.get_config_manager()
            settings = config_manager.app_settings

            max_requests = settings.rate_limit_rpm
            window_seconds = settings.rate_limit_window_seconds
            per_path = settings.rate_limit_per_path

            # Generate key
            key = client_host
            if per_path and path:
                key = f"{client_host}:{path}"

            current_time = time.time()

            # Check if key exists and if window has expired
            if key in self._buckets:
                window_start, count = self._buckets[key]
                if current_time - window_start > window_seconds:
                    # Window expired, reset
                    self._buckets[key] = (current_time, 1)
                    return True, None
                elif count >= max_requests:
                    # Rate limit exceeded
                    retry_after = (
                        int(window_seconds - (current_time - window_start)) + 1
                    )
                    return False, retry_after
                else:
                    # Within limit, increment
                    self._buckets[key] = (window_start, count + 1)
                    return True, None
            else:
                # New key
                self._buckets[key] = (current_time, 1)
                return True, None

        except Exception as e:
            logger.error(f"Rate limit validation error: {e}", exc_info=True)
            # On error, allow request but log the issue
            return True, None


# Global instance for reuse
security_validator = SecurityValidator()


def extract_headers_from_websocket(websocket: WebSocket) -> Dict[str, str]:
    """Extract headers from WebSocket connection for validation.

    Note: Do NOT derive identity from query parameters. Identity must come from
    trusted headers injected by the reverse proxy (e.g., X-User-Email) or from
    a signed token. Query params are considered user-controlled and untrusted.
    """
    headers: Dict[str, str] = {}

    # Get headers from WebSocket scope
    if hasattr(websocket, "scope") and "headers" in websocket.scope:
        for name, value in websocket.scope["headers"]:
            headers[name.decode("utf-8").lower()] = value.decode("utf-8")

    return headers


def get_client_host_from_websocket(websocket: WebSocket) -> str:
    """Extract client host from WebSocket for rate limiting."""
    try:
        if hasattr(websocket, "client") and websocket.client:
            return websocket.client.host

        # Fallback to scope
        if hasattr(websocket, "scope") and "client" in websocket.scope:
            client_info = websocket.scope["client"]
            if client_info and len(client_info) > 0:
                return client_info[0]

        return "unknown"
    except Exception:
        return "unknown"


async def validate_websocket_security(
    websocket: WebSocket, path: str = "/ws"
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate WebSocket connection security (auth + rate limiting).

    Returns:
        (is_valid, user_email, error_message)
    """
    try:
        config_manager = app_factory.get_config_manager()
        debug_mode = config_manager.app_settings.debug_mode

        # Extract security information
        headers = extract_headers_from_websocket(websocket)
        client_host = get_client_host_from_websocket(websocket)
        origin = headers.get("origin")

        # Optional Origin allowlist enforcement (mitigate CSWSH)
        if getattr(
            config_manager.app_settings, "security_ws_origin_check_enabled", False
        ):
            allowed = (
                getattr(config_manager.app_settings, "security_ws_allowed_origins", [])
                or []
            )
            if not origin or origin not in allowed:
                return False, None, "Invalid WebSocket Origin"

        # Validate authentication
        (
            auth_valid,
            user_email,
            auth_error,
        ) = await security_validator.validate_authentication(headers, debug_mode)

        if not auth_valid:
            return False, None, f"Authentication failed: {auth_error}"

        # Validate rate limits
        rate_valid, retry_after = security_validator.validate_rate_limit(
            client_host, path
        )

        if not rate_valid:
            return (
                False,
                None,
                f"Rate limit exceeded. Retry after {retry_after} seconds",
            )

        return True, user_email, None

    except Exception as e:
        logger.error(f"WebSocket security validation error: {e}", exc_info=True)
        return False, None, f"Security validation error: {str(e)}"
