#!/bin/bash
set -euo pipefail

trap 'rc=$?; echo "Cleaning up..."; [[ -n "${BACKEND_PID-}" ]] && kill "${BACKEND_PID}" 2>/dev/null || true; exit $rc' EXIT

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
npm ci

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

# Start backend
echo "Starting backend server..."
cd "$BACKEND_DIR"
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

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
    npm ci
fi

# Detect active tests
if find e2e/ -name "*.spec.js" -not -name "*.disabled" | grep -q .; then
    echo "Installing Playwright browsers..."
    if [ "${ENVIRONMENT:-}" = "cicd" ]; then
        npx playwright install --with-deps chromium
    else
        npx playwright install chromium
    fi

    echo "Executing E2E test suite with timeout..."
    timeout 300 npm run test:e2e
else
    echo "No active E2E tests found (all *.spec.js are disabled). Skipping."
fi

echo "E2E tests finished."
