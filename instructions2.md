# Chat UI Project Instructions

## Overview

Create a frontend for an LLM chat interface similar to ChatGPT, Chainlit, or Anthropic Claude. Users can select and interact with different LLMs through a modern web interface.

Reference: `frontend-example.html` shows the general layout (functionality will differ from the example).

## Architecture Requirements

### Technology Stack

- **Backend**: FastAPI with WebSockets
- **Frontend**: Vanilla JavaScript (future-proofed for easy npm migration)
- **Python Package Manager**: uv
- **Code Analysis**: Ruff for fast Python linting and formatting
- **Containerization**: Docker with Fedora:latest base image


The CHAT ui backend will be an MCP client, and it can connect to different mcp servers. 

### Project Structure

```text
project/
├── frontend/          # Frontend application
├── backend/           # FastAPI backend
│   ├── mcp/          # MCP servers (each in separate folder)
│   └── logs/         # Application logs
├── Dockerfile
├── .env              # Configuration values
├── llmconfig.yml     # LLM configurations
└── mcp.json          # MCP server configurations
```

### Code Quality Standards

- **File Length**: Maximum 400 lines per file (no exceptions)
- **Modularity**: Highly modular and easy to optimize
- **FastAPI Routes**: Use separate routes to maintain separation of concerns
- **Testing**: Unit tests only (no integration tests)
- **Code Style**: No emojis anywhere in the codebase
- **Code Analysis**: Use Ruff for fast Python linting and formatting

## Frontend Requirements

### Technology Approach

- **Vanilla JavaScript**: Use native JavaScript without build tools or npm dependencies
- **Future-Proofing**: Structure code to make migration to npm/build tools easy when needed
- **Module Organization**: Use ES6 modules with clear separation of concerns
- **Static Assets**: Serve directly from filesystem without bundling

### Display Components

- Available models/LLMs
- Available tools (from MCP servers)
- Available data sources for RAG

### Communication

- WebSockets for dynamic loading and real-time updates

## Backend Requirements

### Authentication & Authorization

#### Reverse Proxy Integration

- App assumes it's behind a reverse proxy
- Reverse proxy handles authentication and injects `x-email-header`
- Middleware must check for `x-email-header`
- Redirect to `/auth` endpoint if header is missing

#### Debug Mode

- Skip authentication checks
- Default user: `test@test.com`

#### Authorization System

- Custom authorization library (mock implementation for now)
- Single authorization function: `is_user_in_group(userid, groupid)`
- Server-side validation for all user requests

### Middleware Requirements

- Check for `x-email-header`
- Log request type and route
- Handle authorization

### Security

- Robust security measures
- Proper authentication and authorization
- Server-side validation of all MCP access requests

### Logging

- Log to `app.log` in `logs/` folder

## Configuration

### LLM Configuration (`llmconfig.yml`)

Runtime configuration containing for each LLM:

- `model_url`
- `model_name`
- `api_key`

### MCP Configuration (`mcp.json`)

The CHAT ui backend will be an MCP client, and it can connect to different mcp servers. 

Configuration for MCP servers including:

- `groups`: User groups allowed to access the MCP server
- `is_exclusive`: Whether the MCP can run with other MCPs simultaneously (security consideration)

### Environment Variables (`.env`)

- All other configuration values

## MCP (Model Context Protocol) Integration

### MCP Server Setup

- Location: `backend/mcp/` folder
- Each MCP server in separate subfolder
- Demo server: File system read/write MCP server
- Use fastmcp2: <https://gofastmcp.com/servers/server>

### MCP Usage

- RAG server access through MCP
- Tool usage through MCP
- Chat UI acts as MCP client

### FastMCP Example

```python
from fastmcp import FastMCP

mcp = FastMCP("Demo")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

if __name__ == "__main__":
    mcp.run()
```

### Reference Documentation

- FastMCP Python: <https://gofastmcp.com/getting-started/welcome>
- Use context 7 MCP for documentation lookup

## Docker Configuration

- Base image: `fedora:latest`
- Python package management: uv

## Security Considerations

- Reverse proxy blocks unauthenticated requests
- Backend still handles authorization
- MCP server access based on user group membership
- Exclusive MCP servers prevent concurrent execution when security-sensitive


add a readme.md
add a .gitignore file


use uv and virtual venv
uv venv venv

## Recent Improvements and Clarifications

• **Frontend Dark Theme Redesign**: Completely redesigned the frontend to match modern dark-themed chat interfaces similar to ChatGPT/Claude with proper message bubbles, avatars, and collapsible tools panel. The interface now uses Inter font, backdrop blur effects, and a professional gray-900 color scheme.

• **Dynamic App Name Configuration**: The application name is now configurable via the `.env` file (`APP_NAME` variable) and dynamically loads across all UI elements including page title, header, and message authors. This allows easy branding customization for different deployments.

• **Auto-Model Selection**: The frontend automatically selects the first available LLM model on startup, eliminating the need for manual model selection before chatting. Users can still manually change models via the dropdown in the header.

• **Enhanced Configuration Loading**: Improved error handling for both `llmconfig.yml` and `mcp.json` with multiple path searching, detailed logging, and helpful error messages. The system now provides clear guidance when configuration files are missing or malformed.

• **WebSocket Authentication Security**: Added proper WebSocket authentication that checks for `x-email-header` during handshake from reverse proxy in production mode. Debug mode falls back to `test@test.com` for local development testing.

• **OpenAI-Compatible LLM Integration**: Implemented real LLM API calls using `requests` library with OpenAI-compliant endpoints, proper error handling, and async execution. The system supports environment variable expansion for API keys and comprehensive logging.

• **Markdown Rendering with Code Copy**: Added full markdown-to-HTML rendering for assistant messages using Marked.js with DOMPurify sanitization. Code blocks include copy-to-clipboard functionality with visual feedback and fallback support for older browsers.

• **Improved Project Structure**: Moved `requirements.txt` to project root and created a simplified `start.sh` script that uses `uv venv venv` for virtual environment management. The startup script automatically installs dependencies and launches uvicorn with reload for development.

• **Better Logging and Debugging**: Enhanced logging throughout the application with user-specific WebSocket tracking, detailed LLM API call logging, and clear success/error messages. Configuration loading now shows exactly where files were found and how many models/tools were loaded.

• **Production-Ready Security**: Implemented comprehensive security measures including XSS protection via DOMPurify, server-side request validation, group-based MCP tool authorization, and proper authentication middleware. The system maintains security in production while providing debug fallbacks for development.
