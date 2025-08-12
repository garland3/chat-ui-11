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
from core.orchestrator import orchestrator
# from core.session import session_manager
from core.middleware import AuthMiddleware
from core.otel_config import setup_opentelemetry

# Import routes
from core.admin_routes import admin_router
from core.config_routes import router as config_router
from core.feedback_routes import feedback_router
from core.files_routes import router as files_router

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
    config = orchestrator.get_config_manager()
    # app_settings = config.app_settings
    
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

# Add middleware
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(admin_router)
app.include_router(config_router)
app.include_router(feedback_router)
app.include_router(files_router)

# Serve static files
static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    @app.get("/")
    async def read_root():
        return FileResponse(str(static_dir / "index.html"))

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
        session_manager.end_session(session.session_id)
        logger.info(f"WebSocket connection closed for session {session.session_id}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)