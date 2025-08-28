# Backend Refactoring Plan

## Development Philosophy

**Focus on the Happy Path**: This refactoring prioritizes clean, readable code that clearly expresses the intended functionality. Code should be optimized for human understanding and maintainability.

### Error Handling Strategy
- **Minimal Try/Catch**: Avoid wrapping every function call in try/catch blocks - this hurts readability
- **Strategic Error Boundaries**: Place error handling at logical boundaries (service coordinator, manager entry points)
- **Always Use Traceback**: When catching exceptions, always log with traceback for debugging
- **Let It Fail Fast**: Allow unexpected errors to bubble up to error boundaries rather than catching everywhere
- **Example Pattern**:
  ```python
  # Good: Clean happy path, error boundary at coordinator level
  def execute_tool(tool_name: str, args: dict) -> ToolResult:
      schema = get_tool_schema(tool_name)  # Let this fail if tool doesn't exist
      result = call_tool(schema, args)     # Let this fail if call fails
      return process_result(result)        # Let this fail if processing fails
  
  # Error boundary in coordinator:
  try:
      result = tool_manager.execute_tool(tool_name, args)
  except Exception as e:
      logger.error("Tool execution failed", exc_info=True)  # Always use traceback
      return error_response(str(e))
  ```

**Principle**: Write code for the case when everything works correctly. Handle errors at strategic points where you can take meaningful action.

### Security-First Approach
**Never Trust User Input**: Security is paramount and takes precedence over code simplicity. All user-provided values must be validated, sanitized, and treated as potentially malicious.

#### Security Requirements
- **Input Validation**: Validate all user inputs at entry points (routes, WebSocket messages)
- **Path Traversal Protection**: Never use user input directly in file paths
- **SQL/NoSQL Injection Prevention**: Use parameterized queries and proper escaping
- **Command Injection Prevention**: Never pass user input to system commands
- **File Upload Security**: Validate file types, sizes, and content
- **Authentication/Authorization**: Verify permissions at every access point
- **Data Sanitization**: Sanitize output to prevent XSS and injection attacks

#### Security Pattern Example
```python
# Good: Security validation at entry point
def handle_file_download(user: str, filename: str) -> FileResponse:
    # 1. Validate user authentication
    if not is_authenticated(user):
        raise HTTPException(403, "Authentication required")
    
    # 2. Validate and sanitize filename
    safe_filename = validate_filename(filename)  # Raises on path traversal
    if not safe_filename:
        raise HTTPException(400, "Invalid filename")
    
    # 3. Check user permissions
    if not user_can_access_file(user, safe_filename):
        raise HTTPException(403, "Access denied")
    
    # 4. Now proceed with happy path
    return serve_file(safe_filename)

def validate_filename(filename: str) -> Optional[str]:
    """Validate filename for security. Returns None if invalid."""
    if not filename or '..' in filename or '/' in filename:
        return None
    # Additional validation logic...
    return filename
```

**Principle**: Security validation is the exception to the "minimal error handling" rule. Always validate user input, even if it adds complexity.

## Overview

This document outlines a comprehensive refactoring plan to create cleaner separations and easier-to-understand code in the Chat UI backend. The goal is to break down the current monolithic service.py (800+ lines) into focused, single-responsibility managers while maintaining the working app factory pattern.

## Current State Analysis

### Strengths
- App factory pattern is working well
- Clean separation between domain models and infrastructure
- Good middleware structure
- Service layer abstracts business logic from transport

### Issues to Address
- Service.py is doing too much (800+ lines)
- MCP management is unnecessarily complex
- Tool and file management is scattered
- No clear session management abstraction
- Streaming and prompt checking code clutters the main flow
- Auth logic is spread across multiple files

## Proposed Directory Structure

Uses a **hybrid approach**: simple managers as single files, complex managers as modules. **Important**: All modules must use descriptive file names that indicate their purpose, not generic names like `manager.py`.

