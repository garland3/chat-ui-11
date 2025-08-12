"""Configuration API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends

from core.auth import is_user_in_group
from config import config_manager
from utils import get_current_user
import rag_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config")
async def get_config(current_user: str = Depends(get_current_user)):
    """Get available models, tools, and data sources for the user.
    Only returns MCP servers and tools that the user is authorized to access.
    """
    from main import mcp_manager, session_manager
    
    llm_config = config_manager.llm_config
    app_settings = config_manager.app_settings
    
    # Get RAG data sources for the user
    rag_data_sources = await rag_client.rag_client.discover_data_sources(current_user)
    
    # Get authorized servers for the user - this filters out unauthorized servers completely
    authorized_servers = mcp_manager.get_authorized_servers(current_user, is_user_in_group)
    
    # Add canvas pseudo-tool to authorized servers (available to all users)
    authorized_servers.append("canvas")
    
    # Only build tool information for servers the user is authorized to access
    tools_info = []
    prompts_info = []
    for server_name in authorized_servers:
        # Handle canvas pseudo-tool
        if server_name == "canvas":
            tools_info.append({
                'server': 'canvas',
                'tools': ['canvas'],
                'tool_count': 1,
                'description': 'Canvas for showing final rendered content: complete code, reports, and polished documents. Use this to finalize your work. Most code and reports will be shown here.',
                'is_exclusive': False,
                'author': 'Chat UI Team',
                'short_description': 'Visual content display',
                'help_email': 'support@chatui.example.com'
            })
        elif server_name in mcp_manager.available_tools:
            server_tools = mcp_manager.available_tools[server_name]['tools']
            server_config = mcp_manager.available_tools[server_name]['config']
            
            # Only include servers that have tools and user has access to
            if server_tools:  # Only show servers with actual tools
                tools_info.append({
                    'server': server_name,
                    'tools': [tool.name for tool in server_tools],
                    'tool_count': len(server_tools),
                    'description': server_config.get('description', f'{server_name} tools'),
                    'is_exclusive': server_config.get('is_exclusive', False),
                    'author': server_config.get('author', 'Unknown'),
                    'short_description': server_config.get('short_description', server_config.get('description', f'{server_name} tools')),
                    'help_email': server_config.get('help_email', '')
                })
        
        # Collect prompts from this server if available
        if server_name in mcp_manager.available_prompts:
            server_prompts = mcp_manager.available_prompts[server_name]['prompts']
            server_config = mcp_manager.available_prompts[server_name]['config']
            if server_prompts:  # Only show servers with actual prompts
                prompts_info.append({
                    'server': server_name,
                    'prompts': [{'name': prompt.name, 'description': prompt.description} for prompt in server_prompts],
                    'prompt_count': len(server_prompts),
                    'description': f'{server_name} custom prompts',
                    'author': server_config.get('author', 'Unknown'),
                    'short_description': server_config.get('short_description', f'{server_name} custom prompts'),
                    'help_email': server_config.get('help_email', '')
                })
    
    # Read help page configuration
    help_config = {}
    try:
        import json
        with open("configfiles/help-config.json", "r", encoding="utf-8") as f:
            help_config = json.load(f)
    except Exception as e:
        logger.warning(f"Could not read configfiles/help-config.json: {e}")
        help_config = {"title": "Help & Documentation", "sections": []}
    
# Log what the user can see for debugging
    logger.info(
        f"User {current_user} has access to {len(authorized_servers)} servers: {authorized_servers}\n"
        f"Returning {len(tools_info)} server tool groups to frontend for user {current_user}"
    )
    
    return {
        "app_name": app_settings.app_name,
        "models": list(llm_config.models.keys()),
        "tools": tools_info,  # Only authorized servers are included
        "prompts": prompts_info,  # Available prompts from authorized servers
        "data_sources": rag_data_sources,  # RAG data sources for the user
        "user": current_user,
    "is_in_admin_group": is_user_in_group(current_user, app_settings.admin_group),
        "active_sessions": session_manager.get_session_count() if session_manager else 0,
        "authorized_servers": authorized_servers,  # Optional: expose for debugging
        "agent_mode_available": app_settings.agent_mode_available,  # Whether agent mode UI should be shown
        "banner_enabled": app_settings.banner_enabled,  # Whether banner system is enabled
        "help_config": help_config,  # Help page configuration from help-config.json
        "features": {
            "workspaces": app_settings.feature_workspaces_enabled,
            "rag": app_settings.feature_rag_enabled,
            "tools": app_settings.feature_tools_enabled,
            "marketplace": app_settings.feature_marketplace_enabled,
            "files_panel": app_settings.feature_files_panel_enabled,
            "chat_history": app_settings.feature_chat_history_enabled
        }
    }


@router.get("/sessions")
async def get_session_info(current_user: str = Depends(get_current_user)):
    """Get session information for the current user."""
    from main import session_manager
    
    if not session_manager:
        return {"error": "Session manager not initialized"}
    
    user_sessions = session_manager.get_sessions_for_user(current_user)
    return {
        "total_sessions": session_manager.get_session_count(),
        "user_sessions": len(user_sessions),
        "sessions": [
            {
                "id": session.id,
                "user": session.user_email,
                "messages": len(session.messages),
                "model": session.model_name,
                "tools": session.selected_tools
            } for session in user_sessions
        ]
    }
