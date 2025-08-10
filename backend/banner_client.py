"""Banner Client for integrating with admin-managed banner messages."""

import logging
import os
from typing import List
from pathlib import Path
from fastapi import APIRouter, Depends
from utils import get_current_user

logger = logging.getLogger(__name__)

# Create the banner router
banner_router = APIRouter(prefix="/api", tags=["banner"])


class BannerClient:
    """Client for reading admin-managed banner messages."""
    
    def __init__(self):
        from config import config_manager
        app_settings = config_manager.app_settings
        self.enabled = app_settings.banner_enabled
        
        if not self.enabled:
            logger.info("Banner system is disabled")
        else:
            logger.info("Banner Client initialized for admin-managed messages")
    
    async def get_banner_messages(self) -> List[str]:
        """Get banner messages from admin-managed messages.txt file."""
        if not self.enabled:
            logger.debug("Banner system is disabled, returning empty list")
            return []
        
        try:
            # Read from configfilesadmin/messages.txt
            messages_file = Path("configfilesadmin/messages.txt")
            
            if not messages_file.exists():
                logger.debug("Admin messages file not found, returning empty list")
                return []
            
            with open(messages_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                messages = [line.strip() for line in lines if line.strip()]
            
            logger.info(f"Retrieved {len(messages)} banner messages from admin config")
            return messages
            
        except Exception as exc:
            logger.error(f"Error reading admin banner messages: {exc}", exc_info=True)
            return []


def initialize_banner_client():
    """Initialize the global banner client after environment variables are loaded."""
    global banner_client
    banner_client = BannerClient()
    return banner_client


# Global banner client instance - will be initialized in main.py after env vars are loaded
banner_client = None


@banner_router.get("/banners")
async def get_banners(current_user: str = Depends(get_current_user)):
    """Get banner messages for display at the top of the UI."""
    if not banner_client:
        return {"messages": []}
    
    try:
        messages = await banner_client.get_banner_messages()
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Error fetching banner messages: {e}", exc_info=True)
        return {"messages": []}