# MCP Server UI Modification Capability

## Overview

This document describes the new capability that allows MCP (Model Context Protocol) servers to modify the Chat UI by returning custom HTML content in their tool responses.

## How It Works

### 1. MCP Server Implementation

MCP servers can now return a dictionary/JSON object with a special `custom_html` field:

```python
@mcp.tool
def create_custom_ui() -> Dict[str, Any]:
    """Create custom UI content."""
    custom_html = """
    <div style="background: #2d3748; padding: 20px; border-radius: 10px;">
        <h3>Custom UI from MCP Server</h3>
        <button onclick="alert('Hello from MCP!')">Click Me!</button>
    </div>
    """
    
    return {
        "content": "Custom UI created successfully!",
        "custom_html": custom_html,
        "success": True
    }
```

### 2. Backend Processing

The backend automatically detects `custom_html` fields in MCP tool responses:

- Parses MCP `CallToolResult` objects containing JSON
- Extracts the `custom_html` field if present
- Sends a `custom_ui` update to the frontend via WebSocket
- Logs the UI modification activity

### 3. Frontend Rendering

The frontend handles custom UI content in the Canvas panel:

- Receives `custom_ui` WebSocket messages
- Sanitizes HTML content using DOMPurify for security
- Renders the custom HTML in the Canvas panel
- Auto-opens the Canvas panel when custom content is received

## Security

- **HTML Sanitization**: All custom HTML is processed through DOMPurify to prevent XSS attacks
- **Safe Rendering**: Only safe HTML elements and attributes are allowed
- **Isolated Execution**: Custom JavaScript runs in the browser context but cannot access sensitive APIs

## UI Modification Types Supported

### 1. Interactive Elements
- Buttons with JavaScript onclick handlers
- Forms with validation and submission
- Interactive controls and widgets

### 2. Data Visualizations
- CSS-based charts and graphs
- Progress bars and indicators
- Custom styled data displays

### 3. Custom Layouts
- Responsive designs with CSS Grid/Flexbox
- Themed content areas
- Rich formatted content

## Example Use Cases

1. **Data Visualization Tools**: Generate interactive charts and graphs
2. **Form Builders**: Create custom input forms for data collection
3. **Dashboard Widgets**: Display real-time information in custom layouts
4. **Interactive Demos**: Showcase tool capabilities with live examples
5. **Rich Content Display**: Present formatted reports and documents

## Demo MCP Server

A demonstration server `ui_demo` is included with three example tools:

- `create_button_demo`: Interactive buttons with JavaScript
- `create_data_visualization`: CSS-based bar charts
- `create_form_demo`: Interactive forms with validation

## Files Modified

- `backend/utils.py`: Added custom_html detection and extraction
- `frontend/src/contexts/ChatContext.jsx`: Added custom UI state management
- `frontend/src/components/CanvasPanel.jsx`: Enhanced to render custom HTML
- `frontend/src/App.jsx`: Auto-open canvas for custom content
- `backend/mcp/ui_demo/main.py`: Demo MCP server implementation

## Future Enhancements

- **Iframe Support**: For more complex UI components
- **Callback Modification**: Allow MCP servers to influence chat behavior
- **Template System**: Predefined UI templates for common use cases
- **Real-time Updates**: WebSocket-based dynamic UI updates

## Developer Notes

- MCP servers should always include both `content` (for text response) and `custom_html` (for UI) fields
- Custom HTML should be responsive and work well within the Canvas panel constraints
- JavaScript in custom HTML has access to standard browser APIs but not Chat UI internals
- Test custom HTML thoroughly with DOMPurify sanitization to ensure compatibility