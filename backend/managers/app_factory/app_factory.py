"""Application factory for dependency injection and wiring - Phase 1A."""

import logging
from ..config.config_manager import config_manager
from ..llm.llm_manager import LLMManager
from ..session.session_manager import SessionManager
from ..service_coordinator.service_coordinator import ServiceCoordinator
from managers.mcp.mcp_manager import MCPManager
from managers.tools.tool_caller import ToolCaller
from managers.agent.tool_call_orchestrator import ToolCallOrchestrator

logger = logging.getLogger(__name__)


class AppFactory:
    """Application factory for Phase 1A - minimal setup for LLM-only chat."""

    def __init__(self) -> None:
        self.config_manager = config_manager
        self.llm_manager = None
        self.session_manager = None
        self.service_coordinator = None
        self.mcp_manager = None
        self.tool_caller = None
        self.tool_orchestrator = None
        logger.info("AppFactory initialized - Phase 1A")

    def get_config_manager(self):
        """Get config manager."""
        return self.config_manager

    def get_llm_manager(self):
        """Get LLM manager - lazy initialization."""
        if self.llm_manager is None:
            self.llm_manager = LLMManager(
                llm_config=self.config_manager.llm_config,
                debug_mode=self.config_manager.app_settings.debug_mode,
            )
        return self.llm_manager

    def get_session_manager(self):
        """Get session manager - lazy initialization."""
        if self.session_manager is None:
            self.session_manager = SessionManager()
        return self.session_manager

    async def get_service_coordinator(self):
        """Get service coordinator - lazy initialization."""
        if self.service_coordinator is None:
            # Initialize MCP and tool managers first
            mcp_manager = await self.get_mcp_manager()
            tool_caller = await self.get_tool_caller()
            tool_orchestrator = await self.get_tool_orchestrator()

            self.service_coordinator = ServiceCoordinator(
                session_manager=self.get_session_manager(),
                llm_manager=self.get_llm_manager(),
                mcp_manager=mcp_manager,
                tool_caller=tool_caller,
                tool_orchestrator=tool_orchestrator,
            )
        return self.service_coordinator

    async def get_mcp_manager(self):
        """Get MCP manager - lazy initialization."""
        if self.mcp_manager is None:
            self.mcp_manager = MCPManager(self.config_manager)
            await self.mcp_manager.initialize()
        return self.mcp_manager

    async def get_tool_caller(self):
        """Get tool caller - lazy initialization."""
        if self.tool_caller is None:
            mcp_manager = await self.get_mcp_manager()
            self.tool_caller = ToolCaller(mcp_manager)
        return self.tool_caller

    async def get_tool_orchestrator(self):
        """Get tool orchestrator - lazy initialization."""
        if self.tool_orchestrator is None:
            tool_caller = await self.get_tool_caller()
            llm_manager = self.get_llm_manager()
            self.tool_orchestrator = ToolCallOrchestrator(tool_caller, llm_manager)
        return self.tool_orchestrator

    async def initialize_managers(self):
        """Initialize all managers."""
        self.get_config_manager()
        self.get_llm_manager()
        self.get_session_manager()
        await self.get_service_coordinator()
        logger.info("All managers initialized.")


# Global instance for Phase 1A
app_factory = AppFactory()
