#!/bin/bash
set -e

echo "Running Backend Tests..."
echo "================================="

# Set up Python environment
export PYTHONPATH=/app/backend

# Change to backend directory
cd /app/backend

# Run pytest with verbose output
echo "Running pytest..."
python -m pytest tests/ -v --tb=short

echo "Backend tests completed successfully!"