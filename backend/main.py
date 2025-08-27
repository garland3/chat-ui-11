"""
Basic chat backend implementing the refactored architecture.
Phase 1A: LLM-only chat functionality.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from managers.app_factory.app_factory import app_factory
from routes.config_route import config_router  # Import the config router


# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def websocket_update_callback(websocket: WebSocket, message: dict):
    """
    Simple callback function to handle websocket updates.
    """
    try:
        logger.info(
            f"Sending websocket update: {message.get('type', 'unknown')} - {len(message.get('content', ''))} chars"
        )
        await websocket.send_json(message)
        logger.info("Websocket message sent successfully")
    except Exception as e:
        logger.error(f"Error sending websocket message: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Chat UI Backend (Phase 1A - LLM only)")
    await app_factory.initialize_managers()  # Initialize all managers
    yield
    logger.info("Shutting down Chat UI Backend")


# Create FastAPI app
app = FastAPI(
    title="Chat UI Backend",
    description="Basic chat backend with LLM-only functionality",
    version="2.0.0-phase1a",
    lifespan=lifespan,
)

# Include the config routes
app.include_router(config_router)

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
    Main chat WebSocket endpoint - Phase 1A: LLM-only chat.
    """
    await websocket.accept()
    session_id = uuid4()

    logger.info(f"WebSocket connection established for session {session_id}")

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "chat":
                # Phase 1A: Handle chat message using service coordinator
                try:
                    service_coordinator = await app_factory.get_service_coordinator()

                    response = await service_coordinator.handle_chat_message(
                        session_id=session_id,
                        content=data.get("content", ""),
                        model=data.get("model", "gpt-3.5-turbo"),
                        selected_tool_map=data.get("selected_tool_map"),
                        selected_prompt_map=data.get("selected_prompt_map"),
                        selected_data_sources=data.get("selected_data_sources"),
                        only_rag=data.get("only_rag", False),
                        tool_choice_required=data.get("tool_choice_required", False),
                        user_email=data.get("user"),
                        agent_mode=data.get("agent_mode", False),
                        agent_max_steps=data.get("agent_max_steps", 10),
                        temperature=data.get("temperature", 0.7),
                        update_callback=lambda message: websocket_update_callback(
                            websocket, message
                        ),
                        files=data.get("files"),
                    )
                    # Final response is sent via callback, but we keep this for compatibility
                except Exception as e:
                    logger.error(f"Error in chat handler: {e}", exc_info=True)
                    await websocket.send_json(
                        {"type": "error", "message": "An unexpected error occurred"}
                    )

            elif message_type == "download_file":
                # Handle file download
                service_coordinator = await app_factory.get_service_coordinator()
                response = await service_coordinator.handle_download_file(
                    session_id=session_id,
                    filename=data.get("filename", ""),
                    user_email=data.get("user"),
                )
                await websocket.send_json(response)

            elif message_type == "reset_session":
                # Handle session reset
                service_coordinator = await app_factory.get_service_coordinator()
                response = await service_coordinator.handle_reset_session(
                    session_id=session_id, user_email=data.get("user")
                )
                await websocket.send_json(response)

            else:
                logger.warning(f"Unknown message type: {message_type}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    }
                )

    except WebSocketDisconnect:
        service_coordinator = await app_factory.get_service_coordinator()
        service_coordinator.end_session(session_id)
        logger.info(f"WebSocket connection closed for session {session_id}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
