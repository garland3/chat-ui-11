# Chat UI Project

A modern LLM chat interface with MCP (Model Context Protocol) integration, similar to ChatGPT or Claude. The backend serves as an MCP client that can connect to multiple MCP servers for enhanced functionality.

## Features

- **Multi-LLM Support**: Connect to different language models (OpenAI GPT, Anthropic Claude, Google Gemini)
- **MCP Integration**: Backend acts as MCP client, connecting to various MCP servers for tools and data sources
- **Authentication**: Reverse proxy authentication with x-email-header support
- **Authorization**: Group-based access control for MCP servers
- **Real-time Communication**: WebSocket-based chat interface
- **Modern Configuration**: Pydantic-based type-safe configuration system
- **Unified Error Handling**: Centralized HTTP client and comprehensive error logging
- **Modular Design**: Highly modular codebase with maximum 400 lines per file
- **Vanilla JavaScript**: Frontend built without build tools for easy npm migration
- **Security**: Robust authentication, authorization, and server-side validation

## 🆕 Recent Improvements (v2.0)

The codebase has been significantly refactored for better maintainability and reliability:

### **Configuration System Overhaul**
- **Pydantic Models**: Type-safe configuration with automatic validation
- **Centralized Management**: Single `config.py` file manages all settings
- **Environment Integration**: Seamless .env file loading with fallback defaults
- **Eliminated Duplication**: Removed ~150 lines of duplicate configuration code

### **Unified HTTP Client**
- **Consistent Error Handling**: Standardized HTTP error responses across all services
- **Comprehensive Logging**: All HTTP errors now include full tracebacks
- **Reusable**: Single HTTP client used by RAG service and other components

### **Authorization Utilities**
- **Centralized Logic**: All authorization logic moved to `auth_utils.py`
- **Better Security**: Enhanced security violation logging and monitoring
- **Testable**: Clean, testable authorization functions

### **Enhanced Error Logging**
- **Full Tracebacks**: All errors now use `exc_info=True` for complete stack traces
- **Standardized**: Consistent error logging patterns throughout codebase
- **Debug Cleanup**: Removed all debug print statements in favor of proper logging

## Architecture

### Core Message Processing

**CRITICAL**: The `MessageProcessor` class in `backend/message_processor.py` contains the **most important logic in the entire codebase**. The `handle_chat_message()` method:

- Orchestrates the entire chat message processing pipeline
- Handles RAG-only vs integrated processing modes  
- Manages tool validation and LLM calls
- Coordinates callbacks throughout the message lifecycle
- Processes WebSocket messages and responses

This was extracted from `ChatSession` to improve modularity, testability, and maintainability while preserving encapsulation through dependency injection of the session instance.

### Technology Stack
- **Backend**: FastAPI with WebSockets
- **Frontend**: React with Vite build system
- **Python Package Manager**: uv with virtual environments
- **Code Analysis**: Ruff for Python linting and formatting
- **Containerization**: Docker with Fedora base image

### Project Structure
```
├── frontend/          # React frontend application
│   ├── dist/          # Built frontend files (served by backend)
│   ├── src/           # React source code
│   │   ├── components/ # React components
│   │   ├── contexts/   # React contexts
│   │   └── hooks/      # Custom React hooks
│   ├── package.json   # Node.js dependencies
│   └── vite.config.js # Vite build configuration
├── old_frontend/      # Legacy vanilla JS frontend (deprecated)
├── backend/           # FastAPI backend (MCP client)
│   ├── main.py        # Main FastAPI application
│   ├── session.py     # WebSocket session management
│   ├── message_processor.py # Core message processing logic
│   ├── config.py      # 🆕 Unified Pydantic configuration system
│   ├── http_client.py # 🆕 Unified HTTP client with error handling
│   ├── auth_utils.py  # 🆕 Centralized authorization utilities
│   ├── middleware.py  # Authentication middleware
│   ├── auth.py        # Authorization functions
│   ├── mcp_client.py  # MCP client implementation
│   ├── utils.py       # Utility functions (refactored)
│   ├── rag_client.py  # RAG integration client (refactored)
│   ├── callbacks.py   # Event callback functions
│   ├── prompt_utils.py # System prompt utilities
│   ├── mcp/           # MCP servers
│   │   ├── filesystem/ # File system operations
│   │   ├── calculator/ # Mathematical calculations
│   │   ├── secure/     # Secure operations
│   │   ├── thinking/   # Structured thinking tool
│   │   └── duckduckgo/ # Web search integration
│   └── logs/          # Application logs
├── rag-mock/          # Mock RAG service for testing
├── Dockerfile         # Container configuration
├── .env               # Environment variables
├── llmconfig.yml      # LLM configurations
└── mcp.json           # MCP server configurations
```

