"""Banner Client for integrating with banner mock endpoint."""

import logging
import os
from typing import Dict, List, Optional
from fastapi import HTTPException

from http_client import create_rag_client

logger = logging.getLogger(__name__)


class BannerClient:
    """Client for communicating with Banner mock API."""
    
    def __init__(self):
        from config import config_manager
        app_settings = config_manager.app_settings
        self.enabled = app_settings.banner_enabled
        self.mock_mode = app_settings.mock_banner
        self.base_url = app_settings.banner_mock_url
        self.api_key = app_settings.banner_api_key
        self.timeout = 10.0
        self.test_client = None
        self.http_client = create_rag_client(self.base_url, self.timeout)
        
        if not self.enabled:
            logger.info("Banner system is disabled")
            return
            
        if self.mock_mode:
            self._setup_test_client()
            logger.info(f"Banner Client initialized in mock mode: {self.mock_mode}")
        else:
            logger.info(f"Banner Client initialized in HTTP mode, URL: {self.base_url}")
    
    def _setup_test_client(self):
        """Set up FastAPI TestClient for mock mode."""
        try:
            import sys
            import os
            # Add the sys-admin-mock directory to the path
            banner_mock_path = os.path.join(os.path.dirname(__file__), "..", "sys-admin-mock")
            banner_mock_path = os.path.abspath(banner_mock_path)
            logger.info(f"Adding Banner mock path to sys.path: {banner_mock_path}")
            
            if banner_mock_path not in sys.path:
                sys.path.insert(0, banner_mock_path)
            
            from fastapi.testclient import TestClient
            # Import the app from the banner mock
            logger.info("Importing main_banner_mock module...")
            from main_banner_mock import app as banner_app
            
            self.test_client = TestClient(banner_app)
            logger.info("Banner TestClient initialized successfully")
        except Exception as exc:
            logger.error(f"Failed to setup Banner TestClient: {exc}", exc_info=True)
            # Fall back to HTTP mode
            self.mock_mode = False
        
    async def get_banner_messages(self) -> List[str]:
        """Get banner messages from the banner service."""
        if not self.enabled:
            logger.debug("Banner system is disabled, returning empty list")
            return []
            
        logger.info(f"get_banner_messages called - mock_mode: {self.mock_mode}, test_client: {self.test_client is not None}")
        
        headers = {"X-API-Key": self.api_key or "mock_api_key"}
        
        if self.mock_mode and self.test_client:
            try:
                logger.info(f"Using TestClient to get banner messages")
                response = self.test_client.get("/banner", headers=headers)
                response.raise_for_status()
                data = response.json()
                messages = [msg["message"] for msg in data.get("messages", [])]
                logger.info(f"Retrieved {len(messages)} banner messages via TestClient")
                return messages
            except Exception as exc:
                logger.error(f"TestClient error while getting banner messages: {exc}", exc_info=True)
                return []
        
        # HTTP mode using unified client
        try:
            # Use the same pattern as RAG client but adapt for headers
            import httpx
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/banner", headers=headers)
                response.raise_for_status()
                data = response.json()
                messages = [msg["message"] for msg in data.get("messages", [])]
                logger.info(f"Retrieved {len(messages)} banner messages via HTTP")
                return messages
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                logger.warning("Banner API authentication failed - invalid API key")
            else:
                logger.warning(f"HTTP error getting banner messages: {exc.response.status_code}")
            # Return empty list for graceful degradation instead of raising
            return []
        except Exception as exc:
            logger.error(f"Unexpected error while getting banner messages: {exc}", exc_info=True)
            return []


def initialize_banner_client():
    """Initialize the global banner client after environment variables are loaded."""
    global banner_client
    banner_client = BannerClient()
    return banner_client


# Global banner client instance - will be initialized in main.py after env vars are loaded
banner_client = None