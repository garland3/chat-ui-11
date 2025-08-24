"""Application factory for dependency injection and wiring - Phase 1A."""

import logging
from ..config.config_manager import config_manager
from ..llm.llm_manager import LLMManager
from ..session.session_manager import SessionManager
from ..service_coordinator.service_coordinator import ServiceCoordinator

logger = logging.getLogger(__name__)


class AppFactory:
    """Application factory for Phase 1A - minimal setup for LLM-only chat."""

    def __init__(self) -> None:
        self.config_manager = config_manager
        self.llm_manager = None
        self.session_manager = None
        self.service_coordinator = None
        logger.info("AppFactory initialized - Phase 1A")

    def get_config_manager(self):
        """Get config manager."""
        return self.config_manager

    def get_llm_manager(self):
        """Get LLM manager - lazy initialization."""
        if self.llm_manager is None:
            self.llm_manager = LLMManager(
                llm_config=self.config_manager.llm_config,
                debug_mode=self.config_manager.app_settings.debug_mode
            )
        return self.llm_manager
    
    def get_session_manager(self):
        """Get session manager - lazy initialization."""
        if self.session_manager is None:
            self.session_manager = SessionManager()
        return self.session_manager
    
    def get_service_coordinator(self):
        """Get service coordinator - lazy initialization."""
        if self.service_coordinator is None:
            self.service_coordinator = ServiceCoordinator(
                session_manager=self.get_session_manager(),
                llm_manager=self.get_llm_manager()
            )
        return self.service_coordinator

    def initialize_managers(self):
        """Initialize all managers."""
        self.get_config_manager()
        self.get_llm_manager()
        self.get_session_manager()
        self.get_service_coordinator()
        logger.info("All managers initialized.")


# Global instance for Phase 1A
app_factory = AppFactory()
