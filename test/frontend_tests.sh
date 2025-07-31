#!/bin/bash
set -e

echo "Running Frontend Tests..."
echo "================================="

# Change to frontend directory
cd /app/frontend

# Run tests (dependencies should already be installed in container)
echo "Running vitest..."
timeout 300 npm test -- --run

echo "Frontend tests completed successfully!"