```
backend/
├── main.py                         # FastAPI app entry point (KEEP EXISTING)
├── managers/
NOTE: this was updaed so no individual files are in the managers
NOTE: a routes dir was added to put all the routes 
│   ├── __init__.py
│   ├── service_coordinator.py      # Main coordinator, transport-agnostic (SINGLE FILE)
│   ├── ui_callback_handler.py      # UI callback interface (SINGLE FILE)
│   ├── logger_coordinator.py       # Central logging (SINGLE FILE)
│   ├── app_factory.py               # App factory (SINGLE FILE)
│   ├── config/                      # Configuration management (MODULE)
│   │   ├── __init__.py
│   │   ├── config_manager.py       # Main ConfigManager class
│   │   └── config_models.py        # Configuration-related models
│   ├── auth/                       # Auth management (MODULE)
│   │   ├── __init__.py
│   │   ├── auth_manager.py         # Main AuthManager class
│   │   ├── permission_checker.py   # Permission validation logic
│   │   ├── token_handler.py        # Token management
│   │   ├── capability_tokens.py    # HMAC-signed tokens for file access
│   │   └── auth_models.py          # Auth-related models
│   ├── session/                    # Session management (MODULE)
│   │   ├── __init__.py
│   │   ├── session_manager.py      # Main SessionManager class
│   │   ├── conversation_history.py # History tracking logic
│   │   ├── context_handler.py      # Session context management
│   │   └── session_models.py       # Session-related models
│   ├── mcp/                        # MCP server management (MODULE)
│   │   ├── __init__.py
│   │   ├── mcp_manager.py          # Main MCPManager class
│   │   ├── server_registry.py      # Server class and discovery
│   │   ├── tool_registry.py        # Tool class and management
│   │   ├── prompt_registry.py      # Prompt class and management
│   │   └── mcp_models.py           # MCP-related models
│   ├── storage/                    # File storage management (MODULE)
│   │   ├── __init__.py
│   │   ├── storage_manager.py      # Main StorageManager class
│   │   ├── s3_storage.py          # S3 implementation
│   │   ├── filesystem_storage.py   # Local filesystem implementation
│   │   ├── storage_interfaces.py   # Storage interfaces
│   │   └── storage_models.py       # Storage-related models
│   ├── agent/                      # Agent execution (MODULE)
│   │   ├── __init__.py
│   │   ├── agent_manager.py        # Main AgentManager class
│   │   ├── strategy_handler.py     # ReAct, ThinkAct strategies
│   │   ├── event_emitter.py        # Agent event handling
│   │   └── agent_models.py         # Agent-related models
│   ├── tools/                      # Tool execution (MODULE)
│   │   ├── __init__.py
│   │   ├── tool_caller.py          # Main ToolCaller class
│   │   ├── context_injector.py     # Username, file context injection
│   │   ├── artifact_processor.py   # Tool result/artifact handling
│   │   └── tool_models.py          # Tool-related models
│   ├── rag/                        # RAG operations (MODULE)
│   │   ├── __init__.py
│   │   ├── rag_manager.py          # Main RAGManager class
│   │   ├── mcp_rag_client.py       # MCP RAG integration
│   │   ├── http_rag_client.py      # HTTP RAG integration
│   │   └── rag_models.py           # RAG-related models
│   └── admin/                      # Admin operations (MODULE)
│       ├── __init__.py
│       ├── admin_manager.py        # Main AdminManager class
│       ├── config_handler.py       # Configuration management
│       ├── monitoring.py           # System monitoring
│       ├── log_manager.py          # Log management
│       ├── feedback_handler.py     # User feedback collection/management
│       └── admin_models.py         # Admin-related models
├── middleware/
│   ├── __init__.py
│   ├── auth_middleware.py          # Auth middleware
│   ├── rate_limit_middleware.py    # Rate limiting
│   ├── logging_middleware.py       # Request logging
│   └── security_headers.py         # Security headers
├── routes/
│   ├── __init__.py
│   ├── config_routes.py           # App configuration
│   ├── admin_routes.py            # Admin functionality  
│   ├── files_routes.py            # File operations
│   ├── feedback_routes.py         # User feedback (KEEP EXISTING)
│   └── health_routes.py           # Health checks
└── mcp_servers/                   # MOVED TO ROOT - see MCP Organization section
```

