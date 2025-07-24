# Chat UI Project

A modern LLM chat interface with MCP (Model Context Protocol) integration, similar to ChatGPT or Claude. The backend serves as an MCP client that can connect to multiple MCP servers for enhanced functionality.

## Features

- **Multi-LLM Support**: Connect to different language models (OpenAI GPT, Anthropic Claude, Google Gemini)
- **MCP Integration**: Backend acts as MCP client, connecting to various MCP servers for tools and data sources
- **Authentication**: Reverse proxy authentication with x-email-header support
- **Authorization**: Group-based access control for MCP servers
- **Real-time Communication**: WebSocket-based chat interface
- **Modular Design**: Highly modular codebase with maximum 400 lines per file
- **Vanilla JavaScript**: Frontend built without build tools for easy npm migration
- **Security**: Robust authentication, authorization, and server-side validation

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
- **Frontend**: Vanilla JavaScript (ES6 modules)
- **Python Package Manager**: uv with virtual environments
- **Code Analysis**: Ruff for Python linting and formatting
- **Containerization**: Docker with Fedora base image

### Project Structure
```

├── frontend/          # Frontend application
│   ├── index.html     # Main chat interface
│   ├── style.css      # UI styles
│   └── app.js         # Application logic
├── backend/           # FastAPI backend (MCP client)
│   ├── main.py        # Main FastAPI application
│   ├── session.py     # WebSocket session management
│   ├── message_processor.py # Core message processing logic
│   ├── middleware.py  # Authentication middleware
│   ├── auth.py        # Authorization functions
│   ├── mcp_client.py  # MCP client implementation
│   ├── mcp/           # MCP servers
│   │   ├── filesystem/ # File system operations
│   │   ├── calculator/ # Mathematical calculations
│   │   └── thinking/   # Structured thinking tool
│   └── logs/          # Application logs
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

3. **Start the backend**:
   ```bash
   python main.py
   ```

4. **Access the interface**:
   Open http://localhost:8000 in your browser

## Configuration

### Environment Variables (.env)
```bash
DEBUG_MODE=true              # Skip authentication in development
PORT=8000                   # Server port
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
    "command": ["python", "mcp/filesystem/main.py"],
    "cwd": "backend",
    "groups": ["users", "mcp_basic"],
    "is_exclusive": false,
    "description": "File system read/write operations"
  }
}
```

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
- Use ES6 modules for organization
- Maintain vanilla JavaScript approach
- Structure for easy npm migration
- Follow existing patterns and conventions

## Security Considerations

- Reverse proxy handles authentication
- Server-side authorization for all requests
- MCP server access based on user groups
- Exclusive servers prevent concurrent execution
- Path validation in filesystem operations
- Safe expression evaluation in calculator

## Logging

All application logs are written to `backend/logs/app.log` with the following format:
```
2024-01-01 12:00:00 - module - INFO - Request: GET /api/config
```

## Troubleshooting

### Common Issues
1. **WebSocket connection fails**: Check if backend is running on correct port
2. **Authentication errors**: Verify `x-email-header` or enable `DEBUG_MODE`
3. **MCP tools not available**: Check user group permissions in `mcp.json`
4. **Docker build fails**: Ensure all files are in correct locations

### Development Tips
- Use browser developer tools to inspect WebSocket messages
- Check `backend/logs/app.log` for server-side errors
- Verify environment variables are loaded correctly
- Test MCP servers independently using command line

## Contributing

1. Follow the 400-line file limit
2. Use Ruff for code formatting
3. Write unit tests for new features
4. Update documentation for API changes
5. Follow existing code patterns and conventions

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