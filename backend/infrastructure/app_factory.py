"""Application factory for dependency injection and wiring."""

import logging
from typing import Optional

from application.chat.service import ChatService
from interfaces.llm import LLMProtocol
from interfaces.tools import ToolManagerProtocol
from interfaces.transport import ChatConnectionProtocol
from modules.config import ConfigManager
from modules.file_storage import S3StorageClient
from modules.llm.litellm_caller import LiteLLMCaller
from modules.mcp_tools import MCPToolManager
from modules.rag import RAGClient

logger = logging.getLogger(__name__)


class AppFactory:
    """
    Application factory that wires dependencies.
    Replaces the global orchestrator singleton with proper DI.
    """
    
    def __init__(self):
        """Initialize the factory with all dependencies."""
        # Initialize configuration first
        self.config_manager = ConfigManager()
        
        # Initialize modules
        self.llm_caller = LiteLLMCaller(
            self.config_manager.llm_config, 
            debug_mode=self.config_manager.app_settings.debug_mode
        )
        self.mcp_tools = MCPToolManager()
        self.rag_client = RAGClient()
        self.file_storage = S3StorageClient()
        
        logger.info("AppFactory initialized with all dependencies")
    
    def create_chat_service(
        self,
        connection: Optional[ChatConnectionProtocol] = None
    ) -> ChatService:
        """
        Create a chat service with dependencies.
        
        Args:
            connection: Optional connection for sending updates
            
        Returns:
            Configured ChatService instance
        """
        return ChatService(
            llm=self.llm_caller,
            tool_manager=self.mcp_tools,
            connection=connection
        )
    
    def get_config_manager(self) -> ConfigManager:
        """Get the configuration manager."""
        return self.config_manager
    
    def get_llm_caller(self) -> LiteLLMCaller:
        """Get the LLM caller."""
        return self.llm_caller
    
    def get_mcp_manager(self) -> MCPToolManager:
        """Get the MCP tools manager."""
        return self.mcp_tools
    
    def get_rag_client(self) -> RAGClient:
        """Get the RAG client."""
        return self.rag_client
    
    def get_file_storage(self) -> S3StorageClient:
        """Get the file storage client."""
        return self.file_storage


# Global app factory instance (temporary during migration)
# Eventually this should be created in main.py and passed to routes
app_factory = AppFactory()
