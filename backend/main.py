"""
Refactored FastAPI backend using the new modular architecture.

This is a simplified main.py that uses the orchestrator pattern
from Phase 1 of the refactoring plan.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Import from core (glue layer)
from core.chat_session import ChatSession
from core.middleware import AuthMiddleware
from core.otel_config import setup_opentelemetry

# Import from infrastructure
from infrastructure.app_factory import app_factory

# Import routes
from routes.admin_routes import admin_router
from routes.config_routes import router as config_router
from routes.feedback_routes import feedback_router
from routes.files_routes import router as files_router

# Load environment variables from the parent directory
load_dotenv(dotenv_path="../.env")

# Setup OpenTelemetry logging
otel_config = setup_opentelemetry("chat-ui-backend", "1.0.0")

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Chat UI Backend with modular architecture")
    
    # Initialize configuration
    config = app_factory.get_config_manager()
    
    logger.info(f"Backend initialized with {len(config.llm_config.models)} LLM models")
    logger.info(f"MCP servers configured: {len(config.mcp_config.servers)}")
    
    yield
    
    logger.info("Shutting down Chat UI Backend")


# Create FastAPI app with minimal setup
app = FastAPI(
    title="Chat UI Backend",
    description="Modular chat backend with MCP integration", 
    version="2.0.0",
    lifespan=lifespan,
)

# Get config for middleware
config = app_factory.get_config_manager()

# Add middleware
app.add_middleware(AuthMiddleware, debug_mode=config.app_settings.debug_mode)

# Include routers
app.include_router(admin_router)
app.include_router(config_router)
app.include_router(feedback_router)
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
    Main chat WebSocket endpoint.
    """
    await websocket.accept()
    ## get a uuid
    session = ChatSession(uuid=uuid4(), websocket=websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await session.handle_message(data)
    except WebSocketDisconnect:
        await session.end_session()
        logger.info(f"WebSocket connection closed for session {session.session_id}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
