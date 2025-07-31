#!/bin/bash
set -e

echo "Running E2E Tests..."
echo "================================="

# Change to frontend directory where e2e tests are located
cd /app/frontend

# Install Playwright browsers if needed
echo "Installing Playwright browsers..."
npx playwright install --with-deps chromium

# Run E2E tests
echo "Running Playwright tests..."
npm run test:e2e

echo "E2E tests completed successfully!"