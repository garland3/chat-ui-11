#!/bin/bash

# Parse command line arguments
ONLY_FRONTEND=false
ONLY_BACKEND=false
while getopts "fb" opt; do
  case $opt in
    f)
      ONLY_FRONTEND=true
      ;;
    b)
      ONLY_BACKEND=true
      ;;
  esac
done

# clear the log by setting to ""
# backend/logs/app.jsonl


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
    mkdir -p ./backend/logs
    echo "NEW LOG" > ./backend/logs/app.jsonl
fi

# cd /workspaces/chat-ui-11
. .venv/bin/activate

# Build frontend if not backend only
if [ "$ONLY_BACKEND" = false ]; then
    if [ "$USE_NEW_FRONTEND" = true ]; then
        echo "Using new frontend in frontend"
        cd frontend
        npm install
        npm run build
        cd ../backend
    else
        echo "Using old frontend in frontend"
        cd frontend
        npm run build
        cd ../backend
    fi
fi

# If only frontend flag is set, exit here
if [ "$ONLY_FRONTEND" = true ]; then
    echo "Frontend rebuilt successfully. Exiting as requested."
    exit 0
fi

# If only backend flag is set, start backend services and exit
if [ "$ONLY_BACKEND" = true ]; then
    # Start S3 mock service if enabled
    if [ "$START_S3_MOCK" = true ]; then
        echo "Starting S3 mock service..."
        cd ../mocks/s3-mock
        python main.py &
        cd ../../backend
        echo "S3 mock service started on http://127.0.0.1:8003"
    fi

    uvicorn main:app &
    echo "Backend server started. Exiting as requested."
    exit 0
fi

# Start S3 mock service if enabled
if [ "$START_S3_MOCK" = true ]; then
    echo "Starting S3 mock service..."
    cd ../mocks/s3-mock
    python main.py &
    cd ../../backend
    echo "S3 mock service started on http://127.0.0.1:8003"
fi

uvicorn main:app --port 8000 &
echo "Server started"


# # print every 3 seconds saying it is running. do 10 times. print second since start
# for i in {1..10}
# do
#     echo "Server running for $((i * 3)) seconds"
#     sleep 3
# done

# wait X seconds. 
# waittime=10
# echo "Starting server, waiting for $waittime seconds before sending config request"
# for ((i=waittime; i>0; i--)); do
#     echo "Waiting... $i seconds remaining"
#     sleep 1
# done
# host=127.0.0.1
# echo "Sending config request to $host:8000/api/config"
# result=$(curl -X GET http://$host:8000/api/config -H "Content-Type: application/json" -d '{"key": "value"}')
# # use json format output in a pretty way


# # echo "Config request sent, result:"
# # echo $result | jq .
# # # print the result
# # echo "Config request result: $(echo $result | jq .)
# # "

# # just get the "tools" part of the result and prrety print it
# echo "Config request result: $(echo $result | jq '.tools')"

# # make a count for 20 seconds and prompt the human to cause any errors
# echo "server ready, you can now cause any errors in the UI"
# for ((i=20; i>0; i--)); do
#     echo "You have $i seconds to cause any errors in the UI"
#     sleep 1
# done
