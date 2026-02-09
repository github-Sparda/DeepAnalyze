#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="/home/huangzw/miniforge3/envs/common/bin/python"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/outputs/logs"
src/api_DIR="$ROOT_DIR/src/api"

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT_DIR/.env"
  set +a
fi

read -r src/api_PORT FILE_PORT FRONTEND_PORT <<EOF
$(
  src/api_DIR="$src/api_DIR" "$PYTHON_BIN" - <<'PY'
import os
import sys

api_dir = os.environ.get("src/api_DIR")
if api_dir:
    sys.path.append(api_dir)

from config import src/api_PORT, HTTP_SERVER_PORT, FRONTEND_PORT

print(src/api_PORT, HTTP_SERVER_PORT, FRONTEND_PORT)
PY
)
EOF

stop_pid_file() {
  local name=$1
  local pid_file=$2
  if [ -f "$pid_file" ]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" >/dev/null 2>&1; then
      echo "Stopping $name (PID: $pid)..."
      kill "$pid" >/dev/null 2>&1 || true
      sleep 1
      if kill -0 "$pid" >/dev/null 2>&1; then
        echo "Force stopping $name..."
        kill -9 "$pid" >/dev/null 2>&1 || true
      fi
    else
      echo "$name PID $pid not running."
    fi
    rm -f "$pid_file"
  else
    echo "No PID file for $name."
  fi
}

TARGET="${1:-all}"
case "$TARGET" in
  all|backend|frontend) ;;
  *)
    echo "Usage: $0 [all|backend|frontend]"
    exit 1
    ;;
esac

echo "Stopping DeepAnalyze services..."
if [ "$TARGET" = "all" ] || [ "$TARGET" = "backend" ]; then
  stop_pid_file "Backend src/api" "$LOG_DIR/backend.pid"
fi
if [ "$TARGET" = "all" ] || [ "$TARGET" = "frontend" ]; then
  stop_pid_file "Frontend" "$LOG_DIR/frontend.pid"
fi

echo "Releasing ports..."
if [ "$TARGET" = "all" ] || [ "$TARGET" = "backend" ]; then
  for port in "$src/api_PORT" "$FILE_PORT"; do
    if lsof -i:"$port" >/dev/null 2>&1; then
      echo "Releasing port $port..."
      lsof -ti:"$port" | xargs kill -9 >/dev/null 2>&1 || true
    fi
  done
fi
if [ "$TARGET" = "all" ] || [ "$TARGET" = "frontend" ]; then
  if lsof -i:"$FRONTEND_PORT" >/dev/null 2>&1; then
    echo "Releasing port $FRONTEND_PORT..."
    lsof -ti:"$FRONTEND_PORT" | xargs kill -9 >/dev/null 2>&1 || true
  fi
fi

echo "Done."
