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
from pathlib import Path

from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from middleware import AuthMiddleware
from mcp_client import MCPToolManager
from auth import is_user_in_group
from session import SessionManager
from config import config_manager
from utils import get_current_user
from otel_config import setup_opentelemetry
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
from banner_client import initialize_banner_client, banner_router
from llm_health_check import health_checker, get_llm_health_status
from admin_routes import admin_router, setup_configfilesadmin
from feedback_routes import feedback_router
from files_routes import router as files_router
from config_routes import router as config_router
from mcp_health_check import mcp_health_monitor

mcp_manager: Optional[MCPToolManager] = None
session_manager: Optional[SessionManager] = None

# Load environment variables from the parent directory
load_dotenv(dotenv_path="../.env")

# Setup OpenTelemetry logging (replaces traditional logging setup)
otel_config = setup_opentelemetry("chat-ui-backend", "1.0.0")

# Initialize config first (needed for other initialization)
app_settings = config_manager.app_settings
DEBUG_MODE = app_settings.debug_mode

# Initialize RAG client after environment variables are loaded
initialize_rag_client()

# Initialize Banner client after environment variables are loaded
initialize_banner_client()

logger = logging.getLogger(__name__)

# --- NEW: Session and Callback System ---



# --- FastAPI Lifecycle and App Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the application."""
    global mcp_manager, session_manager
    
    # Startup
    logger.info("Starting Chat UI backend")
    
    # Setup admin configuration directory
    setup_configfilesadmin()
    
    mcp_manager = MCPToolManager()
    await mcp_manager.initialize_clients()
    await mcp_manager.discover_tools()
    await mcp_manager.discover_prompts()
    
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
    
    # Start LLM health checks
    await health_checker.start_periodic_checks()
    
    # Start MCP health monitoring
    mcp_check_interval = app_settings.mcp_health_check_interval
    mcp_health_monitor.update_check_interval(mcp_check_interval)
    await mcp_health_monitor.start_periodic_monitoring(mcp_manager)
    
    logger.info("All callbacks registered successfully")
    yield
    
    # Shutdown
    logger.info("Shutting down Chat UI backend")
    await health_checker.stop_periodic_checks()
    await mcp_health_monitor.stop_periodic_monitoring()
    if mcp_manager:
        await mcp_manager.cleanup()


# Create FastAPI app (config already initialized above)
app = FastAPI(title=app_settings.app_name, lifespan=lifespan)

# Instrument FastAPI with OpenTelemetry
otel_config.instrument_fastapi(app)
otel_config.instrument_httpx()

# Add middleware
app.add_middleware(AuthMiddleware, debug_mode=DEBUG_MODE)

# Serve admin frontend (before admin API router)
@app.get("/admin")
async def admin_frontend():
    if frontend_dist.exists():
        return FileResponse(frontend_dist / "index.html")
    raise HTTPException(404)

# Include routers
app.include_router(admin_router)
app.include_router(feedback_router)
app.include_router(files_router)
app.include_router(config_router)
app.include_router(banner_router)

USE_NEW_FRONTEND = os.getenv("USE_NEW_FRONTEND", "false").lower() == "true"
print(f"USE_NEW_FRONTEND: {USE_NEW_FRONTEND}")

# Serve static files (only if frontend is built) - moved to after routes
if USE_NEW_FRONTEND:
    frontend_dist = Path("../frontend3/dist")
else:
    frontend_dist = Path("../frontend/dist")

print(f"Frontend dist path: {frontend_dist}")

if frontend_dist.exists():
    app.mount("/static", StaticFiles(directory=frontend_dist), name="static")
else:
    logger.warning(f"Frontend dist directory not found at {frontend_dist}. Skipping static file mounting.")
# app.mount("/vendor", StaticFiles(directory="../_old_frontend/vendor"), name="vendor")
# app.mount("/fonts", StaticFiles(directory="../_old_frontend/fonts"), name="fonts")

# --- API Endpoints ---


@app.get("/auth")
async def auth_endpoint():
    """Authentication endpoint for redirect."""
    return {"message": "Please authenticate through reverse proxy"}





@app.get("/healthz")
async def health_check():
    return {"status": "ok"}


@app.get("/api/llm-health")
async def get_llm_health(current_user: str = Depends(get_current_user)):
    """Get the current LLM health status."""
    return await get_llm_health_status()


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
    user_email = websocket.headers.get("X-User-Email")
    
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
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="root")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=app_settings.port, reload=True)
