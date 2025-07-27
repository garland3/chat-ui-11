# TODO and Ideas

Future enhancements and feature ideas for the Chat UI application.

## MCP Server Enhancements


### MCP Server Configuration Fix
- Currently MCP servers need to be in the mcp folder with same folder name as the MCP folder
- **TODO**: Make it properly use the "command" in mcp.json, so path to MCP server can be whatever
- **TODO**: Enable HTTP MCP servers for connecting to remote MCP servers
- Track different MCP services: Tools, Resources, Templates, Prompts




### Naming Convention Fix
- **Issue**: For MCP server names, don't use underscore in folder or file
- **Fix**: Use camelCase instead (e.g., `myCoolServer` not `mycool_server`)
- **Requirement**: Folder name needs to match server name



-------------

ideas.  FUTURE


### Authorization Improvements

- Audit logging



### Session Management
- If a special `session_start` function exists, invoke it when a user first starts interacting with the server
- Inject session and user name in tool calling, similar to the file setup


### Caching
- Response caching for similar queries