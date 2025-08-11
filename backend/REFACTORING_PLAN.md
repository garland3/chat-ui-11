# Backend Modularization Plan

This document outlines a comprehensive plan to refactor the monolithic backend into a clean, modular, testable architecture with better separation of concerns.

## Current State Analysis

The backend currently has tightly coupled components in `main.py` with these functional areas:
- **MCP/Tools System** (`mcp_client.py`, `tool_executor.py`, `mcp/` directory)
- **RAG System** (`rag_client.py`) 
- **File Handling/S3** (`s3_client.py`, file operations in `session.py`)
- **Configuration** (`config.py`, config files)
- **LLM Calling** (`llm_caller.py`)
- **Session Management** (`session.py`, `message_processor.py`)

## Phase 1: Core Modularization (Foundation)

### Objective
Transform the monolithic backend into independent, testable modules with clear separation of concerns and CLI interfaces for each component.

### 1.1 Directory Structure Reorganization

```
backend/
├── modules/
│   ├── mcp_tools/           # MCP & Tool System
│   │   ├── __init__.py
│   │   ├── client.py        # MCPToolManager
│   │   ├── executor.py      # ToolExecutor 
│   │   ├── cli.py          # CLI interface
│   │   └── servers/        # MCP server configs/code
│   │
│   ├── rag/                # RAG System
│   │   ├── __init__.py
│   │   ├── client.py       # RAGClient
│   │   ├── cli.py          # CLI interface
│   │   └── models.py       # Pydantic models
│   │
│   ├── file_storage/       # File & S3 System
│   │   ├── __init__.py
│   │   ├── s3_client.py    # S3StorageClient
│   │   ├── manager.py      # FileManager
│   │   └── cli.py          # CLI interface
│   │
│   ├── config/             # Configuration System
│   │   ├── __init__.py
│   │   ├── manager.py      # ConfigManager
│   │   ├── models.py       # Pydantic config models
│   │   └── cli.py          # CLI interface
│   │
│   └── llm/                # LLM Calling System
│       ├── __init__.py
│       ├── caller.py       # LLMCaller
│       ├── models.py       # Response models
│       └── cli.py          # CLI interface
│
├── core/                   # Glue Layer
│   ├── __init__.py
│   ├── session.py          # Simplified session management
│   ├── orchestrator.py     # Coordinates modules
│   └── interfaces.py       # Common interfaces
│
├── main.py                 # Minimal FastAPI app
└── requirements.txt
```

### 1.2 Module Extraction Order

#### Step 1: Configuration Module
- Extract `config.py` → `modules/config/`
- Add CLI: `python -m backend.modules.config.cli validate`
- Add CLI: `python -m backend.modules.config.cli list-models`
- **Deliverable**: Independent configuration management

#### Step 2: File Storage Module  
- Extract `s3_client.py` → `modules/file_storage/`
- Extract file handling from `session.py` → `modules/file_storage/manager.py`
- Add CLI: `python -m backend.modules.file_storage.cli upload test.txt /path/to/file.txt`
- Add CLI: `python -m backend.modules.file_storage.cli list user@example.com`
- **Deliverable**: Independent file operations

#### Step 3: LLM Module
- Extract `llm_caller.py` → `modules/llm/`
- Add CLI: `python -m backend.modules.llm.cli call gpt-4 "Hello, how are you?"`
- Add CLI: `python -m backend.modules.llm.cli call-with-tools gpt-4 "Calculate 5+3" --tools calculator`
- **Deliverable**: Independent LLM calling

#### Step 4: RAG Module
- Extract `rag_client.py` → `modules/rag/`
- Add CLI: `python -m backend.modules.rag.cli discover-sources user@example.com`
- Add CLI: `python -m backend.modules.rag.cli query user@example.com datasource1 "What is ML?"`
- **Deliverable**: Independent RAG operations

#### Step 5: MCP Tools Module
- Extract `mcp_client.py` and `tool_executor.py` → `modules/mcp_tools/`
- Add CLI: `python -m backend.modules.mcp_tools.cli list-servers`
- Add CLI: `python -m backend.modules.mcp_tools.cli call-tool calculator add '{"a": 5, "b": 3}'`
- **Deliverable**: Independent tool execution

### 1.3 Clean Interfaces

Each module exposes clean, dependency-free interfaces:

```python
# modules/mcp_tools/__init__.py
from .client import MCPToolManager
from .executor import ToolExecutor, ExecutionContext

# modules/rag/__init__.py  
from .client import RAGClient
from .models import RAGResponse

# modules/file_storage/__init__.py
from .s3_client import S3StorageClient
from .manager import FileManager

# modules/llm/__init__.py
from .caller import LLMCaller
from .models import LLMResponse

# modules/config/__init__.py
from .manager import ConfigManager
```

### 1.4 Orchestrator Implementation

```python
# core/orchestrator.py
class MessageOrchestrator:
    def __init__(self):
        self.mcp_tools = MCPToolManager()
        self.rag = RAGClient() 
        self.file_storage = S3StorageClient()
        self.llm = LLMCaller()
        self.config = ConfigManager()
    
    async def process_message(self, session_context, message):
        # Coordinate between modules with minimal coupling
        pass
```

### Phase 1 Success Criteria
- [ ] All 5 modules extracted and working independently
- [ ] CLI tools for each module functional
- [ ] All existing functionality preserved
- [ ] Unit tests pass for each module in isolation
- [ ] Integration tests pass with new orchestrator
- [ ] Original `main.py` still works during transition

---

## Phase 2: Advanced Architecture (Enhancement)

### Objective
Add enterprise-grade patterns for resilience, observability, and maintainability.

