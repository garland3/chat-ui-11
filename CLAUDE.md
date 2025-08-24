# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chat UI is a modern LLM chat interface with MCP (Model Context Protocol) integration. It features a FastAPI backend serving a React frontend with WebSocket-based real-time communication.

**CRITICAL**: This project uses `uv` as the Python package manager, NOT pip or conda.

## Development Commands

### Setup and Environment
```bash
# Install uv (required - NOT pip or conda)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create environment and install dependencies  
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# Setup configuration
cp .env.example .env  # Edit with your API keys, set DEBUG_MODE=true for dev
```

### Running the Application

**Primary Method** - Use the provided startup script:
```bash
# Start full application (builds frontend + starts backend)
sh agent_start.sh

# Optional flags:
sh agent_start.sh -f  # Frontend only (rebuild and exit)
sh agent_start.sh -b  # Backend only (restart backend services)

# Access at http://localhost:8000
```

**What agent_start.sh does:**
- Clears mock S3 storage and logs
- Kills existing Python/uvicorn processes  
- Builds frontend with `npm run build`
- Starts S3 mock service on port 8003
- Starts backend with uvicorn on port 8000

### Storage Dependencies
The application uses MinIO for S3-compatible storage:
```bash
# MinIO should be running all the time with Docker
# (The script will also start a mock S3 service on port 8003 as fallback)
```

### Testing

**Recommended Method** - Use the unified test script:
```bash
# Run all tests (takes up to 2 minutes - NEVER CANCEL)
sh test/run_tests.sh all

# Individual test suites  
sh test/run_tests.sh backend   # ~5 seconds
sh test/run_tests.sh frontend  # ~6 seconds  
sh test/run_tests.sh e2e      # ~70 seconds (may fail without auth config)

# Test script supports optional arguments for different test configurations
```

**Alternative** - Run individual test scripts directly:
```bash
# Individual test scripts (if you prefer direct execution)
sh test/backend_tests.sh      # Backend tests directly
sh test/frontend_tests.sh     # Frontend tests directly  
sh test/e2e_tests.sh         # E2E tests directly

# The unified script above is provided for convenience
```

### Code Quality
```bash
# Python linting
source .venv/bin/activate && ruff check backend/

# Frontend linting
cd frontend && npm run lint
```

## Architecture Overview

### Current Architecture (Pre-Refactor)
- **Backend**: FastAPI with layered architecture
  - `main.py` - FastAPI app entry point with WebSocket endpoint
  - `infrastructure/app_factory.py` - Dependency injection hub
  - `application/chat/service.py` - Monolithic service (800+ lines, **being refactored**)
  - `core/` - Auth, middleware, utilities, OpenTelemetry logging
  - `domain/` - Business models and domain logic
  - `routes/` - API routes (config, admin, files, feedback)
  - `modules/` - Config management, LLM calling, file storage, MCP tools
  - `mcp/` - Individual MCP servers (**moving to root `/mcp`**)

- **Frontend**: React 19 + Vite + Tailwind CSS
  - Real-time chat via WebSocket
  - Settings panel for MCP server/tool selection
  - Builds to `dist/` directory served by backend

### Planned Refactoring (See refactor_plan.md)

**IMPORTANT**: The backend is undergoing a major refactoring to replace the monolithic `service.py` with focused managers:

**New Structure** (being implemented):
```
backend/managers/
├── service_coordinator.py       # Main orchestrator (replaces service.py)  
├── ui_callback_handler.py       # UI communication
├── logger_coordinator.py        # Logging coordination
├── auth/                        # Auth management (singleton)
├── session/                     # Pure state management (no execution logic)  
├── agent/                       # Agent execution logic
├── tools/                       # Tool execution and context injection
├── storage/                     # File storage abstraction
├── mcp/                         # Simplified MCP server management
├── rag/                         # RAG operations
└── admin/                       # Admin operations
```

**Key Refactoring Principles**:
- **Pure State Management**: Session manager handles only state, execution managers operate on sessions
- **Single Responsibility**: Each manager focused on one domain  
- **Happy Path Focus**: Clean readable code, strategic error boundaries
- **Security First**: Always validate user input, even if it adds complexity
- **Descriptive File Names**: Never use generic names like `manager.py`

### MCP Integration
- **Current**: MCP servers in `backend/mcp/`
- **Future**: Moving to root `/mcp/lib/` (shared libraries) and `/mcp/servers/`
- Individual MCP servers run via `cd server_dir && python main.py`
- Shared functionality will be in `/mcp/lib/` with path manipulation imports

### Key Dependencies
- **Transport**: WebSocket connection adapter abstracts FastAPI WebSocket
- **App Factory**: Central dependency injection for all managers
- **Domain Models**: Well-defined message, session, and tool models
- **OpenTelemetry**: Structured JSON logging with tracing (`core/otel_config.py`)

## Development Notes

### Critical Restrictions
- **ALWAYS use `sh agent_start.sh`** to start the application (not manual uvicorn commands)
- **NEVER use `uvicorn --reload`** - causes development problems  
- **NEVER use `npm run dev`** - has WebSocket connection issues
- **PREFER `sh test/run_tests.sh`** for testing (unified script for convenience, individual scripts also available)
- **ALWAYS use `uv`** for Python packages, not pip
- **NEVER CANCEL builds or tests** - they may take time but must complete

### File Limits and Conventions
- **Maximum 400 lines per file** for maintainability
- **Use descriptive file names** - avoid generic names like `manager.py`
- **Follow security-first approach** - validate all user input
- **Strategic error handling** - error boundaries, not defensive try/catch everywhere

### Key Files and Patterns
- **Entry Point**: `backend/main.py` (FastAPI app, stays unchanged in refactor)
- **DI Hub**: `infrastructure/app_factory.py` 
- **Core Services**: Currently in monolithic `application/chat/service.py` (**being refactored**)
- **Config**: Pydantic-based configuration with `.env` support
- **Logging**: OpenTelemetry with structured JSON output to `logs/app.jsonl`

### Testing Strategy
- Backend tests in `backend/tests/` using pytest
- Frontend tests using Vitest 
- E2E tests may fail without proper auth configuration
- All tests must complete - typical runtime: backend(~5s), frontend(~6s), e2e(~70s)

### Container Support
- Docker builds may fail due to SSL cert issues in some environments
- Use local development approach as primary method
- Container builds take 5-10 minutes first time

This codebase is transitioning from a monolithic service architecture to a clean manager-based architecture. When working with the code, refer to `refactor_plan.md` for the target architecture and development philosophy.