"""FastAPI backend for Chat UI with MCP client functionality."""

import asyncio
import json
import logging
import os
import requests
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Callable, Awaitable, Optional
from collections import defaultdict

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

# --- NEW: Session and Callback System ---

class ChatSession:
    """Manages the state and logic for a single WebSocket connection."""
    def __init__(self, websocket: WebSocket, user_email: str, mcp_manager: MCPToolManager, callbacks: Dict[str, List[Callable]]):
        self.websocket = websocket
        self.user_email = user_email
        self.mcp_manager = mcp_manager
        self._callbacks = callbacks
        self.messages: List[Dict[str, Any]] = []
        self.model_name: Optional[str] = None
        self.selected_tools: List[str] = []
        self.validated_servers: List[str] = []
        self.session_id: str = id(self)  # Simple session ID
        
        logger.info(f"ChatSession created for user: {self.user_email} (session: {self.session_id})")

    async def _trigger_callbacks(self, event: str, **kwargs):
        """Asynchronously triggers all callbacks registered for a specific event."""
        if event in self._callbacks:
            # Pass the session instance to each callback
            try:
                await asyncio.gather(*(cb(self, **kwargs) for cb in self._callbacks[event]))
            except Exception as e:
                logger.error(f"Error in callback for event '{event}': {e}", exc_info=True)

    async def run(self):
        """Main loop to receive and handle messages from the client."""
        try:
            await self._trigger_callbacks("session_started")
            
            while True:
                data = await self.websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "chat":
                    await self.handle_chat_message(message)
                else:
                    await self.send_error(f"Unknown message type: {message.get('type')}")
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket connection closed for user: {self.user_email}")
            await self._trigger_callbacks("session_ended")
        except Exception as e:
            logger.error(f"Error in ChatSession for {self.user_email}: {e}", exc_info=True)
            await self.send_error("An internal server error occurred.")
            await self._trigger_callbacks("session_error", error=e)

    async def handle_chat_message(self, message: Dict[str, Any]):
        """Handles chat messages with LLM integration and tool calling."""
        try:
            await self._trigger_callbacks("before_message_processing", message=message)

            content = message.get('content', '')
            self.model_name = message.get('model', '')
            self.selected_tools = message.get('selected_tools', [])
            
            logger.info(f"Received chat message from {self.user_email}: content='{content[:50]}...', model='{self.model_name}', tools={self.selected_tools}")
            
            if not content or not self.model_name:
                raise ValueError("Message content and model name are required.")
            
            # Allow callbacks to modify the message before processing
            await self._trigger_callbacks("before_user_message_added", content=content)
            
            # Append user message to history
            user_message = {"role": "user", "content": content}
            self.messages.append(user_message)
            
            await self._trigger_callbacks("after_user_message_added", user_message=user_message)
            
            await self._trigger_callbacks("before_validation")
            self.validated_servers = await validate_selected_tools(self.selected_tools, self.user_email, self.mcp_manager)
            await self._trigger_callbacks("after_validation", validated_servers=self.validated_servers)
            
            logger.info(f"Calling LLM {self.model_name} for user {self.user_email} with {len(self.validated_servers)} servers")
            
            await self._trigger_callbacks("before_llm_call", messages=self.messages)
            llm_response = await call_llm_with_tools(
                self.model_name, 
                self.messages, 
                self.validated_servers, 
                self.user_email, 
                self.websocket,
                self.mcp_manager
            )
            await self._trigger_callbacks("after_llm_call", llm_response=llm_response)
            
            # Append assistant response to history
            assistant_message = {"role": "assistant", "content": llm_response}
            self.messages.append(assistant_message)
            await self._trigger_callbacks("after_assistant_message_added", assistant_message=assistant_message)

            response_payload = {
                "type": "chat_response", 
                "message": llm_response,
                "model": self.model_name, 
                "user": self.user_email
            }
            
            await self._trigger_callbacks("before_response_send", payload=response_payload)
            await self.send_json(response_payload)
            await self._trigger_callbacks("after_response_send", payload=response_payload)
            logger.info(f"LLM response sent to user {self.user_email}")

        except Exception as e:
            logger.error(f"Error handling chat message for {self.user_email}: {e}", exc_info=True)
            await self._trigger_callbacks("message_error", error=e)
            await self.send_error(f"Error processing message: {str(e)}")

    async def send_json(self, data: Dict[str, Any]):
        await self.websocket.send_text(json.dumps(data))

    async def send_error(self, error_message: str):
        await self.send_json({"type": "error", "message": error_message})


