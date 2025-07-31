#!/bin/bash
set -e

echo "Running E2E Tests..."
echo "================================="

# Use PROJECT_ROOT if set by master script, otherwise detect
if [ -z "$PROJECT_ROOT" ]; then
    if [ -d "/app" ]; then
        PROJECT_ROOT="/app"
    else
        PROJECT_ROOT="$(pwd)/.."
    fi
fi

# Set frontend directory path where e2e tests are located
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "Frontend directory: $FRONTEND_DIR"

# Change to frontend directory
cd "$FRONTEND_DIR"

# Install dependencies if in local environment
if [ "$ENVIRONMENT" = "local" ]; then
    echo "Installing dependencies for local environment..."
    npm ci
fi

# Check if there are any e2e test files to run
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

echo "E2E tests completed successfully!"