### 2.1 Event-Driven Architecture

```python
# core/events.py
class EventBus:
    def __init__(self):
        self._handlers = defaultdict(list)
    
    def emit(self, event: str, data: Any):
        for handler in self._handlers[event]:
            handler(data)
    
    def on(self, event: str, handler: Callable):
        self._handlers[event].append(handler)

# Usage across modules
event_bus.emit('file_uploaded', {'filename': 'test.csv', 'user': 'user@example.com'})
event_bus.emit('tool_executed', {'tool': 'calculator', 'result': 8})
```

### 2.2 Dependency Injection Container

```python
# core/container.py
class Container:
    def __init__(self):
        self._services = {}
        self._singletons = {}
    
    def register(self, interface, implementation, singleton=True):
        self._services[interface] = (implementation, singleton)
    
    def get(self, interface):
        # Implementation details...
        pass
```

### 2.3 Plugin Architecture for MCP Servers

```python
# modules/mcp_tools/plugin_manager.py
class MCPPluginManager:
    def __init__(self):
        self.plugins = {}
    
    def discover_plugins(self, plugin_dir: str):
        # Auto-discover MCP servers from directory
        pass
    
    def load_plugin(self, name: str, path: Path):
        # Dynamic loading with isolation
        pass
```

### 2.4 Observability Layer

```python
# core/observability.py
class MetricsCollector:
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def track_duration(self, operation: str):
        # Decorator for tracking operation metrics
        pass

# Usage
@metrics.track_duration("llm_call")
async def call_llm(...):
    pass
```

### 2.5 Configuration Validation with Schemas

```python
# modules/config/schemas.py
from pydantic import BaseModel, Field, validator

class MCPServerSchema(BaseModel):
    name: str
    command: List[str]
    groups: List[str] = []
    
    @validator('command')
    def command_exists(cls, v):
        if not shutil.which(v[0]):
            raise ValueError(f"Command not found: {v[0]}")
        return v
```

### 2.6 Circuit Breaker Pattern

```python
# core/resilience.py
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        # Implementation for service resilience
        pass
    
    async def call(self, func, *args, **kwargs):
        # Circuit breaker logic
        pass
```

### 2.7 Background Task Queue

```python
# core/task_queue.py
class TaskQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.workers = []
    
    async def enqueue(self, task_func, *args, **kwargs):
        # Queue background tasks
        pass
```

### 2.8 Health Checks for Each Module

```python
# Each module gets a health.py
class MCPToolsHealth:
    async def check(self) -> Dict[str, Any]:
        return {
            'status': 'healthy',
            'active_servers': len(self.mcp_manager.clients),
            'failed_servers': self._count_failed_servers(),
            'last_check': datetime.utcnow().isoformat()
        }
```

### 2.9 Caching Layer

```python
# core/cache.py
class CacheManager:
    def __init__(self):
        self.cache = {}
        self.ttl = {}
    
    @cache_result(ttl=60)
    async def get_rag_response(query: str):
        return await rag_client.query(query)
```

### 2.10 Enhanced Testing Infrastructure

```python
# tests/fixtures.py
@pytest.fixture
async def mock_container():
    container = Container()
    container.register('llm', MockLLMCaller)
    container.register('rag', MockRAGClient)
    return container

@pytest.fixture  
def isolated_mcp_server():
    # Spin up test MCP server in isolation
    pass
```

### 2.11 Module Registry System

```python
# core/registry.py
class ModuleRegistry:
    def __init__(self):
        self.modules = {}
    
    def register_module(self, name: str, module_class):
        self.modules[name] = module_class
    
    def discover_modules(self, modules_dir: str):
        # Auto-discover and register modules
        pass
```

### Phase 2 Success Criteria
- [ ] Event-driven communication implemented
- [ ] Dependency injection working across all modules
- [ ] Circuit breakers protecting external service calls
- [ ] Comprehensive health checks and metrics
- [ ] Background task processing implemented
- [ ] Plugin architecture for MCP servers
- [ ] Enhanced testing with mocks and fixtures
- [ ] Caching layer improving performance
- [ ] Module auto-discovery working

---

## Migration Strategy

### Phase 1 Migration (4-6 weeks)
1. **Week 1-2**: Extract config and file storage modules
2. **Week 3-4**: Extract LLM and RAG modules  
3. **Week 5-6**: Extract MCP tools module, implement orchestrator

### Phase 2 Enhancement (6-8 weeks)
1. **Week 1-2**: Implement event bus and dependency injection
2. **Week 3-4**: Add observability, health checks, and circuit breakers
3. **Week 5-6**: Implement caching, background tasks, and plugin system
4. **Week 7-8**: Enhanced testing infrastructure and documentation

### Risk Mitigation
- Keep existing `main.py` working throughout Phase 1
- Gradual migration with feature flags
- Comprehensive testing at each step
- Rollback plan for each module extraction
- Performance monitoring during migration

### Success Metrics
- **Testability**: Each module has >90% test coverage
- **Independence**: Each module can run standalone via CLI
- **Performance**: No degradation in response times
- **Maintainability**: New features can be added to single modules
- **Reliability**: Circuit breakers prevent cascading failures

## Final Architecture Benefits

1. **Independent Testing**: Each module runs in isolation
2. **Clear Separation**: No cross-dependencies between modules  
3. **CLI Tools**: Debug/test individual components easily
4. **Easier Development**: Work on one module without affecting others
5. **Better Testing**: Unit test each module independently
6. **Deployment Flexibility**: Could deploy modules as separate services
7. **Enterprise Patterns**: Resilience, observability, and caching built-in
8. **Plugin Architecture**: Easy to add new MCP servers and capabilities