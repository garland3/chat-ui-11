verbose = False

"""
Authorization utilities for MCP server access control.

This module provides reusable authorization functions that eliminate
duplicate authorization logic throughout the codebase.
"""

import logging
from typing import Callable, List, Set

logger = logging.getLogger(__name__)


class AuthorizationManager:
    """
    Centralized authorization management for MCP servers and tools.
    
    This class consolidates the authorization logic that was previously
    scattered across multiple files, providing a clean interface for
    checking user permissions and server access.
    """
    
    def __init__(self, auth_check_func: Callable[[str, str], bool]):
        """
        Initialize the authorization manager.
        
        Args:
            auth_check_func: Function to check if user is in a group (user_id, group_id) -> bool
        """
        self.auth_check_func = auth_check_func
    
    def get_user_groups_for_server(self, user_id: str, required_groups: List[str]) -> List[str]:
        """
        Get the groups that a user belongs to from a list of required groups.
        
        Args:
            user_id: User identifier
            required_groups: List of groups to check
            
        Returns:
            List of groups the user belongs to
        """
        user_groups = []
        for group in required_groups:
            try:
                if self.auth_check_func(user_id, group):
                    user_groups.append(group)
            except Exception as e:
                logger.error(f"Error checking group membership for user {user_id}, group {group}: {e}", exc_info=True)
        
        return user_groups
    
    def is_user_authorized_for_server(self, user_id: str, required_groups: List[str]) -> bool:
        """
        Check if a user is authorized to access a server.
        
        Args:
            user_id: User identifier
            required_groups: List of groups required for server access
            
        Returns:
            True if user is authorized, False otherwise
        """
        if not required_groups:
            # No group restrictions
            if verbose:
                logger.debug(f"Server has no group restrictions - authorizing user {user_id}")
            return True
        
        try:
            for group in required_groups:
                if self.auth_check_func(user_id, group):
                    if verbose:
                        logger.debug(f"User {user_id} authorized via group '{group}'")
                    return True
            
            if verbose:
                logger.debug(f"User {user_id} not authorized - not in any required groups: {required_groups}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking authorization for user {user_id}: {e}", exc_info=True)
            return False
    
    def filter_authorized_servers(
        self, 
        user_id: str, 
        servers_config: dict, 
        get_server_groups_func: Callable[[str], List[str]]
    ) -> List[str]:
        """
        Filter servers to only those the user is authorized to access.
        
        Args:
            user_id: User identifier
            servers_config: Dictionary of server configurations
            get_server_groups_func: Function to get required groups for a server
            
        Returns:
            List of authorized server names
        """
        authorized_servers = []
        available_servers = list(servers_config.keys())
        
        logger.debug(f"Checking authorization for user {user_id} across {len(available_servers)} servers")
        
        for server_name in available_servers:
            try:
                required_groups = get_server_groups_func(server_name)
                logger.debug(f"Server {server_name} requires groups: {required_groups}")
                
                if self.is_user_authorized_for_server(user_id, required_groups):
                    authorized_servers.append(server_name)
                #     logger.debug(f"User {user_id} authorized for server {server_name}")
                # else:
                #     logger.debug(f"User {user_id} NOT authorized for server {server_name}")
                    
            except Exception as e:
                logger.error(f"Error checking authorization for server {server_name}: {e}", exc_info=True)
        
        # logger.info(f"User {user_id} authorized for {len(authorized_servers)} servers: {authorized_servers}")
        return authorized_servers
    
    def validate_tool_access(
        self, 
        user_id: str, 
        selected_tools: List[str], 
        get_authorized_servers_func: Callable[[], List[str]]
    ) -> tuple[Set[str], List[str]]:
        """
        Validate tool access and return authorized server names and warnings.
        
        Args:
            user_id: User identifier
            selected_tools: List of selected tool keys (format: "server_tool")
            get_authorized_servers_func: Function to get authorized servers for user
            
        Returns:
            Tuple of (authorized_server_names, warning_messages)
        """
        if not selected_tools:
            return set(), []
        
        try:
            authorized_servers = set(get_authorized_servers_func())
            logger.debug(f"User {user_id} authorized for servers: {authorized_servers}")
            
            requested_servers = set()
            warnings = []
            
            for tool_key in selected_tools:
                parts = tool_key.split("_", 1)
                if len(parts) == 2:
                    server_name = parts[0]
                    
                    # Allow canvas pseudo-tool for all users
                    if server_name == "canvas":
                        requested_servers.add(server_name)
                    elif server_name in authorized_servers:
                        requested_servers.add(server_name)
                    else:
                        warning_msg = f"User {user_id} attempted to access unauthorized server: {server_name}"
                        if verbose:
                            logger.warning(warning_msg)
                        warnings.append(warning_msg)
            
            if not requested_servers:
                if verbose:
                    logger.info(f"No authorized servers requested by user {user_id}")
                return set(), warnings
            
            return requested_servers, warnings
            
        except Exception as e:
            logger.error(f"Error validating tool access for user {user_id}: {e}", exc_info=True)
            return set(), [f"Error validating tool access: {e}"]
    
    def handle_exclusive_servers(
        self, 
        requested_servers: Set[str], 
        is_server_exclusive_func: Callable[[str], bool]
    ) -> Set[str]:
        """
        Handle exclusive server logic - if exclusive servers are present, only allow one.
        
        Args:
            requested_servers: Set of requested server names
            is_server_exclusive_func: Function to check if a server is exclusive
            
        Returns:
            Final set of servers to use (respecting exclusive rules)
        """
        if not requested_servers:
            return set()
        
        try:
            exclusive_servers = []
            regular_servers = []
            
            for server_name in requested_servers:
                if is_server_exclusive_func(server_name):
                    exclusive_servers.append(server_name)
                else:
                    regular_servers.append(server_name)
            
            if exclusive_servers:
                if len(exclusive_servers) > 1:
                    if verbose:
                        logger.warning(f"Multiple exclusive servers selected, using only {exclusive_servers[0]}")
                final_servers = {exclusive_servers[0]}
                if verbose:
                    logger.info(f"Exclusive mode enabled for server: {exclusive_servers[0]}")
            else:
                final_servers = set(regular_servers)
            
            return final_servers
            
        except Exception as e:
            logger.error(f"Error handling exclusive servers: {e}", exc_info=True)
            return requested_servers
    
    def perform_final_authorization_check(
        self, 
        user_id: str, 
        servers: Set[str], 
        get_server_groups_func: Callable[[str], List[str]]
    ) -> List[str]:
        """
        Perform final authorization check on selected servers.
        
        This is a security measure to ensure servers that passed initial checks
        are still properly authorized.
        
        Args:
            user_id: User identifier
            servers: Set of server names to validate
            get_server_groups_func: Function to get required groups for a server
            
        Returns:
            List of finally validated server names
        """
        validated_servers = []
        
        for server_name in servers:
            try:
                required_groups = get_server_groups_func(server_name)
                
                if self.is_user_authorized_for_server(user_id, required_groups):
                    validated_servers.append(server_name)
                else:
                    logger.error(
                        f"SECURITY VIOLATION: Server {server_name} passed initial auth but failed final validation for user {user_id}",
                        exc_info=True
                    )
                    
            except Exception as e:
                logger.error(f"Error in final authorization check for server {server_name}: {e}", exc_info=True)
        
        logger.info(f"Final validated servers for user {user_id}: {validated_servers}")
        return validated_servers


def create_authorization_manager(auth_check_func: Callable[[str, str], bool]) -> AuthorizationManager:
    """
    Create an authorization manager with the provided auth check function.
    
    Args:
        auth_check_func: Function to check if user is in a group
        
    Returns:
        Configured AuthorizationManager instance
    """
    return AuthorizationManager(auth_check_func)
