# MCP Enhanced - Server Library

A server-side extension for the `@mcp.tool` decorator from fastmcp that provides filesystem sandboxing, response formatting, and security utilities according to the MCP v2.1 Enhanced Specification.

## Purpose

This library handles **server-side** responsibilities only. The client (chat-ui) handles:
- Username injection
- File path resolution  
- Timeout management and user notifications
- Size-based artifact routing (base64 vs S3)

## Quick Start

```python
from mcp_enhanced import enhanced_tool, create_mcp_response, artifact, secure_output_path

@enhanced_tool()
def analyze_data(filename: str, username: str) -> dict:
    """
    Analyze a CSV file. 
    
    filename: Already resolved by client to secure path like /tmp/{username}/input_files/data.csv
    username: Already injected by client with authenticated user identity
    """
    import pandas as pd
    
    # Process input file at client-resolved path
    df = pd.read_csv(filename)
    
    # Generate output in secure location
    output_path = secure_output_path(username, "summary.json")
    summary = {"rows": len(df), "columns": len(df.columns)}
    
    with open(output_path, 'w') as f:
        json.dump(summary, f)
    
    # Return MCP response with artifact path
    # Client will handle size-based routing (base64 vs S3)
    return create_mcp_response(
        results={"message": f"Analyzed {len(df)} rows"},
        artifacts=[artifact(
            name="summary.json",
            path=output_path,  # Client processes this path
            description="Data analysis summary"
        )]
    )
```

## Core Features

### 🔒 Filesystem Sandboxing

Automatically restricts file write operations to `/tmp/{username}/` through monkey patching:

```python
@enhanced_tool()  # Sandboxing enabled by default
def my_tool(filename: str, username: str) -> dict:
    # ✅ This works - writing to user directory
    output = secure_output_path(username, "result.txt")
    with open(output, 'w') as f:
        f.write("data")
    
    # ❌ This fails - writing outside user directory  
    with open("/etc/passwd", 'w') as f:  # SecurityViolationError
        f.write("hack attempt")
```

### 📝 Response Formatting

Simple utilities for creating MCP v2.1 compliant responses:

```python
# Basic response
return create_mcp_response(
    results={"status": "completed", "items_processed": 42}
)

# With artifacts
return create_mcp_response(
    results={"message": "Generated report"},
    artifacts=[
        artifact("report.pdf", "/tmp/user/report.pdf", description="Analysis report"),
        artifact("data.csv", "/tmp/user/data.csv", category="dataset")
    ]
)

# With deferred artifacts (drafts needing editing)
return create_mcp_response(
    results={"message": "Created draft"},
    deferred_artifacts=[
        deferred_artifact(
            "draft.md", 
            "/tmp/user/draft.md",
            reason="needs_editing",
            next_actions=["Complete TODO sections", "Review findings"]
        )
    ]
)
```

### 🛠 Utility Functions

```python
from mcp_enhanced import secure_output_path, list_user_files, get_file_info

# Create secure output paths
output = secure_output_path(username, "result.csv")  # /tmp/{username}/result.csv

# List files in user directory  
files = list_user_files(username, "*.csv")

# Get file metadata
info = get_file_info("/path/to/file.csv")  # Returns size, modified time, etc.
```

## API Reference

### Decorators

#### `@enhanced_tool(enable_sandbox=True)`
Main decorator providing filesystem sandboxing and response validation.

### Response Builders

#### `create_mcp_response(results, artifacts=None, ...)`
Create properly formatted MCP v2.1 response.

#### `artifact(name, path, mime=None, ...)`
Create artifact dictionary. Client processes the `path` field for size routing.

#### `deferred_artifact(name, path, reason=None, ...)`  
Create deferred artifact for files needing additional processing.

#### `error_response(message, reason="ExecutionError", ...)`
Create standardized error response.

### Utilities

#### `secure_output_path(username, filename) -> str`
Generate secure path in user's isolated directory.

#### `list_user_files(username, pattern="*") -> List[str]`
List files in user's directory matching pattern.

#### `normalize_filename(filename) -> str`
Basic server-side filename sanitization.

## Security Model

### Filesystem Isolation
- **Write Operations**: Restricted to `/tmp/{username}/` only
- **Read Operations**: Allowed system-wide (client provides secure input paths)
- **Sandboxing**: Automatic via monkey patching of file operations
- **Validation**: Server-side validation as safety net

### User Separation
- Each user gets isolated `/tmp/{username}/` directory
- Username provided by client (already authenticated)
- Tools cannot access other users' files

## Examples

See `examples.py` for complete working examples:

1. **Basic CSV Analysis**: Process file and generate summary
2. **Multiple File Merging**: Combine multiple CSV files  
3. **Multi-format Reports**: Generate both JSON and HTML outputs
4. **Draft Creation**: Create files that need user editing
5. **Batch Processing**: Process data with multiple outputs

## Client Integration

This library is designed to work with the chat-ui client which handles:

1. **Username Injection**: Automatically injects authenticated user identity
2. **File Resolution**: Resolves user file names to secure paths like `/tmp/{username}/input_files/file.csv`
3. **Artifact Processing**: Converts artifact paths to base64 (small files) or S3 (large files)
4. **Timeout Management**: Handles timeouts and progress notifications
5. **Security**: Additional client-side security and validation

## Testing

```python
from mcp_enhanced.examples import run_server_examples

# Run built-in examples
run_server_examples()

# Test your own tools
@enhanced_tool()
def my_tool(filename: str, username: str) -> dict:
    return create_mcp_response(results={"status": "ok"})

# Simulate client behavior  
result = my_tool("/tmp/testuser/input_files/data.csv", "testuser")
```

## Development Guidelines

1. **File Size Agnostic**: Don't worry about file sizes - return paths, let client handle routing
2. **Security First**: Always use `secure_output_path()` for generated files  
3. **Username Trust**: Trust the client-injected username parameter
4. **Response Format**: Always return properly formatted MCP responses
5. **Error Handling**: Use provided error response utilities

## License

This library is part of the Chat UI project and follows the same licensing terms.