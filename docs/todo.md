# TODO and Ideas

Future enhancements and feature ideas for the Chat UI application.

## MCP Server Enhancements

### Session Management
- If a special `session_start` function exists, invoke it when a user first starts interacting with the server
- Inject session and user name in tool calling, similar to the file setup

### MCP Marketplace & Selection ✅
- ✅ Create `/marketplace` route showing different possible MCPs
- ✅ Allow selecting MCPs, only show user-selected MCPs on main UI
- ✅ Save selections to browser memory
- Future: Get more info about each MCP (ratings, downloads)
- Future: Persistent storage in database instead of browser memory

### MCP Server Configuration Fix
- Currently MCP servers need to be in the mcp folder with same folder name as the MCP folder
- **TODO**: Make it properly use the "command" in mcp.json, so path to MCP server can be whatever
- **TODO**: Enable HTTP MCP servers for connecting to remote MCP servers

### Custom Prompting via MCP
- Design pattern for fastmcp: MCPs expose special system prompts in marketplace
- Examples: "Think like a financial tech wizard", "You are an expert dog trainer"
- Probably in `handle_chat_message` in message-processor, override system prompt for first message
- Track different MCP services: Tools, Resources, Templates, Prompts

Example MCP prompt implementation:
```python
from fastmcp import FastMCP
from fastmcp.prompts.prompt import Message, PromptMessage, TextContent

mcp = FastMCP(name="PromptServer")

@mcp.prompt
def ask_about_topic(topic: str) -> str:
    """Generates a user message asking for an explanation of a topic."""
    return f"Can you please explain the concept of '{topic}'?"

@mcp.prompt
def generate_code_request(language: str, task_description: str) -> PromptMessage:
    """Generates a user message requesting code generation."""
    content = f"Write a {language} function that performs the following task: {task_description}"
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
```

### User Info in MCP Server
- Implement user elicitation mechanism for MCP clients
- Reference: https://gofastmcp.com/clients/elicitation

## UI Enhancements

### Single Line Banners ✅
- ✅ Feature can be on/off via .env file setting
- ✅ Hit a URL with custom API key from .env, reads host name
- ✅ Route: `{endpoint host}/banner` returns JSON with list of banner messages
- ✅ Sys admin can quickly add messages like "Known outage on RAG server 5 detected"
- ✅ Each message on new line, full width, stacks below existing features
- ✅ Mock implementation in sys-admin-mock folder

### Canvas Tool Enhancement ✅
- ✅ Let user adjust canvas width to take more or less screen compared to chat UI

### UI Modification by MCP ✅
- ✅ Allow MCP to modify the UI
- ✅ Canvas area modification
- ✅ If MCP returns JSON with special `custom_html` field, inject this
- ✅ Inject as custom element

## Architecture Improvements

### Authentication & Authorization
- **Security Issue**: User could spoof another user's email in WebSocket
- **TODO**: Set up JWT to match to their email, check JWT to get real user name
- **TODO**: Use FastAPI 'depends' for this authentication

### Tool Pipeline
- **TODO**: Pipeline where you force backend to use a tool, skip LLM tool invocation and just call it directly

### Naming Convention Fix
- **Issue**: For MCP server names, don't use underscore in folder or file
- **Fix**: Use camelCase instead (e.g., `myCoolServer` not `mycool_server`)
- **Requirement**: Folder name needs to match server name

## Testing & Quality

### Unit Testing
- ✅ **In Progress**: Add 10 unit tests for backend
- ✅ **In Progress**: Add 10 unit tests for frontend
- Focus on basic unit tests, not integration tests

### Documentation ✅
- ✅ **Completed**: Reorganize .md files into docs/ folder
- ✅ **Completed**: Minimal README.md pointing to docs
- ✅ **Completed**: Separation of concerns: frontend, backend, MCP dev, quick dev, quick start, todo
- ✅ **Completed**: Emphasize use of 'uv' as Python package manager

## Advanced Features

### File Return Handling ✅
- ✅ If file returned type is image or has `custom_html` field, render in addition to allowing download

### Agent Mode Enhancements
- Improve multi-step reasoning interface
- Better progress tracking
- Save agent reasoning chains

### RAG Improvements
- Better document indexing
- Support for more file types
- Improved search relevance

## Configuration Enhancements

### Dynamic Configuration
- Hot reload of configuration without restart
- Per-user configuration overrides
- Configuration validation UI

### Model Management
- Model performance monitoring
- Cost tracking per model/user
- Model fallback on failures

## Performance & Scalability

### WebSocket Improvements
- Connection pooling
- Better error recovery
- Message queuing for offline users

### Caching
- Response caching for similar queries
- Model output caching
- Static asset optimization

### Load Balancing
- Multiple backend instances
- Session affinity
- Health check endpoints

## Security Enhancements

### Enhanced Authentication
- Multi-factor authentication
- SAML/OIDC integration
- Session management

### Authorization Improvements
- Fine-grained permissions
- Role-based access control
- Audit logging

### Input Validation
- Content filtering
- Rate limiting per user
- Request sanitization

## Developer Experience

### Development Tools
- Better debugging tools
- Development dashboard
- Live configuration editing

### API Documentation
- Interactive API documentation
- SDK for custom integrations
- Webhook support

### Monitoring
- Application metrics
- User analytics
- Error tracking

## Deployment Improvements

### Container Orchestration
- Kubernetes deployment manifests
- Helm charts
- Auto-scaling configuration

### CI/CD Pipeline
- Automated testing
- Deployment pipelines
- Environment promotion

### Monitoring & Logging
- Centralized logging
- Application metrics
- Health monitoring

## Integration Ideas

### External Services
- GitHub integration for code-related queries
- Slack/Teams integration
- Email notifications

### Third-party Tools
- Jupyter notebook integration
- VS Code extension
- Browser extension

## Research Areas

### AI/ML Improvements
- Fine-tuning for specific use cases
- Multi-modal support (images, audio)
- Retrieval-augmented generation improvements

### Performance Research
- Model optimization
- Response time improvements
- Resource usage optimization

---

## Implementation Priorities

### High Priority
1. ✅ Documentation reorganization
2. ✅ Unit testing infrastructure
3. JWT authentication for WebSocket security
4. MCP server path configuration fix

### Medium Priority
1. HTTP MCP server support
2. Enhanced agent mode
3. Better error handling and recovery
4. Performance monitoring

### Low Priority
1. Advanced integrations
2. Multi-modal support
3. Advanced analytics
4. Third-party tool integrations

---

**Note**: Items marked with ✅ have been completed or are in progress.