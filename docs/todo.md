# TODO and Ideas

Future enhancements and feature ideas for the Chat UI application.

## MCP Server Enhancements

### Session Management
- If a special `session_start` function exists, invoke it when a user first starts interacting with the server
- Inject session and user name in tool calling, similar to the file setup

### MCP Server Configuration Fix
- Currently MCP servers need to be in the mcp folder with same folder name as the MCP folder
- **TODO**: Make it properly use the "command" in mcp.json, so path to MCP server can be whatever
- **TODO**: Enable HTTP MCP servers for connecting to remote MCP servers
- Track different MCP services: Tools, Resources, Templates, Prompts

### Custom Prompting via MCP
- Design pattern for fastmcp: MCPs expose special system prompts in marketplace
- Examples: "Think like a financial tech wizard", "You are an expert dog trainer"
- Probably in `handle_chat_message` in message-processor, override system prompt for first message

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

#

### Dynamic Configuration
- Hot reload of configuration without restart
- Per-user configuration overrides
- Configuration validation UI



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


### Authorization Improvements

- Audit logging