## Quick Start

### Using Docker

1. **Build the container**:
   ```bash
   docker build -t chat-ui .
   ```

2. **Run the container**:
   ```bash
   docker run -p 8000:8000 chat-ui
   ```

3. **Access the interface**:
   Open http://localhost:8000 in your browser

### Local Development

1. **Set up Python environment**:
   ```bash
   cd backend
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

3. **Build the frontend**:
   ```bash
   cd ../frontend
   npm install
   npm run build
   ```

4. **Start the backend**:
   ```bash
   cd ../backend
   python main.py
   ```

5. **Access the interface**:
   Open http://localhost:8000 in your browser

## Configuration

The project now uses a **modern Pydantic-based configuration system** that provides type safety, validation, and centralized management of all settings.

### Configuration Architecture

- **`config.py`** - Unified configuration management with Pydantic models
- **Type-safe** - Automatic validation and type checking
- **Environment integration** - Seamless .env file loading
- **Centralized** - Single source of truth for all configuration

### Environment Variables (.env)
```bash
# Application Settings
DEBUG_MODE=true              # Skip authentication in development  
PORT=8000                   # Server port
APP_NAME="Chat UI"          # Application name

# RAG Settings
MOCK_RAG=true               # Use mock RAG service for testing
RAG_MOCK_URL=http://localhost:8001  # RAG service URL

# Agent Settings
AGENT_MODE_AVAILABLE=false  # Enable agent mode UI
AGENT_MAX_STEPS=10          # Maximum agent reasoning steps

# API Keys (used by LLM config)
OPENAI_API_KEY=your_key     # OpenAI API key
ANTHROPIC_API_KEY=your_key  # Anthropic API key
GOOGLE_API_KEY=your_key     # Google API key
```

### LLM Configuration (llmconfig.yml)
```yaml
models:
  gpt-4:
    model_url: "https://api.openai.com/v1/chat/completions"
    model_name: "gpt-4"
    api_key: "${OPENAI_API_KEY}"
  # Add more models...
```

### MCP Configuration (mcp.json)
```json
{
  "filesystem": {
    "groups": ["users", "mcp_basic"],
    "is_exclusive": false,
    "description": "File system read/write operations",
    "enabled": true
  },
  "calculator": {
    "groups": ["users"],
    "is_exclusive": false,
    "description": "Mathematical calculations",
    "enabled": true
  },
  "duckduckgo": {
    "groups": ["users", "mcp_basic"],
    "is_exclusive": false,
    "description": "Web search via DuckDuckGo",
    "enabled": true
  }
}
```

### Accessing Configuration in Code
```python
from config import config_manager

# Get application settings
app_settings = config_manager.app_settings
print(f"Running {app_settings.app_name} on port {app_settings.port}")

# Get LLM configuration
llm_config = config_manager.llm_config
models = list(llm_config.models.keys())

# Get MCP configuration
mcp_config = config_manager.mcp_config
servers = list(mcp_config.servers.keys())
```

### System Prompt Configuration
The AI assistant behavior can be customized by editing `backend/prompts/system_prompt.md`. This file contains the system prompt that's loaded at runtime for new conversations. The prompt supports user personalization with `{user_email}` placeholders and is automatically formatted when loaded. Changes to this file take effect immediately for new conversations without requiring a server restart.

### Offline Deployment
For deployments without internet access, run the dependency download script to eliminate all external CDN calls:

```bash
python scripts/download-deps.py
```

This downloads the required JavaScript libraries (marked.js and DOMPurify) to `frontend/vendor/` and removes all external dependencies from the application. The main route serves `index.html` directly instead of redirecting to static files.

**Manual edits required after running the script:**
- Remove Google Fonts CDN links from `index.html` (fonts can be system fonts)
- Remove source map reference from `purify.min.js` to prevent CDN lookups
- Add vendor directory mounts in `main.py` for proper static file serving

## MCP Servers

The backend includes two demo MCP servers:

### Filesystem Server
- **Tools**: read_file, write_file, list_directory, create_directory, delete_file, file_exists
- **Security**: Path validation to prevent directory traversal
- **Groups**: users, mcp_basic

### Calculator Server
- **Tools**: add, subtract, multiply, divide, power, sqrt, factorial, evaluate
- **Security**: Safe expression evaluation with restricted builtins
- **Groups**: users

## Authentication & Authorization

### Authentication
- **Production**: Expects `x-email-header` from reverse proxy
- **Development**: Set `DEBUG_MODE=true` to use test user

### Authorization
- **Group-based**: Users belong to groups (admin, users, mcp_basic, mcp_advanced)
- **Server-side validation**: All MCP access requests validated
- **Exclusive servers**: Some MCP servers cannot run concurrently for security

**Note**: For testing different authorization scenarios, you can toggle the `mock_groups` configuration in `backend/auth.py`. The file contains commented examples showing different user group assignments that can be uncommented to test various permission levels.

## API Endpoints

- `GET /`: Main chat interface
- `GET /api/config`: Get available models and tools for user
- `WebSocket /ws`: Real-time chat communication
- `GET /auth`: Authentication endpoint for redirects

## WebSocket Protocol

### Client Messages
```json
{
  "type": "chat",
  "content": "Hello, world!",
  "model": "gpt-4",
  "user": "user@example.com"
}

