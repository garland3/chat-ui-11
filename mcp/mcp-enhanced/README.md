# MCP Enhanced - Server Library

A server-side extension for the `@mcp.tool` decorator from fastmcp that provides filesystem sandboxing, response formatting, and security utilities according to the MCP v2.1 Enhanced Specification.

## Installation

```bash
# From PyPI (when published)
pip install mcp-enhanced

# From source
pip install -e .

# With development dependencies
pip install -e ".[dev]"

# With examples dependencies
pip install -e ".[examples]"
```

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

## Documentation

See the [docs](./docs/) directory for detailed documentation:

- [README.md](./docs/README.md) - Complete API reference and examples
- Run examples: `mcp-enhanced-examples` or `python -m examples.examples`

## Development

```bash
# Install in development mode
pip install -e ".[dev,examples]"

# Run tests
pytest

# Format code
black .
isort .

# Lint
flake8 .
```

## License

This library is part of the Chat UI project.