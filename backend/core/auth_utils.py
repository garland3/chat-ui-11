"""
Minimal auth utilities stub for basic chat functionality.
This is a temporary implementation for testing.
"""

import logging
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)


def create_authorization_manager(auth_check_func: Optional[Callable] = None) -> Any:
    """
    Create a simple authorization manager stub.
    For basic chat, this just allows all operations.
    """
    class SimpleAuthManager:
        def __init__(self, auth_func):
            self.auth_func = auth_func or (lambda *args, **kwargs: True)
        
        def check_authorization(self, *args, **kwargs) -> bool:
            """Simple auth check - allows everything for basic chat."""
            return True
        
        def filter_authorized_servers(self, servers, user_email, auth_check_func):
            """Filter servers based on authorization - for basic chat, allow all."""
            return servers
        
        def __call__(self, *args, **kwargs):
            return self.check_authorization(*args, **kwargs)
    
    return SimpleAuthManager(auth_check_func)