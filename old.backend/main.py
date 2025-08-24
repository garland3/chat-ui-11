"""
Basic chat backend implementing the modular architecture.
Focuses on essential chat functionality only.

Developer note:
- For stepping through a single chat flow with specific tools in a debugger,
    you can run the helper script:
        scripts/invoke_chat_with_tools.py
    which calls ChatService.handle_chat_message with a prompt and tools
    similar to how this module does inside the WebSocket handler.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Import domain errors
from domain.errors import ValidationError

# Import from core (only essential middleware and config)
from core.middleware import AuthMiddleware
from core.rate_limit_middleware import RateLimitMiddleware
from core.security_headers_middleware import SecurityHeadersMiddleware
from core.otel_config import setup_opentelemetry

# Import from infrastructure
from infrastructure.app_factory import app_factory
from infrastructure.transport.websocket_connection_adapter import WebSocketConnectionAdapter

# Import essential routes
from routes.config_routes import router as config_router
from routes.admin_routes import admin_router
from routes.files_routes import router as files_router

# Load environment variables from the parent directory
load_dotenv(dotenv_path="../.env")

# Setup OpenTelemetry logging
otel_config = setup_opentelemetry("chat-ui-backend", "1.0.0")

logger = logging.getLogger(__name__)


async def websocket_update_callback(websocket: WebSocket, message: dict):
    """
    Callback function to handle websocket updates with enhanced logging.
    """
    try:
        mtype = message.get("type")
        
        # Create truncated version for debug logging
        truncated_msg = {}
        for k, v in message.items():
            if k == "content" and isinstance(v, str) and len(v) > 100:
                truncated_msg[k] = v[:100] + "..."
            elif isinstance(v, str) and len(v) > 100:
                truncated_msg[k] = v[:100] + "..."
            elif isinstance(v, dict):
                # Truncate nested dict content
                truncated_v = {}
                for nk, nv in v.items():
                    if isinstance(nv, str) and len(nv) > 50:
                        truncated_v[nk] = nv[:50] + "..."
                    else:
                        truncated_v[nk] = nv
                truncated_msg[k] = truncated_v
            else:
                truncated_msg[k] = v
        
        # Log UI update with message type and size
        message_size = len(str(message))
        logger.info("UI_UPDATE: type=%s, size=%d", mtype, message_size)
        logger.debug("UI_UPDATE_DATA: %s", truncated_msg)
        
        # Type-specific logging (moved to DEBUG)
        if mtype == "intermediate_update":
            utype = message.get("update_type") or message.get("data", {}).get("update_type")
            if utype == "canvas_files":
                files = (message.get("data") or {}).get("files") or []
                logger.debug(
                    "Canvas files update: count=%d files=%s display=%s",
                    len(files),
                    [f.get("filename") for f in files if isinstance(f, dict)],
                    (message.get("data") or {}).get("display"),
                )
            elif utype == "files_update":
                files = (message.get("data") or {}).get("files") or []
                logger.debug("Files update: total=%d", len(files))
            else:
                logger.debug("Intermediate update type: %s", utype)
        elif mtype == "canvas_content":
            content = message.get("content")
            clen = len(content) if isinstance(content, str) else "obj"
            logger.debug("Canvas content length: %s", clen)
        elif mtype == "agent_update":
            update_type = message.get("update_type")
            logger.debug("Agent update type: %s", update_type)
        elif mtype == "tool_start":
            tool_name = message.get("tool_name")
            logger.debug("Tool start: %s", tool_name)
        elif mtype == "tool_complete":
            tool_name = message.get("tool_name")
            logger.debug("Tool complete: %s", tool_name)
            
    except Exception as e:
        # Non-fatal logging error; continue to send
        logger.debug("Error in websocket update logging: %s", e)
    
    await websocket.send_json(message)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Chat UI Backend with modular architecture")
    
    # Initialize configuration
    config = app_factory.get_config_manager()
    
    logger.info(f"Backend initialized with {len(config.llm_config.models)} LLM models")
    logger.info(f"MCP servers configured: {len(config.mcp_config.servers)}")
    
    # Initialize MCP tools manager
    logger.info("Initializing MCP tools manager...")
    mcp_manager = app_factory.get_mcp_manager()
    
    try:
        logger.info("Step 1: Initializing MCP clients...")
        await mcp_manager.initialize_clients()
        logger.info("Step 1 complete: MCP clients initialized")
        
        logger.info("Step 2: Discovering tools...")
        await mcp_manager.discover_tools()
        logger.info("Step 2 complete: Tool discovery finished")
        
        logger.info("Step 3: Discovering prompts...")
        await mcp_manager.discover_prompts()
        logger.info("Step 3 complete: Prompt discovery finished")
        
        logger.info("MCP tools manager initialization complete")
    except Exception as e:
        logger.error(f"Error during MCP initialization: {e}", exc_info=True)
        # Continue startup even if MCP fails
        logger.warning("Continuing startup without MCP tools")
    
    yield
    
    logger.info("Shutting down Chat UI Backend")
    # Cleanup MCP clients
    await mcp_manager.cleanup()


# Create FastAPI app with minimal setup
app = FastAPI(
    title="Chat UI Backend",
    description="Basic chat backend with modular architecture", 
    version="2.0.0",
    lifespan=lifespan,
)

# Get config for middleware
config = app_factory.get_config_manager()

"""Security: enforce rate limiting and auth middleware.
RateLimit first to cheaply throttle abusive traffic before heavier logic.
"""
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware, debug_mode=config.app_settings.debug_mode)

# Include essential routes (add files API)
app.include_router(config_router)
app.include_router(admin_router)
app.include_router(files_router)

# Serve frontend build (Vite)
static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if static_dir.exists():
    # Serve the SPA entry
    @app.get("/")
    async def read_root():
        return FileResponse(str(static_dir / "index.html"))

    # Serve hashed asset files under /assets (CSS/JS/images from Vite build)
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # Common top-level static files in the Vite build
    @app.get("/favicon.ico")
    async def favicon():
        path = static_dir / "favicon.ico"
        return FileResponse(str(path))

    @app.get("/vite.svg")
    async def vite_svg():
        path = static_dir / "vite.svg"
        return FileResponse(str(path))

    @app.get("/logo.png")
    async def logo_png():
        path = static_dir / "logo.png"
        return FileResponse(str(path))

# WebSocket endpoint for chat
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main chat WebSocket endpoint using new architecture.
    """
    await websocket.accept()
    session_id = uuid4()
    
    # Create connection adapter and chat service
    connection_adapter = WebSocketConnectionAdapter(websocket)
    chat_service = app_factory.create_chat_service(connection_adapter)
    
    logger.info(f"WebSocket connection established for session {session_id}")
    
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "chat":
                # Handle chat message with streaming updates
                try:
                    response = await chat_service.handle_chat_message(
                        session_id=session_id,
                        content=data.get("content", ""),
                        model=data.get("model", ""),
                        selected_tools=data.get("selected_tools"),
                        selected_prompts=data.get("selected_prompts"),
                        selected_data_sources=data.get("selected_data_sources"),
                        only_rag=data.get("only_rag", False),
                        tool_choice_required=data.get("tool_choice_required", False),
                        user_email=data.get("user"),
                        agent_mode=data.get("agent_mode", False),
                        agent_max_steps=data.get("agent_max_steps", 10),
                        temperature=data.get("temperature", 0.7),
                        update_callback=lambda message: websocket_update_callback(websocket, message),
                        files=data.get("files")
                    )
                    # Final response is already sent via callbacks, but we keep this for backward compatibility
                except ValidationError as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                except Exception as e:
                    logger.error(f"Error in chat handler: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": "An unexpected error occurred"
                    })
                
            elif message_type == "download_file":
                # Handle file download
                response = await chat_service.handle_download_file(
                    session_id=session_id,
                    filename=data.get("filename", ""),
                    user_email=data.get("user")
                )
                await websocket.send_json(response)
            
            elif message_type == "reset_session":
                # Handle session reset
                response = await chat_service.handle_reset_session(
                    session_id=session_id,
                    user_email=data.get("user")
                )
                await websocket.send_json(response)
                
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
                
    except WebSocketDisconnect:
        chat_service.end_session(session_id)
        logger.info(f"WebSocket connection closed for session {session_id}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
