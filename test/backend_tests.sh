#!/bin/bash
set -e

echo "Running Backend Tests..."
echo "================================="

# Use PROJECT_ROOT if set by master script, otherwise detect
if [ -z "$PROJECT_ROOT" ]; then
    if [ -d "/app" ]; then
        PROJECT_ROOT="/app"
    else
        PROJECT_ROOT="$(pwd)/.."
    fi
fi

# Set up Python environment and paths
BACKEND_DIR="$PROJECT_ROOT/backend"
export PYTHONPATH="$BACKEND_DIR"

echo "Backend directory: $BACKEND_DIR"
echo "PYTHONPATH: $PYTHONPATH"

# Change to backend directory
cd "$BACKEND_DIR"

# Run pytest with verbose output
echo "Running pytest..."
timeout 300 python -m pytest tests/ -v --tb=short

echo "Backend tests completed successfully!"