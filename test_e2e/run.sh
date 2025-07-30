#!/bin/bash

# Automated E2E Test Runner
# This script checks setup and runs tests in a fully automated way

set -e  # Exit on any command failure
set -o pipefail  # Exit on pipe failures

# Function to run commands with timeout
run_with_timeout() {
    local timeout=$1
    shift
    timeout "$timeout" "$@" || {
        echo "❌ Command timed out after ${timeout}s: $*"
        exit 1
    }
}

# Function to cleanup on exit
cleanup() {
    echo "🧹 Cleaning up..."
    # Kill any hanging processes if needed
    pkill -f "npm install" 2>/dev/null || true
    pkill -f "playwright install" 2>/dev/null || true
}
trap cleanup EXIT

echo "🚀 Starting Automated E2E Test Runner"
echo "======================================"

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Please run this script from the test_e2e directory."
    exit 1
fi

echo "📦 Installing test dependencies..."
run_with_timeout 60 npm install --silent || {
    echo "❌ Failed to install npm dependencies"
    exit 1
}

echo "🌐 Installing Playwright browsers..."
run_with_timeout 300 npx playwright install --with-deps > /dev/null 2>&1 || {
    echo "⚠️  Browser installation had warnings, trying without deps..."
    run_with_timeout 180 npx playwright install > /dev/null 2>&1 || {
        echo "❌ Failed to install Playwright browsers"
        exit 1
    }
}

echo "🔧 Checking if backend server is running..."
if run_with_timeout 10 curl -s http://localhost:8000/api/config > /dev/null; then
    echo "✅ Backend server is running on port 8000"
else
    echo "❌ Backend server not detected on port 8000"
    echo "   Please start the server first:"
    echo "   cd ../backend && python -c \"import uvicorn; from main import app; from config import config_manager; uvicorn.run(app, host='0.0.0.0', port=config_manager.app_settings.port, reload=False)\" &"
    exit 1
fi

echo "🏗️  Checking if frontend is built..."
if [ -d "../frontend/dist" ]; then
    echo "✅ Frontend build directory found"
else
    echo "⚠️  Frontend not built. Building now..."
    cd ../frontend || {
        echo "❌ Failed to change to frontend directory"
        exit 1
    }
    run_with_timeout 120 npm run build > /dev/null 2>&1 || {
        echo "❌ Failed to build frontend"
        exit 1
    }
    cd ../test_e2e || {
        echo "❌ Failed to return to test_e2e directory"
        exit 1
    }
    echo "✅ Frontend built successfully"
fi

echo "🧹 Cleaning up old test results..."
rm -rf test-results/ || true
rm -rf screenshots/*.png || true

echo "📸 Creating screenshots directory..."
mkdir -p screenshots || {
    echo "❌ Failed to create screenshots directory"
    exit 1
}

echo ""
echo "🧪 Running E2E Tests (Headless Mode)"
echo "===================================="

# Set environment variables for headless operation
export PWDEBUG=0
export CI=true

# Run tests with timeout and proper error handling
echo "Starting test execution with 2 minute timeout..."
if run_with_timeout 120 npx playwright test \
    --config=playwright.config.js \
    --reporter=list \
    --timeout=10000 \
    --retries=1 \
    --workers=1; then
    
    echo ""
    echo "📊 Test Results Summary"
    echo "======================"
    echo "✅ All tests passed!"
    
    echo ""
    echo "📸 Screenshots captured:"
    if [ -d "screenshots" ] && [ "$(ls -A screenshots/ 2>/dev/null)" ]; then
        ls -la screenshots/
    else
        echo "   No screenshots found (tests may have passed without capturing)"
    fi
    
    echo ""
    echo "📝 Test artifacts:"
    echo "   - Test results: test-results/"
    echo "   - Screenshots: screenshots/"
    echo "   - HTML report: npx playwright show-report"
    
    echo ""
    echo "🎉 E2E Test Run Complete!"
    
else
    echo ""
    echo "📊 Test Results Summary"
    echo "======================"
    echo "❌ Some tests failed or timed out!"
    echo ""
    echo "🔍 Debug information:"
    echo "   - Check test-results/ for detailed logs"
    echo "   - Screenshots available in screenshots/"
    echo "   - Run 'npx playwright show-report' for detailed HTML report"
    exit 1
fi