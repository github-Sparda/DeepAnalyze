#!/bin/bash

echo "Starting Chat System"
echo "=========================="

# Ensure outputs/logs directory exists
mkdir -p outputs/logs

# Function to check and free ports
check_port() {
    local port=$1
    if lsof -i:$port > /dev/null 2>&1; then
        echo "Port $port is already in use, terminating process..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# Clean up old processes
echo "Cleaning old processes..."
pkill -f "python.*backend.py" 2>/dev/null || true
pkill -f "npm.*dev" 2>/dev/null || true

PYTHON_BIN=${PYTHON_BIN:-python3}
CONFIG_DIR="$(cd "$(dirname "$0")/../src/api" && pwd)"

read -r VLLM_PORT src/api_PORT FILE_PORT FRONTEND_PORT FRONTEND_HOST src/api_BASE src/api_PUBLIC_BASE FILE_BASE WEBSOCKET_URL <<EOF
$($PYTHON_BIN - <<PY
import sys
from pathlib import Path

sys.path.append(str(Path("$CONFIG_DIR")))
from config import (
    src/api_BASE,
    src/api_PORT,
    HTTP_SERVER_PORT,
    FRONTEND_PORT,
    FRONTEND_HOST,
    src/api_PUBLIC_BASE,
    HTTP_SERVER_BASE,
    WEBSOCKET_URL,
    get_vllm_port,
)

print(
    f"{get_vllm_port() or ''} {src/api_PORT} {HTTP_SERVER_PORT} {FRONTEND_PORT} {FRONTEND_HOST} "
    f"{src/api_BASE} {src/api_PUBLIC_BASE} {HTTP_SERVER_BASE} {WEBSOCKET_URL}"
)
PY
)
EOF

# Check and clean ports
if [ -n "$VLLM_PORT" ]; then
    check_port "$VLLM_PORT"
fi
check_port "$FILE_PORT"
check_port "$src/api_PORT"
check_port "$FRONTEND_PORT"

echo "Cleanup completed."
echo ""

# Start backend src/api (ports from src/api/config.py)
echo "Starting backend src/api..."
nohup python3 backend.py > outputs/logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
echo "src/api running on: $src/api_PUBLIC_BASE"
echo "File service running on: $FILE_BASE"

# Wait for backend to initialize
sleep 3

# Start frontend (React, default port: $FRONTEND_PORT)
echo ""
echo "Starting React frontend..."
cd chat || exit
NEXT_PUBLIC_BACKEND_URL="$src/api_PUBLIC_BASE" \
NEXT_PUBLIC_FILE_SERVER_BASE="$FILE_BASE" \
NEXT_PUBLIC_AI_src/api_URL="${src/api_BASE%/v1}" \
NEXT_PUBLIC_WEBSOCKET_URL="$WEBSOCKET_URL" \
nohup npm run dev -- -p $FRONTEND_PORT > ../outputs/logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "Frontend PID: $FRONTEND_PID"
echo "Frontend running on: http://$FRONTEND_HOST:$FRONTEND_PORT"

# Save PIDs
echo $BACKEND_PID > outputs/logs/backend.pid
echo $FRONTEND_PID > outputs/logs/frontend.pid

echo ""
echo "All services started successfully."
echo ""
echo "Service URLs:"
echo "  Model src/api:    ${src/api_BASE%/v1}"
echo "  Backend src/api:  $src/api_PUBLIC_BASE"
echo "  Frontend:     http://$FRONTEND_HOST:$FRONTEND_PORT"
echo "  File Service: $FILE_BASE"
echo ""
echo "Log files:"
echo "  Backend: outputs/logs/backend.log"
echo "  Frontend: outputs/logs/frontend.log"
echo ""
echo "Stop services: ./stop.sh"
