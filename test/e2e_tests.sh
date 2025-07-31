#!/bin/bash
set -e

echo "Running E2E Tests..."
echo "================================="

# Use PROJECT_ROOT if set by master script, otherwise detect
if [ -z "$PROJECT_ROOT" ]; then
    PROJECT_ROOT=$(pwd)
fi

# Set frontend and backend directory paths
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "Frontend directory: $FRONTEND_DIR"
echo "Backend directory: $BACKEND_DIR"

# Build frontend
echo "Building frontend..."
cd "$FRONTEND_DIR"
export PATH=$(npm bin):$PATH
npm ci
npm run build

# Start backend in the background
echo "Starting backend server..."
cd "$BACKEND_DIR"
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for the server to be ready
echo "Waiting for backend server to start..."
sleep 10

# Run Playwright tests
echo "Running Playwright tests..."
cd "$FRONTEND_DIR"
# Install dependencies if in local environment
if [ "$ENVIRONMENT" = "local" ]; then
    echo "Installing dependencies for local environment..."
    npm ci
fi
if find e2e/ -name "*.spec.js" -not -name "*.disabled" | grep -q .; then
    echo "Installing Playwright browsers..."
    
    # In CI/CD, use --with-deps, locally just install
    if [ "$ENVIRONMENT" = "cicd" ]; then
        npx playwright install --with-deps chromium
    else
        npx playwright install chromium
    fi

    # Run E2E tests
    echo "Running Playwright tests..."
    timeout 300 npm run test:e2e
else
    echo "No active E2E tests found (all tests are disabled)"
    echo "Skipping E2E test execution"
fi


# Stop the backend server
echo "Stopping backend server..."
kill $BACKEND_PID

echo "E2E tests completed successfully!"