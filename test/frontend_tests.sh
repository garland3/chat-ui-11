#!/bin/bash
set -e

echo "Running Frontend Tests..."
echo "================================="

# Use PROJECT_ROOT if set by master script, otherwise detect
if [ -z "$PROJECT_ROOT" ]; then
    PROJECT_ROOT=$(pwd)
fi

# Set frontend directory path
FRONTEND_DIR="$PROJECT_ROOT/frontend3"

echo "Frontend directory: $FRONTEND_DIR"

# Change to frontend directory
cd "$FRONTEND_DIR"

# Install dependencies if in local environment
if [ "$ENVIRONMENT" = "local" ]; then
    echo "Installing dependencies for local environment..."
    npm ci
fi

# Run tests (ENVIRONMENT variable is already set by master script)
echo "Running vitest..."

# Make sure vitest is executable
if [ -f "node_modules/.bin/vitest" ]; then
    chmod +x node_modules/.bin/vitest
fi

# Add node_modules/.bin to PATH to ensure vitest is found
export PATH="$PWD/node_modules/.bin:$PATH"

# Run tests with proper configuration
timeout 300 npm test -- --run --config vite.config.test.js

echo "Frontend tests completed successfully!"