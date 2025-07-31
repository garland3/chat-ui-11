#!/bin/bash
set -e

echo "Running E2E Tests..."
echo "================================="

# Change to frontend directory where e2e tests are located
cd /app/frontend

# Check if there are any e2e test files to run
if find e2e/ -name "*.spec.js" -not -name "*.disabled" | grep -q .; then
    echo "Installing Playwright browsers..."
    npx playwright install --with-deps chromium

    # Run E2E tests
    echo "Running Playwright tests..."
    timeout 300 npm run test:e2e
else
    echo "No active E2E tests found (all tests are disabled)"
    echo "Skipping E2E test execution"
fi

echo "E2E tests completed successfully!"