## Manager Organization Strategy

### File Naming Convention
**Critical Rule**: All modules must use descriptive file names that clearly indicate their purpose. Avoid generic names like `manager.py`, `client.py`, or `handler.py` without context.

**Examples of Good Names:**
- `auth_manager.py` (not `manager.py`)
- `permission_checker.py` (not `checker.py`) 
- `s3_storage.py` (not `storage.py`)
- `conversation_history.py` (not `history.py`)

## common models

* common models which might be shared are in the  models folder

**Modules** - Complex managers needing multiple supporting classes:
- `auth/` - Authentication, permissions, tokens
- `session/` - Session lifecycle, history, context
- `mcp/` - Server/tool/prompt classes + discovery
- `storage/` - Multiple backends + interfaces
- `agent/` - Different strategies + event handling
- `tools/` - Execution + context injection + artifacts
- `rag/` - Multiple RAG implementations
- `admin/` - Configuration + monitoring + logs

## Detailed Manager Specifications

### 1. Service Coordinator (`service_coordinator.py`)
- **Purpose**: Main coordinator that orchestrates pure managers (execution-mode router)
- **Responsibilities**: 
  - Route chat requests to appropriate execution managers (plain, tools, agent, rag)
  - Coordinate session state updates across execution managers
  - Handle top-level errors and response formatting
  - Orchestrate manager interactions without containing business logic
- **Execution Flow**:
  - Get/create session via session manager
  - Route to appropriate execution manager (agent, tool, rag)
  - Execution managers interact with session manager for state
  - Return final response to transport layer
- **Dependencies**: Session manager, agent manager, tool caller, RAG manager
- **Key Principle**: Pure coordination - no business logic, just orchestration
- **Size Target**: <200 lines

### 2. Session Management (`managers/session/`) - Pure State Management
- **Main Class**: `SessionManager` in `session_manager.py`
- **Purpose**: Pure session lifecycle and state management (execution-agnostic)
- **Responsibilities**:
  - Session CRUD operations (create, read, update, delete)
  - Session lifecycle management
  - User-session association
  - Session metadata and timestamps
- **Supporting Files**:
  - `conversation_history.py` - Message history tracking and retrieval
  - `context_handler.py` - Session context (files, metadata) management
  - `session_models.py` - Session-related models and state structures
- **Interface**: Clean state management - execution managers interact with sessions, not vice versa
- **Key Principle**: Session manager knows nothing about agents, tools, or RAG - it's pure state

### 3. Auth Management (`managers/auth/`) - Singleton
- **Main Class**: `AuthManager` in `auth_manager.py` 
- **Purpose**: Single source of auth truth
- **Supporting Files**:
  - `permission_checker.py` - Permission validation logic
  - `token_handler.py` - Token management
  - `auth_models.py` - Auth-related models
- **Injectable**: Other modules can dependency inject and use

