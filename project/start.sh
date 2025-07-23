#!/bin/bash

# Simple start script for Chat UI

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    uv venv venv
    source venv/bin/activate
    uv pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Create logs directory
mkdir -p backend/logs

# Start uvicorn server
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload