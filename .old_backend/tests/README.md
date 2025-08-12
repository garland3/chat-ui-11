# Backend Tests

This directory contains unit tests for the backend components.

## Running Tests

```bash
cd backend
pytest tests/ -v
```

## Test Structure

- `test_config.py` - Configuration system tests
- `test_utils.py` - Utility function tests  
- `test_auth_utils.py` - Authorization utility tests
- `test_http_client.py` - HTTP client tests
- `test_callbacks.py` - Callback function tests
- `test_prompt_utils.py` - Prompt utility tests
- `test_mcp_client.py` - MCP client tests
- `test_banner_client.py` - Banner client tests
- `test_rag_client.py` - RAG client tests
- `test_message_processor.py` - Message processor tests

## Test Coverage

These are basic unit tests focused on individual components, not integration tests.