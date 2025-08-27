"""
Minimal utilities for basic chat functionality.
"""

import logging
from typing import Optional
from fastapi import Request

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> str:
    """Get current user from request state (set by middleware)."""
    return getattr(request.state, "user_email", "test@test.com")


def get_user_from_header(x_email_header: Optional[str]) -> Optional[str]:
    """Extract user email from X-User-Email header."""
    if not x_email_header:
        return None
    return x_email_header.strip()
