#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="/home/huangzw/miniforge3/envs/common/bin/python"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/API"
DEMO_DIR="$ROOT_DIR/demo"
DEMO_DIR="$ROOT_DIR/demo"
CHAT_DIR="$DEMO_DIR/chat"
LOG_DIR="$ROOT_DIR/logs"

mkdir -p "$LOG_DIR"

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT_DIR/.env"
  set +a
fi

read -r API_BASE API_PUBLIC_BASE API_PUBLIC_BASE_V1 HTTP_SERVER_BASE FRONTEND_HOST FRONTEND_PORT WEBSOCKET_URL <<EOF
$(
  API_DIR="$API_DIR" "$PYTHON_BIN" - <<'PY'
import os
import sys

api_dir = os.environ.get("API_DIR")
if api_dir:
    sys.path.append(api_dir)

from config import (
    API_BASE,
    API_PUBLIC_BASE,
    API_PUBLIC_BASE_V1,
    HTTP_SERVER_BASE,
    FRONTEND_HOST,
    FRONTEND_PORT,
    WEBSOCKET_URL,
)

print(
    API_BASE,
    API_PUBLIC_BASE,
    API_PUBLIC_BASE_V1,
    HTTP_SERVER_BASE,
    FRONTEND_HOST,
    FRONTEND_PORT,
    WEBSOCKET_URL,
)
PY
)
EOF

TARGET="${1:-all}"
case "$TARGET" in
  all|backend|frontend) ;;
  *)
    echo "Usage: $0 [all|backend|frontend]"
    exit 1
    ;;
esac

echo "Starting DeepAnalyze services (LLM not started)."
echo "API base: $API_PUBLIC_BASE_V1"
echo "File server: $HTTP_SERVER_BASE"
echo "Frontend: http://$FRONTEND_HOST:$FRONTEND_PORT"

if [ "$TARGET" = "all" ] || [ "$TARGET" = "backend" ]; then
  if [ -f "$LOG_DIR/backend.pid" ] && kill -0 "$(cat "$LOG_DIR/backend.pid")" >/dev/null 2>&1; then
    echo "Backend already running (PID: $(cat "$LOG_DIR/backend.pid"))."
  else
    echo "Starting backend API (demo backend)..."
    nohup "$PYTHON_BIN" "$DEMO_DIR/backend.py" > "$LOG_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo "$BACKEND_PID" > "$LOG_DIR/backend.pid"
  fi
fi

if [ "$TARGET" = "all" ] || [ "$TARGET" = "frontend" ]; then
  if [ -f "$LOG_DIR/frontend.pid" ] && kill -0 "$(cat "$LOG_DIR/frontend.pid")" >/dev/null 2>&1; then
    echo "Frontend already running (PID: $(cat "$LOG_DIR/frontend.pid"))."
  else
    if [ ! -d "$CHAT_DIR/node_modules" ]; then
      echo "Installing frontend dependencies..."
      (cd "$CHAT_DIR" && npm install)
    fi

    echo "Starting frontend..."
    (
      export NEXT_PUBLIC_BACKEND_URL="$API_PUBLIC_BASE"
      export NEXT_PUBLIC_FILE_SERVER_BASE="$HTTP_SERVER_BASE"
      export NEXT_PUBLIC_AI_API_URL="${API_BASE%/v1}"
      export NEXT_PUBLIC_WEBSOCKET_URL="$WEBSOCKET_URL"
      cd "$CHAT_DIR"
      nohup npm run dev -- -p "$FRONTEND_PORT" > "$LOG_DIR/frontend.log" 2>&1 &
      echo $! > "$LOG_DIR/frontend.pid"
    )
  fi
fi

echo "Services started."
if [ -f "$LOG_DIR/backend.pid" ]; then
  echo "Backend PID: $(cat "$LOG_DIR/backend.pid")"
fi
if [ -f "$LOG_DIR/frontend.pid" ]; then
  echo "Frontend PID: $(cat "$LOG_DIR/frontend.pid")"
fi
echo "Logs: $LOG_DIR/backend.log, $LOG_DIR/frontend.log"