class SessionManager:
    """Manages the lifecycle of all active ChatSession instances."""
    def __init__(self, mcp_manager: MCPToolManager):
        self.active_sessions: Dict[WebSocket, ChatSession] = {}
        self.callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.mcp_manager = mcp_manager

    def register_callback(self, event: str, func: Callable[['ChatSession', ...], Awaitable[None]]):
        """Register a callback function for a specific event."""
        self.callbacks[event].append(func)
        logger.info(f"Registered callback for event '{event}': {func.__name__}")

    def unregister_callback(self, event: str, func: Callable):
        """Unregister a callback function for a specific event."""
        if event in self.callbacks and func in self.callbacks[event]:
            self.callbacks[event].remove(func)
            logger.info(f"Unregistered callback for event '{event}': {func.__name__}")

    async def connect(self, websocket: WebSocket, user_email: str):
        """Creates and runs a new ChatSession."""
        await websocket.accept()
        session = ChatSession(websocket, user_email, self.mcp_manager, self.callbacks)
        self.active_sessions[websocket] = session
        logger.info(f"Session started for {user_email}, total active: {len(self.active_sessions)}")
        await session.run()

    def disconnect(self, websocket: WebSocket):
        """Removes a session upon disconnection."""
        if websocket in self.active_sessions:
            session = self.active_sessions[websocket]
            del self.active_sessions[websocket]
            logger.info(f"Session removed for {session.user_email}, remaining active: {len(self.active_sessions)}")

    def get_session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self.active_sessions)

    def get_sessions_for_user(self, user_email: str) -> List[ChatSession]:
        """Get all active sessions for a specific user."""
        return [session for session in self.active_sessions.values() if session.user_email == user_email]


# --- Global Managers ---
mcp_manager: Optional[MCPToolManager] = None
session_manager: Optional[SessionManager] = None


# --- Utility Functions ---

def get_current_user(request: Request) -> str:
    """Get current user from request state."""
    return getattr(request.state, 'user_email', None)


async def validate_selected_tools(selected_tools: List[str], user_email: str, mcp_manager: MCPToolManager) -> List[str]:
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


async def call_llm_with_tools(model_name: str, messages: List[Dict[str, str]], validated_servers: List[str], user_email: str, websocket: WebSocket, mcp_manager: MCPToolManager) -> str:
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


# --- Example Callbacks ---

async def log_session_events_callback(session: ChatSession, **kwargs):
    """Log session lifecycle events."""
    event_type = kwargs.get('event_type', 'unknown')
    logger.info(f"[SESSION] {event_type} for user {session.user_email} (session: {session.session_id})")

async def log_llm_call_callback(session: ChatSession, **kwargs):
    """A simple logging callback."""
    logger.info(f"[CALLBACK] User {session.user_email} is calling model {session.model_name} with {len(session.messages)} total messages.")

async def message_history_limit_callback(session: ChatSession, **kwargs):
    """Limit message history to prevent context overflow."""
    max_messages = 20  # Configurable limit
    if len(session.messages) > max_messages:
        # Keep first message (system prompt if any) and last N messages
        session.messages = session.messages[:1] + session.messages[-(max_messages-1):]
        logger.info(f"[CALLBACK] Trimmed message history for {session.user_email} to {len(session.messages)} messages")

async def security_audit_callback(session: ChatSession, **kwargs):
    """Audit security-sensitive operations."""
    message = kwargs.get('message', {})
    content = message.get('content', '') if message else ''
    
    # Check for potentially sensitive keywords
    sensitive_keywords = ['password', 'api_key', 'secret', 'token', 'credential']
    if any(keyword in content.lower() for keyword in sensitive_keywords):
        logger.warning(f"[SECURITY] Potentially sensitive content detected from user {session.user_email}")

async def modify_user_message_callback(session: ChatSession, **kwargs):
    """An example callback that modifies the user's message."""
    content = kwargs.get('content', '')
    # Example: Add context or disclaimers
    # This would modify the content before it's added to the message history
    # For now, we'll just log that we could modify it
    logger.debug(f"[CALLBACK] Could modify user message for {session.user_email}")


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
    session_manager.register_callback("before_user_message_added", modify_user_message_callback)
    
    logger.info("All callbacks registered successfully")
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


# --- API Endpoints ---

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
    """Get available models, tools, and data sources for the user.
    Only returns MCP servers and tools that the user is authorized to access.
    """
    llm_config = load_llm_config()
    
    # Get authorized servers for the user - this filters out unauthorized servers completely
    authorized_servers = mcp_manager.get_authorized_servers(current_user, is_user_in_group)
    
    # Only build tool information for servers the user is authorized to access
    tools_info = []
    for server_name in authorized_servers:
        if server_name in mcp_manager.available_tools:
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
        "app_name": os.getenv("APP_NAME", "Chat UI"),
        "models": list(llm_config.get("models", {}).keys()) if llm_config else [],
        "tools": tools_info,  # Only authorized servers are included
        "user": current_user,
        "active_sessions": session_manager.get_session_count() if session_manager else 0,
        "authorized_servers": authorized_servers  # Optional: expose for debugging
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


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main_refactored:app", host="0.0.0.0", port=port, reload=True)
