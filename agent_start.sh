#!/bin/bash

# Parse command line arguments
ONLY_FRONTEND=false
ONLY_BACKEND=false

# Iterate through all arguments to support both short and long options
for arg in "$@"; do
  case $arg in
    -f|--frontend)
      ONLY_FRONTEND=true
      ;;
    -b|--backend)
      ONLY_BACKEND=true
      ;;
  esac
done

# Configuration
USE_NEW_FRONTEND=${USE_NEW_FRONTEND:-true}
START_S3_MOCK=false

# Kill any running uvicorn processes (skip if only rebuilding frontend)
if [ "$ONLY_FRONTEND" = false ] && [ "$ONLY_BACKEND" = false ]; then
    echo "Killing any running uvicorn processes... and python processes"
    pkill -f uvicorn
    # also kill python
    pkill -f python
    # wait a few seconds for processes to terminate
    sleep 2
    clear
    echo "Clearing log for fresh start"
    mkdir -p ./logs
    echo "NEW LOG" > ./logs/app.jsonl
fi

. .venv/bin/activate

# Build frontend if not backend only
if [ "$ONLY_BACKEND" = false ]; then
    echo "FRONTEND"
    cd frontend
    npm install
    # Set VITE_APP_NAME for build (required for index.html template replacement)
    export VITE_APP_NAME="Chat UI"
    npm run build
    cd ../backend
fi

# If only frontend flag is set, exit here
if [ "$ONLY_FRONTEND" = true ]; then
    echo "Frontend rebuilt successfully. Exiting as requested."
    exit 0
fi

# If only backend flag is set, start backend services and exit
if [ "$ONLY_BACKEND" = true ]; then
    echo "Killing any running uvicorn processes... and python processes"
    pkill -f uvicorn
    # also kill python
    pkill -f python
    # wait a few seconds for processes to terminate
    sleep 2
    clear
    echo "Clearing log for fresh start"
    mkdir -p ./logs
    echo "NEW LOG" > ./logs/app.jsonl

    cd backend
    uvicorn main:app --host 0.0.0.0 --port 8000 &
    echo "Backend server started. Exiting as requested."
    exit 0
fi
# cd backend
uvicorn main:app --port 8000 &
echo "Server started"
