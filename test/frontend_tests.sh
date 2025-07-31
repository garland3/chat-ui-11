#!/bin/bash
set -e

echo "Running Frontend Tests..."
echo "================================="

# Use PROJECT_ROOT if set by master script, otherwise detect
if [ -z "$PROJECT_ROOT" ]; then
    if [ -d "/app" ]; then
        PROJECT_ROOT="/app"
    else
        PROJECT_ROOT="$(pwd)/.."
    fi
fi

# Set frontend directory path
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "Frontend directory: $FRONTEND_DIR"

# Change to frontend directory
cd "$FRONTEND_DIR"

# Install dependencies if in local environment
if [ "$ENVIRONMENT" = "local" ]; then
    echo "Installing dependencies for local environment..."
    npm ci
fi

# Run tests
echo "Running vitest..."
timeout 300 npm test -- --run

echo "Frontend tests completed successfully!"