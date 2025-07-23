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
from mcp_client import MCPToolManager
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

# Global MCP tool manager
mcp_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the application."""
    global mcp_manager
    
    # Startup
    logger.info("Starting Chat UI backend")
    mcp_manager = MCPToolManager()
    await mcp_manager.initialize_clients()
    await mcp_manager.discover_tools()
    yield
    
    # Shutdown
    logger.info("Shutting down Chat UI backend")
    if mcp_manager:
        await mcp_manager.cleanup()


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


async def validate_selected_tools(selected_tools: List[str], user_email: str) -> List[Dict[str, str]]:
    """Validate selected tools and return validated server names."""
    validated_servers = []
    
    # Parse tool keys to extract server names
    server_names = set()
    for tool_key in selected_tools:
        parts = tool_key.split('_', 1)
        if len(parts) == 2:
            server_name = parts[0]
            server_names.add(server_name)
    
    # Check for exclusive servers
    exclusive_servers = []
    regular_servers = []
    
    for server_name in server_names:
        if mcp_manager.is_server_exclusive(server_name):
            exclusive_servers.append(server_name)
        else:
            regular_servers.append(server_name)
    
    # If exclusive servers are selected, only use the first exclusive server
    if exclusive_servers:
        if len(exclusive_servers) > 1:
            logger.warning(f"Multiple exclusive servers selected, using only {exclusive_servers[0]}")
        server_names = {exclusive_servers[0]}  # Only use first exclusive server
        logger.info(f"Exclusive mode enabled for server: {exclusive_servers[0]}")
    else:
        server_names = set(regular_servers)
    
    # Validate user permissions for each server
    for server_name in server_names:
        required_groups = mcp_manager.get_server_groups(server_name)
        authorized = False
        
        if not required_groups:  # No restrictions
            authorized = True
        else:
            for group in required_groups:
                if is_user_in_group(user_email, group):
                    authorized = True
                    break
        
        if authorized:
            validated_servers.append(server_name)
        else:
            logger.warning(f"User {user_email} not authorized for server {server_name}")
    
    return validated_servers


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


async def call_llm_with_tools(model_name: str, messages: List[Dict[str, str]], validated_servers: List[str], user_email: str, websocket: WebSocket) -> str:
    """Call LLM with tool calling support."""
    if not validated_servers:
        # No tools selected, use regular LLM call
        return await call_llm(model_name, messages)
    
    # Get tools schema for selected servers
    tools_data = mcp_manager.get_tools_for_servers(validated_servers)
    tools_schema = tools_data['tools']
    tool_mapping = tools_data['mapping']
    
    if not tools_schema:
        # No tools available, use regular LLM call
        return await call_llm(model_name, messages)
    
    llm_config = load_llm_config()
    models = llm_config.get("models", {})
    
    if model_name not in models:
        raise ValueError(f"Model {model_name} not found in configuration")
    
    model_config = models[model_name]
    api_url = model_config["model_url"]
    api_key = os.path.expandvars(model_config["api_key"])
    model_id = model_config["model_name"]
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Check if any server is exclusive (force tool calling)
    is_exclusive_mode = any(mcp_manager.is_server_exclusive(server) for server in validated_servers)
    tool_choice = "required" if is_exclusive_mode else "auto"
    
    payload = {
        "model": model_id,
        "messages": messages,
        "tools": tools_schema,
        "tool_choice": tool_choice,
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: requests.post(api_url, headers=headers, json=payload, timeout=30)
        )
        
        if response.status_code == 200:
            result = response.json()
            choice = result["choices"][0]
            message = choice["message"]
            
            # Check if LLM wants to call tools
            if message.get("tool_calls"):
                tool_results = []
                for tool_call in message["tool_calls"]:
                    function_name = tool_call["function"]["name"]
                    function_args = json.loads(tool_call["function"]["arguments"])
                    
                    if function_name in tool_mapping:
                        mapping = tool_mapping[function_name]
                        server_name = mapping['server']
                        tool_name = mapping['tool_name']
                        
                        try:
                            # Execute the tool
                            logger.info(f"Executing tool {tool_name} on server {server_name} for user {user_email}")
                            tool_result = await mcp_manager.call_tool(server_name, tool_name, function_args)
                            
                            # Handle FastMCP CallToolResult object
                            if hasattr(tool_result, 'content'):
                                # Extract content from CallToolResult
                                if hasattr(tool_result.content, '__iter__') and not isinstance(tool_result.content, str):
                                    # If content is a list of text blocks
                                    content_text = '\n'.join([block.text if hasattr(block, 'text') else str(block) for block in tool_result.content])
                                else:
                                    content_text = str(tool_result.content)
                            else:
                                # Fallback: convert entire result to string
                                content_text = str(tool_result)
                            
                            tool_results.append({
                                "tool_call_id": tool_call["id"],
                                "role": "tool",
                                "content": content_text
                            })
                            
                        except Exception as e:
                            logger.error(f"Error executing tool {tool_name}: {e}")
                            # print the traceback for debugging
                            import traceback
                            logger.error(traceback.format_exc())
                            tool_results.append({
                                "tool_call_id": tool_call["id"],
                                "role": "tool",
                                "content": json.dumps({"error": f"Tool execution failed: {str(e)}"})
                            })
                
                # Send tool results back to LLM for final response
                if tool_results:
                    # Add assistant's tool call message
                    follow_up_messages = messages + [message] + tool_results
                    
                    follow_up_payload = {
                        "model": model_id,
                        "messages": follow_up_messages,
                        "max_tokens": 1000,
                        "temperature": 0.7
                    }
                    
                    follow_up_response = await loop.run_in_executor(
                        None,
                        lambda: requests.post(api_url, headers=headers, json=follow_up_payload, timeout=30)
                    )
                    
                    if follow_up_response.status_code == 200:
                        follow_up_result = follow_up_response.json()
                        return follow_up_result["choices"][0]["message"]["content"]
                    else:
                        logger.error(f"Follow-up LLM call failed: {follow_up_response.status_code}")
                        return message.get("content", "Tool execution completed but failed to generate response.")
            
            return message.get("content", "")
        else:
            logger.error(f"LLM API error {response.status_code}: {response.text}")
            raise Exception(f"LLM API error: {response.status_code}")
            
    except requests.RequestException as e:
        logger.error(f"Request error calling LLM with tools: {e}")
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
    
    # Get authorized servers for the user
    authorized_servers = mcp_manager.get_authorized_servers(current_user, is_user_in_group)
    
    # Get detailed tool information for authorized servers
    tools_info = []
    for server_name in authorized_servers:
        if server_name in mcp_manager.available_tools:
            server_tools = mcp_manager.available_tools[server_name]['tools']
            server_config = mcp_manager.available_tools[server_name]['config']
            
            tools_info.append({
                'server': server_name,
                'tools': [tool.name for tool in server_tools],
                'tool_count': len(server_tools),
                'description': server_config.get('description', f'{server_name} tools'),
                'is_exclusive': server_config.get('is_exclusive', False)
            })
    
    return {
        "app_name": os.getenv("APP_NAME", "Chat UI"),
        "models": list(llm_config.get("models", {}).keys()) if llm_config else [],
        "tools": tools_info,
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
    """Handle chat messages with LLM integration and tool calling."""
    try:
        content = message.get('content', '')
        model_name = message.get('model', '')
        selected_tools = message.get('selected_tools', [])
        # print the first few words of the content, the model, names of tools
        logger.info(f"Received chat message from {user_email}: content='{content[:50]}...', model='{model_name}', tools={selected_tools}")
        
        if not content:
            raise ValueError("Message content is required")
        
        if not model_name:
            raise ValueError("Model name is required")
        
        # Validate selected tools and user permissions
        validated_tools = await validate_selected_tools(selected_tools, user_email)
        
        # Prepare messages for OpenAI-compliant API
        messages = [
            {"role": "user", "content": content}
        ]
        
        # Call the LLM with tools if any are selected
        logger.info(f"Calling LLM {model_name} for user {user_email} with {len(validated_tools)} tools")
        llm_response = await call_llm_with_tools(model_name, messages, validated_tools, user_email, websocket)
        
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




if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)