### 4. Agent Management (`managers/agent/`)
- **Main Class**: `AgentManager` in `agent_manager.py`
- **Purpose**: Agent execution logic (interacts with session state, doesn't manage it)
- **Responsibilities**:
  - Execute agent workflows (ReAct, ThinkAct)
  - Emit agent events to UI
  - Update session history with agent messages
  - Coordinate with tool caller for agent tool usage
- **Supporting Files**:
  - `strategy_handler.py` - ReAct, ThinkAct execution strategies
  - `event_emitter.py` - Agent event handling and UI notifications
  - `agent_models.py` - Agent-related models (events, results)
- **Session Interaction**: Reads session context, adds messages to history, doesn't manage session lifecycle
- **Interface**: `execute(session_id, messages, context, ...) -> AgentResult`

### 5. Tool Management (`managers/tools/`)
- **Main Class**: `ToolCaller` in `tool_caller.py`
- **Purpose**: Tool execution with context injection (reads session state for context)
- **Responsibilities**:
  - Execute individual tools and tool workflows
  - Inject username, file references, storage context
  - Process tool results and artifacts
  - Update session context with produced artifacts (via session manager)
- **Supporting Files**:
  - `context_injector.py` - Username, file context injection from session
  - `artifact_processor.py` - Tool result/artifact handling and session updates
  - `tool_execution.py` - Core tool execution logic (from current tool_utils.py)
  - `tool_models.py` - Tool-related models
- **Session Interaction**: Reads session context for injection, updates session with artifacts
- **Dependencies**: Storage manager interface, session manager interface

### 6. Storage Management (`managers/storage/`)
- **Main Class**: `StorageManager` in `storage_manager.py`
- **Purpose**: Abstract file storage operations
- **Supporting Files**:
  - `s3_storage.py` - S3 implementation
  - `filesystem_storage.py` - Local filesystem implementation
  - `storage_interfaces.py` - Storage interfaces
  - `storage_models.py` - Storage-related models

### 7. MCP Management (`managers/mcp/`) - Simplified
- **Main Class**: `MCPManager` in `mcp_manager.py`
- **Purpose**: Cleaner MCP server management
- **Supporting Files**:
  - `server_registry.py` - Server class and discovery
  - `tool_registry.py` - Tool class and management
  - `prompt_registry.py` - Prompt class and management
  - `mcp_models.py` - MCP-related models
- **Reduce Complexity**: Move transformation logic out, let consumers handle formats

### 8. RAG Management (`managers/rag/`)
- **Main Class**: `RAGManager` in `rag_manager.py`
- **Purpose**: Handle retrieval augmented generation
- **Supporting Files**:
  - `mcp_rag_client.py` - MCP RAG integration
  - `http_rag_client.py` - HTTP RAG integration
  - `rag_models.py` - RAG-related models

### 9. UI Callback Handler (`ui_callback_handler.py`)
- **Purpose**: Standardize UI communication
- **Responsibilities**:
  - Define callback interfaces
  - Handle different callback types (streaming, notifications, progress)
  - Abstract transport layer (WebSocket, HTTP, etc.)

### 10. Admin Management (`managers/admin/`)
- **Main Class**: `AdminManager` in `admin_manager.py`
- **Purpose**: Handle admin-specific operations
- **Supporting Files**:
  - `config_handler.py` - Configuration management
  - `monitoring.py` - System monitoring  
  - `log_manager.py` - Log management
  - `admin_models.py` - Admin-related models
- **Injectable**: Into admin routes

### 11. Logger Coordinator (`logger_coordinator.py`)
- **Purpose**: Central logging coordinator
- **Responsibilities**:
  - Structured logging
  - Log aggregation
  - Log filtering and routing

## Migration Strategy

The frontend is nice and will only need a few tweaks.Try not to modify it. 

[x] ### Phase 1: Extract Managers

Part A 
- move old version to old.backend, create 'backend' as a fresh start. 
- setup the main.py and an app factory. 
- setup the basic folder structures. 
-  set the config manager
- setup the llm manager. 
- wire up the app to work for the case of just llm calls with no tools, agents, or RAG
- focus on minimal implementation to just get things working with just the LLM doing chat. 
- preference for copying code from the old.backend, and then deleting unneed parts. Literally use the `cp` command. Only copy 1 file at a time. Under no circumstance shouuld you copy a whole fodler. 

part B
[x]* move the mcp to folder. 
[x]* setup the common mcp logging, and other utilities
[x]* setup the mcp manager
[x]* setup the tool managere
[x]* expose the /api/config to get hte list of tools

Part C 
* wire the service to allow tool calling from the mcps, so make a if tools in handle_chat_message
* setup the authentication to allowed mcp servers. Always check when getting the config, always check when a user tries to call a function.

## Key Changes from Current Structure

### Removals
- **Streaming Code**: Remove complex streaming logic from service layer
- **Prompt Checking**: Remove prompt injection risk checking as requested
- **Complex Transformations**: Simplify MCP data transformations

### Additions
- **Manager Layer**: Clear separation of concerns
- **Interfaces**: Well-defined contracts between components
- **Models per Module**: Organized data structures
- **Singleton Auth**: Centralized authentication

### Improvements
- **Single Responsibility**: Each manager handles one domain
- **Transport Agnostic**: Service manager doesn't know about WebSockets
- **Dependency Injection**: Clear dependencies via app factory
- **Testability**: Isolated components for better testing

## Benefits of This Structure

1. **Separation of Concerns**: Each manager has a single, clear purpose
2. **Testability**: Managers can be tested in isolation
3. **Maintainability**: Smaller, focused classes are easier to understand
4. **Extensibility**: New functionality can be added as new managers
5. **Dependency Injection**: Clear dependencies between components
6. **Transport Agnostic**: Service manager doesn't know about WebSockets
7. **Reusability**: Managers can be reused across different interfaces

## Implementation Notes

### Manager Size Guidelines
- Service Manager: <200 lines
- Individual Managers: 50-200 lines each
- Focus on single responsibility
- Clear interfaces between managers

### Application Entry Point

**Keep Existing Structure**: The current `backend/main.py` remains as the FastAPI application entry point. This file handles:
- FastAPI app creation and configuration
- WebSocket endpoint (`/ws`)
- Static file serving
- Route inclusion
- Application lifespan management
- Middleware setup

The refactoring primarily affects the service layer and below, not the application entry point.

### Dependency Flow & Session Interaction Pattern
```
backend/main.py (FastAPI app) -> app_factory -> service_coordinator -> [session/, agent/, tools/, etc.]
                                             -> [auth/ (singleton), storage/, mcp/, rag/, admin/]
```

### Pure State Management Pattern
```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│  Service            │    │     Session          │    │  Execution          │
│  Coordinator        │    │     Manager          │    │  Managers           │
│                     │    │  (Pure State)        │    │  (Business Logic)   │
├─────────────────────┤    ├──────────────────────┤    ├─────────────────────┤
│ • Route requests    │───▶│ • Session CRUD       │◀───│ • Agent Manager     │
│ • Orchestrate flow  │    │ • History tracking   │    │ • Tool Caller       │
│ • Handle errors     │    │ • Context management │    │ • RAG Manager       │
│ • No business logic │    │ • State persistence  │    │ • Storage Manager   │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘

Flow: Service Coordinator → Session Manager (get/create session)
      Service Coordinator → Execution Manager (process request)  
      Execution Manager → Session Manager (read context, add messages)
      Execution Manager → Service Coordinator (return result)
```

**Key Principle**: Session Manager is pure state - execution managers operate on sessions, sessions don't know about execution modes.

### Import Examples
```python
# Single file imports
from managers.service_coordinator import ServiceCoordinator
from managers.ui_callback_handler import UICallbackHandler
from managers.logger_coordinator import LoggerCoordinator

# Module imports - always use descriptive file names
from managers.auth.auth_manager import AuthManager
from managers.auth.permission_checker import PermissionChecker
from managers.session.session_manager import SessionManager
from managers.session.conversation_history import ConversationHistory
from managers.mcp.mcp_manager import MCPManager
from managers.mcp.server_registry import ServerRegistry
from managers.storage.storage_manager import StorageManager
from managers.storage.s3_storage import S3Storage
```

### Configuration
- Maintain current configuration system
- Managers receive config via dependency injection
- App factory remains the central wiring point

### What Stays the Same
- **`backend/main.py`**: FastAPI application entry point remains unchanged
- **App Factory Pattern**: Central dependency injection and wiring
- **Route Structure**: Existing route organization
- **Middleware**: Current middleware stack
- **Configuration System**: Existing config management

### What Changes
- **Service Layer**: Replace monolithic `service.py` with `service_coordinator.py` + managers
- **Business Logic**: Extract into focused managers
- **Complexity**: Remove streaming and prompt checking code
- **Organization**: Better separation of concerns

## MCP Organization

### Structure
MCP servers will be moved to the project root for better organization and future containerization:

```
/mcp/
├── lib/                           # Shared MCP libraries
│   ├── __init__.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── s3_client.py          # S3 operations
│   │   ├── file_handler.py       # File upload/download logic
│   │   └── storage_interfaces.py # Abstract interfaces
│   ├── responses/
│   │   ├── __init__.py
│   │   ├── response_types.py     # Standard MCP response formats
│   │   ├── error_responses.py    # Common error handling
│   │   └── file_responses.py     # File-specific response types
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging_utils.py      # MCP-specific logging
│   │   ├── validation.py         # Input validation helpers
│   │   └── auth_utils.py         # Common auth patterns
│   └── base/
│       ├── __init__.py
│       ├── mcp_server_base.py    # Optional base class
│       └── common_mixins.py      # Reusable functionality
└── servers/
    ├── calculator/
    │   └── main.py
    ├── filesystem/
    │   └── main.py
    └── ...
```

### Import Handling

**Current Implementation (Option 1)**: Since MCP servers are run by `cd`-ing into their directory and running `python main.py`, we'll use absolute path manipulation:

```python
# In each server's main.py
import sys
from pathlib import Path

# Add the mcp root to Python path
mcp_root = Path(__file__).parent.parent.parent  # Go up to /mcp
sys.path.insert(0, str(mcp_root))

# Now imports work from mcp root
from lib.storage.s3_client import S3Client
from lib.responses.response_types import ToolResponse
```

**Future Enhancement (Option 4)**: For better long-term maintainability, consider making the shared lib an installable package with its own `setup.py`. This would allow:
- `pip install -e /mcp/lib` for development
- Clean imports without path manipulation
- Easier testing and version management
- Better separation for containerization

### Benefits
- **Shared Functionality**: Common S3 access, response types, utilities
- **DRY Principle**: Eliminate code duplication across MCP servers
- **Future-Ready**: Easy to containerize or deploy separately
- **Consistent Interfaces**: Standard patterns across all MCPs

## Missing Components Integration

### Components to Integrate into Managers

**From `application/chat/utilities/`**:
- `error_utils.py` → Integrate into Service Coordinator error handling
- `file_utils.py` → Move to Storage Management module (`storage/file_operations.py`)
- `tool_utils.py` → Move to Tool Management module (`tools/tool_execution.py`)
- `notification_utils.py` → Move to UI Callback Handler (primary integration point)

**From `core/`**:
- `capabilities.py` → Move to Auth Management (`auth/capability_tokens.py`)
- `otel_config.py` → **KEEP IN CORE** - Logger Coordinator interfaces with this
- `http_client.py` → Move to RAG Management or expand as needed
- `prompt_risk.py` → **DELETE** (per requirement to remove prompt checking)

**Existing Routes**:
- `feedback_routes.py` → **KEEP** - Add feedback logic to Admin Management

### Infrastructure Components (Keep As-Is)
- `infrastructure/transport/websocket_connection_adapter.py` - Working well
- `infrastructure/app_factory.py` - Core dependency injection hub
- `core/otel_config.py` - Foundation for all logging
- `domain/` models - Well-organized domain objects

### Integration Notes

**UI Callback Handler** becomes the central notification system:
- Absorbs `notification_utils.py` functionality
- Handles WebSocket callbacks, event formatting
- File sanitization for UI responses
- Transport abstraction (WebSocket, HTTP, etc.)

**Storage Management** absorbs file utilities:
- File upload/download/deletion logic
- S3 operations and interfaces  
- Artifact processing from tools
- File context management

**Auth Management** gets capability tokens:
- HMAC-signed tokens for headless file access
- Integration with existing auth and permission systems
- Secure token generation and validation

This refactoring plan maintains the working FastAPI application structure and app factory pattern while creating much cleaner separations and easier-to-understand code. Each manager will be focused on a single concern, replacing the current 800+ line monolithic service.py.