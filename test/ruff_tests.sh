#!/bin/bash
set -e

echo "Running Ruff checks..."

# Define directories to check
BACKEND_DIR="backend"
MCP_DIR="mcp"
TEST_FAILED=0

# Check for Python files in backend directory
if [ -d "$BACKEND_DIR" ]; then
    echo "Checking backend code with Ruff..."
    # Use ruff format to check formatting
    ruff format "$BACKEND_DIR" --check || TEST_FAILED=1
    # Use ruff check to check linting
    ruff check "$BACKEND_DIR" || TEST_FAILED=1
else
    echo "Backend directory not found, skipping Ruff checks for backend."
fi

# Check for Python files in mcp directory
if [ -d "$MCP_DIR" ]; then
    echo "Checking mcp code with Ruff..."
    # Use ruff format to check formatting
    ruff format "$MCP_DIR" --check || TEST_FAILED=1
    # Use ruff check to check linting
    ruff check "$MCP_DIR" || TEST_FAILED=1
else
    echo "MCP directory not found, skipping Ruff checks for mcp."
fi

if [ "$TEST_FAILED" -eq 1 ]; then
    echo "Ruff checks FAILED."
    exit 1
else
    echo "Ruff checks completed successfully."
fi
