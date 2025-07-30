#!/bin/bash

# Setup script for E2E tests
# This script prepares the environment for running the end-to-end tests

set -e

echo "🚀 Setting up E2E Test Environment"

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Please run this script from the test_e2e directory."
    exit 1
fi

echo "📦 Installing test dependencies..."
npm install

echo "🌐 Installing Playwright browsers..."
npx playwright install

echo "🔧 Checking if backend server is running..."
if curl -s http://localhost:8000/api/config > /dev/null; then
    echo "✅ Backend server is running on port 8000"
else
    echo "⚠️  Backend server not detected on port 8000"
    echo "   Please start the server with:"
    echo "   cd ../backend && python -c \"import uvicorn; from main import app; from config import config_manager; uvicorn.run(app, host='0.0.0.0', port=config_manager.app_settings.port, reload=False)\" &"
fi

echo "🏗️  Checking if frontend is built..."
if [ -d "../frontend/dist" ]; then
    echo "✅ Frontend build directory found"
else
    echo "⚠️  Frontend not built. Building now..."
    cd ../frontend
    npm run build
    cd ../test_e2e
    echo "✅ Frontend built successfully"
fi

echo ""
echo "🎉 E2E Test Environment Setup Complete!"
echo ""
echo "Run tests with:"
echo "  npm test              # Run all tests"
echo "  npm run test:ui       # Run with interactive UI"
echo "  npm run test:headed   # Run in visible browser"
echo ""