# File MCP Injection Pattern

## Overview
This document describes the implementation of a file upload and injection system for MCP (Model Context Protocol) tools. The system allows users to upload files through the chat UI, which are then automatically injected into MCP tool calls that expect file data.

## Architecture Components

### 1. Frontend File Upload
- **Upload Button**: Small upload button in the chat UI
- **File Storage**: Files stored as filename -> base64 mapping in the frontend state
- **UI Behavior**: Hide base64 data in tool arguments/responses, show only filenames

### 2. Backend Session Management
- **Session Storage**: Each ChatSession maintains a `files` dictionary mapping filename -> base64
- **File Transmission**: Files sent to backend when chat messages are submitted
- **Memory Management**: Files persist for the duration of the chat session

### 3. MCP Tool Detection & Injection
- **Parameter Detection**: Identify MCP tools with `file_data_base64` and `filename` parameters
- **Auto-Injection**: Automatically inject base64 data when tool is called with a filename
- **Framework Integration**: Seamless integration with existing MCP framework

### 4. File Returns
- **Return Format**: MCPs can return files using `returned_file_name` and `returned_file_base64` keys
- **Download Handling**: Frontend provides download capabilities for returned files

## Implementation Pattern

### Frontend Upload Flow
```javascript
// User uploads file via button
const handleFileUpload = (file) => {
  const reader = new FileReader();
  reader.onload = (e) => {
    setUploadedFiles(prev => ({
      ...prev,
      [file.name]: e.target.result.split(',')[1] // Remove data URL prefix
    }));
  };
  reader.readAsDataURL(file);
};
```

### Backend Session Enhancement
```python
class ChatSession:
    def __init__(self, ...):
        # ... existing code ...
        self.uploaded_files: Dict[str, str] = {}  # filename -> base64
    
    def update_files(self, files: Dict[str, str]):
        """Update the session's file mapping"""
        self.uploaded_files.update(files)
```

### MCP Tool Injection
```python
async def call_mcp_tool(self, tool_name: str, args: dict, server_name: str):
    """Enhanced tool calling with file injection"""
    
    # Check if tool expects file injection
    if 'file_data_base64' in tool_signature and 'filename' in args:
        filename = args['filename']
        if filename in self.uploaded_files:
            args['file_data_base64'] = self.uploaded_files[filename]
    
    # Call the tool
    result = await mcp_client.call_tool(tool_name, args)
    
    # Handle returned files
    if isinstance(result, dict) and 'returned_file_base64' in result:
        # Process file return for frontend
        pass
    
    return result
```

### Prompt Enhancement
```python
def build_prompt_with_files(self, user_prompt: str) -> str:
    """Append available files to user prompt"""
    if not self.uploaded_files:
        return user_prompt
        
    file_list = "\n".join(f"- {filename}" for filename in self.uploaded_files.keys())
    return f"{user_prompt}\n\nFiles available:\n\n{file_list}"
```

## Example MCP Tool Integration

### Tool Definition
```python
@mcp.tool
def analyze_document(
    instructions: str,
    filename: str,
    file_data_base64: str = ""  # Auto-injected by framework
) -> Dict[str, Any]:
    """Process uploaded document with instructions"""
    # Tool implementation
    pass
```

### Tool Response with File Return
```python
return {
    "analysis": "Document analysis complete",
    "returned_file_name": "analysis_report.pdf",
    "returned_file_base64": encoded_report_data
}
```

## Security Considerations
- File size limits to prevent memory exhaustion
- File type validation in frontend
- Base64 data sanitization
- Session isolation for file access

## Benefits
1. **Seamless Integration**: Files automatically available to relevant MCP tools
2. **User Experience**: Simple upload button, automatic file availability listing
3. **Developer Experience**: MCP tools work transparently with file injection
4. **Memory Efficient**: Files stored per-session, cleaned up on disconnect
5. **Extensible**: Pattern works with any MCP tool that follows the convention

## Usage Flow
1. User uploads file(s) via upload button
2. Files stored in session state as filename -> base64 mapping
3. User sends message mentioning file or calling tool
4. System appends available files list to prompt
5. LLM calls MCP tool with filename parameter
6. Backend detects file injection candidate and injects base64 data
7. MCP tool processes file and optionally returns result file
8. Frontend handles file downloads and hides base64 from UI