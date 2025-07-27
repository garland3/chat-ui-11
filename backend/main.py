"""FastAPI backend for Chat UI with MCP client functionality.

CALLBACK SYSTEM:
================
This backend uses an event-driven callback system that allows for highly customizable behavior.
Callbacks can be registered for various events in the chat session lifecycle.

Callback Signature:
    async def my_callback(session: ChatSession, **kwargs) -> None:
        # Access and modify session state
        session.messages.append(...)
        session.model_name = "different-model"
        session.selected_tools = ["new_tool"]
        # etc.

Available Events:
    - session_started: When a new WebSocket connection begins
    - session_ended: When a WebSocket connection closes
    - session_error: When an error occurs in the session
    - before_message_processing: Before processing any incoming message
    - before_user_message_added: Before adding user message to history
    - after_user_message_added: After adding user message to history
    - before_validation: Before validating selected tools
    - after_validation: After validating selected tools
    - before_llm_call: Before calling the LLM
    - after_llm_call: After receiving LLM response
    - after_assistant_message_added: After adding assistant message to history
    - before_response_send: Before sending response to client
    - after_response_send: After sending response to client
    - message_error: When an error occurs processing a message

Example Usage:
    async def my_custom_callback(session: ChatSession, **kwargs) -> None:
        logger.info(f"Processing message for {session.user_email}")
        if len(session.messages) > 10:
            session.messages = session.messages[-5:]  # Keep only last 5
    
    session_manager.register_callback("before_llm_call", my_custom_callback)
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from middleware import AuthMiddleware
from mcp_client import MCPToolManager
from auth import is_user_in_group
from session import SessionManager
from config import config_manager
from utils import get_current_user
from callbacks import (
    log_session_events_callback,
    log_llm_call_callback,
    message_history_limit_callback,
    security_audit_callback,
    authorization_audit_callback,
    modify_user_message_callback,
    dynamic_model_selection_callback,
    conversation_context_callback,
)
import rag_client
from rag_client import initialize_rag_client
import banner_client
from banner_client import initialize_banner_client

mcp_manager: Optional[MCPToolManager] = None
session_manager: Optional[SessionManager] = None

# Load environment variables from the parent directory
load_dotenv(dotenv_path="../.env")

# Initialize RAG client after environment variables are loaded
initialize_rag_client()

# Initialize Banner client after environment variables are loaded
initialize_banner_client()

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# --- NEW: Session and Callback System ---



# --- FastAPI Lifecycle and App Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the application."""
    global mcp_manager, session_manager
    
    # Startup
    logger.info("Starting Chat UI backend")
    mcp_manager = MCPToolManager()
    await mcp_manager.initialize_clients()
    await mcp_manager.discover_tools()
    
    session_manager = SessionManager(mcp_manager)
    
    # Register callbacks here
    session_manager.register_callback("session_started", log_session_events_callback)
    session_manager.register_callback("session_ended", log_session_events_callback)
    session_manager.register_callback("before_llm_call", log_llm_call_callback)
    session_manager.register_callback("before_llm_call", message_history_limit_callback)
    session_manager.register_callback("before_message_processing", security_audit_callback)
    session_manager.register_callback("before_message_processing", dynamic_model_selection_callback)
    session_manager.register_callback("before_user_message_added", modify_user_message_callback)
    session_manager.register_callback("after_user_message_added", conversation_context_callback)
    session_manager.register_callback("after_validation", authorization_audit_callback)
    
    logger.info("All callbacks registered successfully")
    yield
    
    # Shutdown
    logger.info("Shutting down Chat UI backend")
    if mcp_manager:
        await mcp_manager.cleanup()


# Create FastAPI app
app_settings = config_manager.app_settings
DEBUG_MODE = app_settings.debug_mode
app = FastAPI(title=app_settings.app_name, lifespan=lifespan)

# Add middleware
app.add_middleware(AuthMiddleware, debug_mode=DEBUG_MODE)

# Serve static files
app.mount("/static", StaticFiles(directory="../frontend/dist"), name="static")
app.mount("/vendor", StaticFiles(directory="../old_frontend/vendor"), name="vendor")
app.mount("/fonts", StaticFiles(directory="../old_frontend/fonts"), name="fonts")

# --- API Endpoints ---


@app.get("/auth")
async def auth_endpoint():
    """Authentication endpoint for redirect."""
    return {"message": "Please authenticate through reverse proxy"}


@app.get("/api/banners")
async def get_banners(current_user: str = Depends(get_current_user)):
    """Get banner messages for display at the top of the UI."""
    if not banner_client.banner_client:
        return {"messages": []}
    
    try:
        messages = await banner_client.banner_client.get_banner_messages()
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Error fetching banner messages: {e}", exc_info=True)
        return {"messages": []}


