# Help & Documentation

Welcome to the Chat UI! This application provides an advanced chat interface with AI models, enhanced by powerful tools and data sources.


test 1


## Quick Start

### Start a New Chat
Click "New Chat" button or press `Ctrl+Alt+N`

### Access Tools
Click the Settings icon in the header to open the tools panel

## Core Features

### RAG (Retrieval-Augmented Generation)
Connect your chats to external data sources for enhanced, context-aware responses.

- Click the menu icon to open data sources panel
- Select which documents/databases to include in your conversation
- Toggle "RAG Only" mode to query only your documents without LLM processing
- View source attribution to see which documents informed the response

### Tools & MCP Servers
Extend AI capabilities with specialized tools through Model Context Protocol (MCP) servers.

- Click the Settings icon to view available tools
- Built-in tools include file operations, calculations, and UI demos
- Tools can create interactive content in the Canvas panel
- Select specific tools in the marketplace for personalized experience

### MCP Store/Marketplace
Browse and select MCP servers that provide different capabilities.

- Navigate to `/marketplace` to browse available servers
- Select which MCP servers you want to use in your chats
- Each server provides specific tools and functionalities
- Your selections are saved and persist across sessions

## Tips & Best Practices

### Starting Fresh Conversations
For best results, start a new chat session when switching to a completely different topic. This prevents context confusion and ensures cleaner responses.

### Handling Errors
If you encounter errors or unexpected behavior, restart your chat session using the "New Chat" button. This clears the conversation history and resets the context.

### Keyboard Shortcuts
- `Ctrl+Alt+N` - Start new chat
- `Enter` - Send message
- `Shift+Enter` - New line in message

## Technical Documentation

### Building Your Own MCP Server
Create custom tools and functionality by developing your own MCP servers.

#### Special Return Types
- `custom_html` - Return custom HTML for Canvas rendering
- `file_path` - Reference files for download/display
- `content` - Standard text response
- `success` - Boolean indicating operation success

#### Custom HTML Example
```json
{
    "content": "Created interactive chart",
    "custom_html": "<div>Your HTML here</div>",
    "success": true
}
```

### UI Modification & Custom Prompts
Advanced customization options for developers.

- MCP servers can return custom HTML that renders in the Canvas panel
- All HTML is sanitized for security using DOMPurify
- JavaScript is supported for interactive elements
- Use custom prompts to modify AI behavior
- Create specialized tools for domain-specific tasks

### Development Resources
- `docs/mcp-development.md` - Comprehensive MCP development guide
- `docs/advanced-features.md` - Advanced features and examples
- `docs/configuration.md` - Configuration options
- `backend/mcp/` - Example MCP server implementations

## Agent Mode

Agent mode enables multi-step reasoning where the AI breaks down complex tasks into manageable steps.

### Features
- Step-by-step task breakdown and execution
- Visual progress tracking
- Integration with MCP tools during reasoning
- Ability to interrupt the reasoning process

**Note:** Agent mode availability depends on your configuration. Check with your administrator if this feature is not visible.

## Need More Help?

For additional information and detailed guides:

### Documentation
Check the `docs/` folder for comprehensive guides on setup, configuration, and development.

### Configuration
Refer to `.env.example` and configuration documentation for customization options.