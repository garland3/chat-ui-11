"""
Message orchestrator that coordinates between modules.

This is the core glue layer that brings together all the extracted modules
as described in Phase 1 of the refactoring plan.
"""

import logging
from typing import Any, Dict, List, Optional

# Import from modules
from modules.mcp_tools import MCPToolManager
from modules.rag import RAGClient
from modules.file_storage import S3StorageClient
from modules.llm import LLMCaller
from modules.config import ConfigManager

logger = logging.getLogger(__name__)


class MessageOrchestrator:
    """
    Coordinates between modules with minimal coupling.
    
    This replaces the tightly coupled logic that was previously in main.py
    and various other files.
    """
    
    def __init__(self):
        """Initialize all module instances."""
        self.mcp_tools = MCPToolManager()
        self.rag = RAGClient()
        self.file_storage = S3StorageClient()
        self.llm = LLMCaller()
        self.config = ConfigManager()
        
        logger.info("Message orchestrator initialized with all modules")
    
    # async def process_message(self, session_context, message):
    #     """
    #     Coordinate message processing between modules.
        
    #     This is where the orchestration logic would go to replace
    #     the complex interdependencies that existed before.
    #     """
    #     # This would contain the coordinated logic between modules
    #     # For now, this is a placeholder for the proper implementation
    #     logger.info("Processing message through orchestrator")
    #     pass
    
    
    def get_mcp_manager(self) -> MCPToolManager:
        """Get the MCP tools manager."""
        return self.mcp_tools
    
    def get_rag_client(self) -> RAGClient:
        """Get the RAG client."""
        return self.rag
    
    def get_file_storage(self) -> S3StorageClient:
        """Get the file storage client."""
        return self.file_storage
    
    def get_llm_caller(self) -> LLMCaller:
        """Get the LLM caller."""
        return self.llm
    
    def get_config_manager(self) -> ConfigManager:
        """Get the configuration manager."""
        return self.config


from core.session import session_manager

# Global orchestrator instance
orchestrator = MessageOrchestrator()

def create_chat_session(websocket):
    """Create a new chat session managed by the session manager."""
    return session_manager.create_session(websocket)

# Add create_chat_session method to orchestrator
orchestrator.create_chat_session = create_chat_session