{
  "type": "mcp_request",
  "server": "filesystem",
  "request": {
    "method": "tools/call",
    "params": {
      "name": "read_file",
      "arguments": {"path": "test.txt"}
    }
  }
}
```

### Server Messages
```json
{
  "type": "chat_response",
  "message": "Hello! How can I help you?",
  "user": "user@example.com"
}

{
  "type": "mcp_response",
  "server": "filesystem",
  "response": {"content": "file contents..."}
}
```

## Development

### Code Quality Standards
- **File Length**: Maximum 400 lines per file
- **Modularity**: Highly modular design
- **Code Style**: No emojis in codebase
- **Testing**: Unit tests only
- **Linting**: Use `ruff` for Python code analysis

### Adding New MCP Servers
1. Create new directory in `backend/mcp/`
2. Implement `main.py` with MCP protocol
3. Add configuration to `mcp.json`
4. Set appropriate user groups

### Extending Frontend
- Built with React and Vite for modern development
- Uses Tailwind CSS for styling
- WebSocket integration through React contexts
- Components organized by functionality

## Security Considerations

- Reverse proxy handles authentication
- Server-side authorization for all requests
- MCP server access based on user groups
- Exclusive servers prevent concurrent execution
- Path validation in filesystem operations
- Safe expression evaluation in calculator

## Logging

The application uses comprehensive logging with the following improvements:

### **Enhanced Error Logging**
- **Full Tracebacks**: All errors include complete stack traces (`exc_info=True`)
- **Consistent Format**: Standardized logging patterns across all modules
- **Security Auditing**: Special logging for security violations and authorization failures

### **Log Files**
All application logs are written to `backend/logs/app.log` with the following format:
```
2024-01-01 12:00:00,123 - module_name - ERROR - Error message with full traceback
```

### **Log Levels**
- **ERROR**: All exceptions and errors (with full tracebacks)
- **WARNING**: Security violations, authorization failures, deprecated usage
- **INFO**: Application lifecycle events, successful operations
- **DEBUG**: Detailed debugging information (development only)

## Troubleshooting

### Common Issues
1. **WebSocket connection fails**: Check if backend is running on correct port
2. **Authentication errors**: Verify `x-email-header` or enable `DEBUG_MODE`
3. **MCP tools not available**: Check user group permissions in `mcp.json`
4. **Docker build fails**: Ensure all files are in correct locations

### Development Tips
- Use browser developer tools to inspect WebSocket messages
- Check `backend/logs/app.log` for server-side errors (now includes full tracebacks)
- Verify environment variables with: `python -c "from config import config_manager; print(config_manager.app_settings)"`
- Test configuration loading: `python -c "from config import config_manager; print('✅ Config OK')"`
- Test MCP servers independently using command line
- Use the new authorization utilities for consistent permission checking

## Contributing

1. Follow the 400-line file limit
2. Use Ruff for code formatting
3. Write unit tests for new features
4. Update documentation for API changes
5. Follow existing code patterns and conventions
6. **Use the new utilities**: 
   - Import from `config.config_manager` for all configuration
   - Use `http_client.UnifiedHTTPClient` for HTTP requests
   - Use `auth_utils.AuthorizationManager` for permission checks
   - Always use `exc_info=True` for error logging

## License

This project is licensed under the MIT License.


# mcp notes
the mcp.json requires the name of the tool to match the folder right now. TODO to fix. 

for the main socket. 
I think a user couuld spoof another user's email. 
-- so we need to setup some jwt to match to their email. check the jwt to get the real user name. 
-- probably use 'depends' for this 


-- some pipeline, where you force the backend to use a tool, ... skip the invocation of the llm tool and just call it. 

-- how do custom promtps?