@app.get("/api/config")
async def get_config(current_user: str = Depends(get_current_user)):
    """Get available models, tools, and data sources for the user.
    Only returns MCP servers and tools that the user is authorized to access.
    """
    llm_config = config_manager.llm_config
    
    # Get RAG data sources for the user
    rag_data_sources = await rag_client.rag_client.discover_data_sources(current_user)
    
    # Get authorized servers for the user - this filters out unauthorized servers completely
    authorized_servers = mcp_manager.get_authorized_servers(current_user, is_user_in_group)
    
    # Add canvas pseudo-tool to authorized servers (available to all users)
    authorized_servers.append("canvas")
    
    # Only build tool information for servers the user is authorized to access
    tools_info = []
    for server_name in authorized_servers:
        # Handle canvas pseudo-tool
        if server_name == "canvas":
            tools_info.append({
                'server': 'canvas',
                'tools': ['canvas'],
                'tool_count': 1,
                'description': 'Canvas for showing final rendered content: complete code, reports, and polished documents. Use this to finalize your work. Most code and reports will be shown here.',
                'is_exclusive': False
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
                    'is_exclusive': server_config.get('is_exclusive', False)
                })
    
    # Log what the user can see for debugging
    logger.info(f"User {current_user} has access to {len(authorized_servers)} servers: {authorized_servers}")
    logger.info(f"Returning {len(tools_info)} server tool groups to frontend for user {current_user}")
    
    return {
        "app_name": app_settings.app_name,
        "models": list(llm_config.models.keys()),
        "tools": tools_info,  # Only authorized servers are included
        "data_sources": rag_data_sources,  # RAG data sources for the user
        "user": current_user,
        "active_sessions": session_manager.get_session_count() if session_manager else 0,
        "authorized_servers": authorized_servers,  # Optional: expose for debugging
        "agent_mode_available": app_settings.agent_mode_available,  # Whether agent mode UI should be shown
        "banner_enabled": app_settings.banner_enabled  # Whether banner system is enabled
    }


@app.get("/api/sessions")
async def get_session_info(current_user: str = Depends(get_current_user)):
    """Get session information for the current user."""
    if not session_manager:
        return {"error": "Session manager not initialized"}
    
    user_sessions = session_manager.get_sessions_for_user(current_user)
    return {
        "total_sessions": session_manager.get_session_count(),
        "user_sessions": len(user_sessions),
        "session_ids": [session.session_id for session in user_sessions]
    }


@app.get("/api/debug/servers")
async def get_server_debug_info(current_user: str = Depends(get_current_user)):
    """Get detailed server authorization information for debugging.
    Only available in DEBUG mode.
    """
    if not DEBUG_MODE:
        raise HTTPException(status_code=404, detail="Not found")
    
    if not mcp_manager:
        return {"error": "MCP manager not initialized"}
    
    all_servers = mcp_manager.get_available_servers()
    authorized_servers = mcp_manager.get_authorized_servers(current_user, is_user_in_group)
    
    server_details = {}
    for server_name in all_servers:
        required_groups = mcp_manager.get_server_groups(server_name)
        is_authorized = server_name in authorized_servers
        is_exclusive = mcp_manager.is_server_exclusive(server_name)
        
        # Check which groups the user is in (for this server)
        user_groups = []
        for group in required_groups:
            if is_user_in_group(current_user, group):
                user_groups.append(group)
        
        server_details[server_name] = {
            "authorized": is_authorized,
            "required_groups": required_groups,
            "user_groups": user_groups,
            "is_exclusive": is_exclusive,
            "tool_count": len(mcp_manager.available_tools.get(server_name, {}).get('tools', []))
        }
    
    return {
        "user": current_user,
        "all_servers": all_servers,
        "authorized_servers": authorized_servers,
        "server_details": server_details,
        "debug_mode": DEBUG_MODE
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint now delegates connection handling to the SessionManager."""
    check_header = not DEBUG_MODE
    user_email = websocket.headers.get("x-email-header")
    
    if check_header and not user_email:
        await websocket.close(code=1008, reason="Authentication required")
        return
        
    if not user_email and not check_header:
        user_email = "test@test.com"

    # The endpoint's job is now much simpler
    try:
        await session_manager.connect(websocket, user_email)
    finally:
        session_manager.disconnect(websocket)


# Mount frontend files at root for direct serving (must be last to avoid conflicts)
app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="root")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=app_settings.port, reload=True)
