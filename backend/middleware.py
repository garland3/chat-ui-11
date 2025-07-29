"""FastAPI middleware for authentication and logging."""

import logging

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from auth import get_user_from_header

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to handle authentication and logging."""
    
    def __init__(self, app, debug_mode: bool = False):
        super().__init__(app)
        self.debug_mode = debug_mode
        
    async def dispatch(self, request: Request, call_next) -> Response:
        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")
        
        # Skip auth for static files and auth endpoint
        if request.url.path.startswith('/static') or request.url.path == '/auth':
            return await call_next(request)
            
        # Check authentication
        user_email = None
        if self.debug_mode:
            user_email = "test@test.com"
            logger.info("Debug mode: using test user")
        else:
            x_email_header = request.headers.get('X-User-Email')
            user_email = get_user_from_header(x_email_header)
            
            if not user_email:
                logger.warning("Missing X-User-Email, redirecting to auth")
                return RedirectResponse(url="/auth", status_code=302)
        
        # Add user to request state
        request.state.user_email = user_email
        
        response = await call_next(request)
        return response