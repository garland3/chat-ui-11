# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend Development
```bash
cd backend
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
python main.py
```

### Code Quality
```bash
# Python linting and formatting
ruff check backend/
ruff format backend/
```

### Docker Development
```bash
# Build container
docker build -t chat-ui .

# Run container
docker run -p 8000:8000 chat-ui
```

### Testing
- Unit tests only (no specific test framework configured)
- Test MCP servers independently using command line

## Architecture Overview

### Core Message Processing Pipeline
The **most critical** code is in `backend/message_processor.py`. The `MessageProcessor.handle_chat_message()` method orchestrates the entire chat processing pipeline:

1. **RAG-only Mode**: Direct queries to selected data sources, bypassing LLM tool integration
2. **Integrated Mode**: Combines RAG context with LLM calls and MCP tool validation
3. **Callback Coordination**: Triggers callbacks throughout the message lifecycle
4. **WebSocket Communication**: Manages real-time updates to the frontend

### Key Components

**Backend (FastAPI + WebSockets)**
- `main.py`: FastAPI application with callback system registration
- `session.py`: WebSocket session management with SessionManager
- `message_processor.py`: Core message processing logic (MOST IMPORTANT)
- `mcp_client.py`: MCP (Model Context Protocol) client implementation
- `auth.py` + `middleware.py`: Authentication and authorization

**Frontend (Vanilla JavaScript)**
- `frontend/index.html`: Main chat interface
- `frontend/app.js`: Application logic with ES6 modules
- `frontend/style.css`: UI styles

**MCP Servers** (located in `backend/mcp/`)
- `filesystem/`: File operations with path validation security
- `calculator/`: Math operations with safe expression evaluation
- `thinking/`: Structured thinking tool

### Technology Stack
- **Backend**: FastAPI with WebSockets, Python `uv` package manager
- **Frontend**: Vanilla JavaScript (no build tools, designed for easy npm migration)
- **MCP Integration**: FastMCP client connecting to local MCP servers
- **Containerization**: Docker with Fedora base image

## Configuration Files

### Environment Variables (.env)
```bash
DEBUG_MODE=true              # Skip authentication in development
PORT=8000                   # Server port
OPENAI_API_KEY=your_key     # OpenAI API key
ANTHROPIC_API_KEY=your_key  # Anthropic API key
GOOGLE_API_KEY=your_key     # Google API key
```

### LLM Configuration (llmconfig.yml)
Defines available language models with API endpoints and keys.

### MCP Configuration (mcp.json)
Configures MCP servers with:
- Command paths and working directories
- Group-based authorization (`users`, `mcp_basic`, `mcp_advanced`, `admin`)
- Exclusive server settings (cannot run concurrently)
- Security descriptions

## Development Standards

### Code Quality
- **Maximum 400 lines per file** (strictly enforced)
- **No emojis in codebase**
- **Highly modular design**
- Use `ruff` for Python linting and formatting

### Security & Authorization
- **Group-based access control**: Users belong to groups that determine MCP server access
- **Server-side validation**: All MCP access requests validated against user groups
- **Path validation**: Filesystem operations prevent directory traversal
- **Safe evaluation**: Calculator uses restricted builtins
- **Authentication**: Production expects `x-email-header` from reverse proxy

### Callback System
The backend uses an event-driven callback system for customizable behavior:
- Register callbacks for events like `before_llm_call`, `after_validation`, etc.
- Callbacks receive the `ChatSession` instance and can modify state
- See `main.py` lines 57-66 for callback registration examples

## Adding New Features

### New MCP Servers
1. Create directory in `backend/mcp/`
2. Implement `main.py` with MCP protocol
3. Add configuration to `mcp.json` with appropriate groups
4. Server name must match folder name (current limitation)

### Frontend Extensions
- Maintain vanilla JavaScript approach
- Use ES6 modules for organization
- Follow existing patterns for WebSocket communication
- Structure code for easy npm migration

## API Endpoints
- `GET /`: Main chat interface (redirects to `/static/index.html`)
- `GET /api/config`: Available models, tools, and user permissions
- `GET /api/sessions`: Session information for current user
- `GET /api/debug/servers`: Server authorization debug info (DEBUG_MODE only)
- `WebSocket /ws`: Real-time chat communication

## WebSocket Protocol
Client sends messages with `type: "chat"` including content, model, selected_tools, selected_data_sources, and only_rag flag. Server responds with `type: "chat_response"` or `type: "error"`.

## Logging
All logs written to `backend/logs/app.log` with format: `YYYY-MM-DD HH:MM:SS - module - LEVEL - message`