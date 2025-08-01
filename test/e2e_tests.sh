#!/bin/bash
set -euo pipefail

trap 'rc=$?; echo "🧹 Cleaning up..."; [[ -n "${BACKEND_PID-}" ]] && { echo "Killing backend process (PID: $BACKEND_PID)"; kill "${BACKEND_PID}" 2>/dev/null || true; }; exit $rc' EXIT

echo "Running E2E Tests..."
echo "================================="

# Resolve project root
: "${PROJECT_ROOT:=$(pwd)}"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "Project root: $PROJECT_ROOT"
echo "Frontend directory: $FRONTEND_DIR"
echo "Backend directory: $BACKEND_DIR"

# Ensure frontend dependencies are installed once
cd "$FRONTEND_DIR"
export PATH="$FRONTEND_DIR/node_modules/.bin:$PATH"
echo "Current PATH: $PATH"

echo "Installing frontend dependencies..."
npm install

# Verify vite exists (local)
if ! command -v vite >/dev/null 2>&1; then
    echo "vite binary not found in node_modules/.bin. Listing installed packages for debugging:"
    ls -1 node_modules/.bin || true
    echo "Attempting to install vite explicitly..."
    npx vite --version || {
        echo "Failed to get vite. Check that 'vite' is declared in package.json dependencies/devDependencies."
        exit 1
    }
fi

echo "Building frontend..."
npx vite build

# Start backend with startup validation
echo "Starting backend server..."
cd "$BACKEND_DIR"

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 is already in use. Attempting to continue with existing service..."
    # Get the PID of the existing process for potential cleanup
    EXISTING_PID=$(lsof -Pi :8000 -sTCP:LISTEN -t 2>/dev/null | head -1)
    echo "ℹ️  Existing service PID: ${EXISTING_PID:-unknown}"
else
    echo "Starting uvicorn server..."
    uvicorn main:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    
    # Give the server a moment to start
    sleep 3
    
    # Verify the process started successfully
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "❌ Backend process failed to start or died immediately"
        exit 1
    fi
    
    echo "✅ Backend server started successfully (PID: $BACKEND_PID)"
fi

# Wait for backend to be healthy (probe)
echo "Waiting for backend to become ready..."
MAX_RETRIES=15
RETRY_INTERVAL=2
SUCCESS=false
for i in $(seq 1 $MAX_RETRIES); do
    if curl --silent --fail http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
        echo "Backend is up (after $i attempt(s))"
        SUCCESS=true
        break
    fi
    echo "  [${i}/${MAX_RETRIES}] backend not ready yet, sleeping ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done
if ! $SUCCESS; then
    echo "Backend failed to become ready in time. Dumping last few lines of backend process (if any):"
    ps -p "$BACKEND_PID" && kill -0 "$BACKEND_PID" 2>/dev/null || true
    exit 1
fi

# Run Playwright tests
echo "Running Playwright tests..."
cd "$FRONTEND_DIR"

# Only install again in local environment if explicitly needed
if [ "${ENVIRONMENT:-}" = "local" ]; then
    echo "Local environment: re-installing dependencies..."
    npm install
fi

# Detect active tests
if find e2e/ -name "*.spec.js" -not -name "*.disabled" | grep -q .; then
    echo "Installing Playwright browsers..."
    if [ "${ENVIRONMENT:-}" = "cicd" ]; then
        npx playwright install --with-deps chromium
    else
        npx playwright install chromium
    fi

    echo "Executing E2E test suite with enhanced timeout and retry logic..."
    
    # Enhanced timeout and retry configuration from run.sh
    TIMEOUT_DURATION=300  # 5 minutes
    MAX_RETRIES=2
    
    # Function to run tests with timeout and better error handling
    run_tests_with_timeout() {
        local attempt=$1
        echo "🧪 Test attempt ${attempt}/${MAX_RETRIES}"
        
        # Run tests with timeout
        if timeout ${TIMEOUT_DURATION} npm run test:e2e; then
            echo "✅ E2E tests passed on attempt ${attempt}"
            return 0
        else
            local exit_code=$?
            if [ $exit_code -eq 124 ]; then
                echo "⏰ Tests timed out after ${TIMEOUT_DURATION} seconds on attempt ${attempt}"
            else
                echo "❌ Tests failed with exit code ${exit_code} on attempt ${attempt}"
            fi
            return $exit_code
        fi
    }
    
    # Run tests with retry logic
    for attempt in $(seq 1 $MAX_RETRIES); do
        if run_tests_with_timeout $attempt; then
            echo "🎉 E2E tests completed successfully!"
            break
        fi
        
        if [ $attempt -lt $MAX_RETRIES ]; then
            echo "🔄 Retrying in 5 seconds..."
            sleep 5
        else
            echo "💥 All attempts failed. E2E tests failed after ${MAX_RETRIES} attempts."
            exit 1
        fi
    done
else
    echo "No active E2E tests found (all *.spec.js are disabled). Skipping."
fi

echo "E2E tests finished."

# Explicit cleanup before exit
if [[ -n "${BACKEND_PID-}" ]]; then
    echo "🧹 Stopping backend server (PID: $BACKEND_PID)..."
    kill "${BACKEND_PID}" 2>/dev/null || true
    # Wait a moment for graceful shutdown
    sleep 2
    # Force kill if still running
    kill -9 "${BACKEND_PID}" 2>/dev/null || true
    echo "✅ Backend server stopped"
fi
