# Chat UI

A modern LLM chat interface with MCP (Model Context Protocol) integration.

## Features

- **Multi-LLM Support**: OpenAI GPT, Anthropic Claude, Google Gemini
- **MCP Integration**: Connect to multiple MCP servers for tools and data sources  
- **Real-time Communication**: WebSocket-based chat interface
- **Custom UI**: MCP servers can modify the UI with custom HTML
- **Authorization**: Group-based access control for MCP servers
- **Modern Stack**: React frontend, FastAPI backend, Docker support

## Quick Start

### Docker (Recommended)
```bash
docker build -t chat-ui .
docker run -p 8000:8000 chat-ui
```
Open http://localhost:8000

### Local Development
**Important**: This project uses **uv** as the Python package manager.

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup environment
uv venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# Configure
cp .env.example .env  # Edit with your API keys

# Build frontend
cd frontend && npm install && npm run build

# Start backend  
cd ../backend && python main.py
```

## Documentation

All documentation has been organized in the `docs/` folder:

- **[Quick Start](docs/quick-start.md)** - Get running quickly
- **[Developer Setup](docs/developer-setup.md)** - Full development environment setup
- **[Backend Guide](docs/backend.md)** - Backend architecture and development  
- **[Frontend Guide](docs/frontend.md)** - React frontend development
- **[MCP Development](docs/mcp-development.md)** - Creating MCP servers
- **[Configuration](docs/configuration.md)** - Complete configuration guide
- **[Advanced Features](docs/advanced-features.md)** - Custom HTML, RAG, Agent mode
- **[TODO & Ideas](docs/todo.md)** - Roadmap and future enhancements

## Key Technologies

- **Backend**: FastAPI + WebSockets  
- **Frontend**: React + Vite + Tailwind CSS
- **Python Package Manager**: **uv** (not pip!)
- **Configuration**: Pydantic with type safety
- **Containerization**: Docker

## Important Notes

- **Use `uv`** for Python package management, not pip or conda
- **Don't use `uvicorn --reload`** - causes problems in development
- **Use `npm run build`** instead of `npm run dev` for frontend development
- **File limit**: Maximum 400 lines per file for maintainability

## License

MIT License