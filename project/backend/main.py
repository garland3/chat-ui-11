"""FastAPI backend for Chat UI with MCP client functionality."""

import asyncio
import json
import logging
import os
import requests
from contextlib import asynccontextmanager
from typing import Dict, List, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
import yaml
from dotenv import load_dotenv

from middleware import AuthMiddleware
from mcp_client import MCPClient
from auth import is_user_in_group

# Load environment variables
load_dotenv()

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

# Global MCP client
mcp_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the application."""
    global mcp_client
    
    # Startup
    logger.info("Starting Chat UI backend")
    mcp_client = MCPClient()
    yield
    
    # Shutdown
    logger.info("Shutting down Chat UI backend")
    if mcp_client:
        await mcp_client.cleanup()


# Create FastAPI app
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
app = FastAPI(title="Chat UI Backend", lifespan=lifespan)

# Add middleware
app.add_middleware(AuthMiddleware, debug_mode=DEBUG_MODE)

# Serve static files
app.mount("/static", StaticFiles(directory="../frontend"), name="static")


def get_current_user(request: Request) -> str:
    """Get current user from request state."""
    return getattr(request.state, 'user_email', None)


async def call_llm(model_name: str, messages: List[Dict[str, str]]) -> str:
    """Call OpenAI-compliant LLM API using requests."""
    llm_config = load_llm_config()
    models = llm_config.get("models", {})
    
    if model_name not in models:
        raise ValueError(f"Model {model_name} not found in configuration")
    
    model_config = models[model_name]
    api_url = model_config["model_url"]
    api_key = os.path.expandvars(model_config["api_key"])  # Expand environment variables
    model_id = model_config["model_name"]
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_id,
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    try:
        # Use asyncio to run requests in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: requests.post(api_url, headers=headers, json=payload, timeout=30)
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            logger.error(f"LLM API error {response.status_code}: {response.text}")
            raise Exception(f"LLM API error: {response.status_code}")
            
    except requests.RequestException as e:
        logger.error(f"Request error calling LLM: {e}")
        raise Exception(f"Failed to call LLM: {str(e)}")
    except KeyError as e:
        logger.error(f"Invalid response format from LLM: {e}")
        raise Exception("Invalid response format from LLM")


def load_llm_config() -> Dict[str, Any]:
    """Load LLM configuration from YAML file."""
    config_paths = [
        "llmconfig.yml",           # Current directory (backend/)
        "../llmconfig.yml",        # Parent directory (project/)
        os.path.join(os.path.dirname(__file__), "..", "llmconfig.yml")  # Relative to script
    ]
    
    for config_path in config_paths:
        try:
            if os.path.exists(config_path):
                logger.info(f"Found LLM config at: {os.path.abspath(config_path)}")
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if config and isinstance(config, dict):
                        logger.info(f"Loaded {len(config.get('models', {}))} models from config")
                        return config
                    else:
                        logger.error(f"Invalid YAML format in {config_path}: expected dict, got {type(config)}")
                        return {}
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {config_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error reading {config_path}: {e}")
            continue
    
    logger.warning(f"llmconfig.yml not found in any of these locations: {config_paths}")
    logger.info("Create llmconfig.yml with your LLM configurations to enable model support")
    return {}


@app.get("/")
async def root():
    """Serve the main chat interface."""
    return RedirectResponse(url="/static/index.html")


@app.get("/auth")
async def auth_endpoint():
    """Authentication endpoint for redirect."""
    return {"message": "Please authenticate through reverse proxy"}


@app.get("/api/config")
async def get_config(current_user: str = Depends(get_current_user)):
    """Get available models, tools, and data sources for the user."""
    llm_config = load_llm_config()
    available_servers = mcp_client.get_available_servers()
    
    # Filter servers based on user permissions
    authorized_servers = []
    for server_name in available_servers:
        required_groups = mcp_client.get_server_groups(server_name)
        if not required_groups:  # No restrictions
            authorized_servers.append(server_name)
        else:
            # Check if user is in any required group
            for group in required_groups:
                if is_user_in_group(current_user, group):
                    authorized_servers.append(server_name)
                    break
    
    return {
        "app_name": os.getenv("APP_NAME", "Chat UI"),
        "models": list(llm_config.get("models", {}).keys()) if llm_config else [],
        "tools": authorized_servers,
        "user": current_user
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat communication."""
    # Check for authentication header during handshake
    check_header = not DEBUG_MODE
    if check_header and not websocket.headers.get("x-email-header"):
        await websocket.close(code=1008, reason="Authentication required")
        return
    
    # Get the user email (either from header or use test email for development)
    user_email = websocket.headers.get("x-email-header")
    if not user_email and not check_header:
        user_email = "test@test.com"  # Development fallback
    
    await websocket.accept()
    logger.info(f"WebSocket connection established for user: {user_email}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "chat":
                await handle_chat_message(websocket, message, user_email)
            elif message["type"] == "mcp_request":
                await handle_mcp_request(websocket, message, user_email)
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {message['type']}"
                }))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for user: {user_email}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_email}: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Internal server error"
        }))


async def handle_chat_message(websocket: WebSocket, message: Dict[str, Any], user_email: str):
    """Handle chat messages with LLM integration."""
    try:
        content = message.get('content', '')
        model_name = message.get('model', '')
        
        if not content:
            raise ValueError("Message content is required")
        
        if not model_name:
            raise ValueError("Model name is required")
        
        # Prepare messages for OpenAI-compliant API
        messages = [
            {"role": "user", "content": content}
        ]
        
        # Call the LLM
        logger.info(f"Calling LLM {model_name} for user {user_email}")
        llm_response = await call_llm(model_name, messages)
        
        # Send response back to client
        response = {
            "type": "chat_response",
            "message": llm_response,
            "model": model_name,
            "user": user_email
        }
        await websocket.send_text(json.dumps(response))
        logger.info(f"LLM response sent to user {user_email}")
        
    except ValueError as e:
        logger.error(f"Validation error in chat message: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e)
        }))
    except Exception as e:
        logger.error(f"Error handling chat message for user {user_email}: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Error processing chat message. Please try again."
        }))


async def handle_mcp_request(websocket: WebSocket, message: Dict[str, Any], user_email: str):
    """Handle MCP tool requests."""
    try:
        server_name = message.get("server")
        if not server_name:
            raise ValueError("Server name required")
        
        # Check authorization
        required_groups = mcp_client.get_server_groups(server_name)
        authorized = False
        
        if not required_groups:  # No restrictions
            authorized = True
        else:
            for group in required_groups:
                if is_user_in_group(user_email, group):
                    authorized = True
                    break
        
        if not authorized:
            raise HTTPException(status_code=403, detail="Not authorized for this MCP server")
        
        # Start server if not running
        await mcp_client.start_server(server_name)
        
        # Send request to MCP server
        mcp_request = message.get("request", {})
        response = await mcp_client.send_request(server_name, mcp_request)
        
        await websocket.send_text(json.dumps({
            "type": "mcp_response",
            "server": server_name,
            "response": response
        }))
        
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Error processing MCP request: {str(e)}"
        }))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)