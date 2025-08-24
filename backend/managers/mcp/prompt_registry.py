"""Registry for managing MCP prompts."""

import logging
from typing import Dict, List, Optional
from .mcp_models import MCPPrompt

logger = logging.getLogger(__name__)


class PromptRegistry:
    """Registry for MCP prompts."""
    
    def __init__(self):
        self._prompts: Dict[str, MCPPrompt] = {}  # full_name -> prompt
        self._prompts_by_server: Dict[str, List[MCPPrompt]] = {}  # server_name -> prompts
    
    def add_prompt(self, prompt: MCPPrompt) -> None:
        """Add a prompt to the registry."""
        # Store by full name
        self._prompts[prompt.full_name] = prompt
        
        # Store by server
        if prompt.server_name not in self._prompts_by_server:
            self._prompts_by_server[prompt.server_name] = []
        self._prompts_by_server[prompt.server_name].append(prompt)
        
        logger.debug(f"Added prompt to registry: {prompt.full_name}")
    
    def get_prompt_by_name(self, full_name: str) -> Optional[MCPPrompt]:
        """Get a prompt by its full name."""
        return self._prompts.get(full_name)
    
    def get_prompts_by_server(self, server_name: str) -> List[MCPPrompt]:
        """Get all prompts for a specific server."""
        return self._prompts_by_server.get(server_name, [])
    
    def get_all_prompts(self) -> List[MCPPrompt]:
        """Get all registered prompts."""
        return list(self._prompts.values())
    
    def get_enabled_prompts(self) -> List[MCPPrompt]:
        """Get only enabled prompts."""
        return [prompt for prompt in self._prompts.values() if prompt.enabled]
    
    def remove_prompt(self, full_name: str) -> bool:
        """Remove a prompt from the registry."""
        prompt = self._prompts.get(full_name)
        if prompt:
            # Remove from main registry
            del self._prompts[full_name]
            
            # Remove from server registry
            server_prompts = self._prompts_by_server.get(prompt.server_name, [])
            self._prompts_by_server[prompt.server_name] = [
                p for p in server_prompts if p.full_name != full_name
            ]
            
            logger.debug(f"Removed prompt from registry: {full_name}")
            return True
        return False
    
    def remove_prompts_by_server(self, server_name: str) -> int:
        """Remove all prompts for a specific server."""
        server_prompts = self._prompts_by_server.get(server_name, [])
        count = 0
        
        for prompt in server_prompts:
            if prompt.full_name in self._prompts:
                del self._prompts[prompt.full_name]
                count += 1
        
        if server_name in self._prompts_by_server:
            del self._prompts_by_server[server_name]
        
        if count > 0:
            logger.debug(f"Removed {count} prompts for server: {server_name}")
        
        return count
    
    def prompt_exists(self, full_name: str) -> bool:
        """Check if a prompt exists in the registry."""
        return full_name in self._prompts
    
    def get_prompt_names(self) -> List[str]:
        """Get list of all prompt names."""
        return list(self._prompts.keys())
    
    def get_server_names(self) -> List[str]:
        """Get list of server names that have prompts."""
        return list(self._prompts_by_server.keys())
    
    def clear(self) -> None:
        """Clear all prompts from the registry."""
        self._prompts.clear()
        self._prompts_by_server.clear()
        logger.debug("Cleared prompt registry")
    
    def count(self) -> int:
        """Get count of registered prompts."""
        return len(self._prompts)
    
    def count_by_server(self, server_name: str) -> int:
        """Get count of prompts for a specific server."""
        return len(self._prompts_by_server.get(server_name, []))
