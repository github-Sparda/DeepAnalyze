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

check_pid() {
  local name=$1
  local pid_file=$2
  if [ -f "$pid_file" ]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" >/dev/null 2>&1; then
      echo "$name: running (PID: $pid)"
      return 0
    fi
    echo "$name: not running (stale PID: $pid)"
    return 1
  fi
  echo "$name: not running (no PID file)"
  return 1
}

check_port() {
  local name=$1
  local port=$2
  if lsof -i:"$port" >/dev/null 2>&1; then
    echo "$name port $port: in use"
    return 0
  fi
  echo "$name port $port: free"
  return 1
}

TARGET="${1:-all}"
case "$TARGET" in
  all|backend|frontend) ;;
  *)
    echo "Usage: $0 [all|backend|frontend]"
    exit 1
    ;;
esac

echo "DeepAnalyze service status"
if [ "$TARGET" = "all" ] || [ "$TARGET" = "backend" ]; then
  check_pid "Backend src/api" "$LOG_DIR/backend.pid"
  check_port "src/api" "$src/api_PORT"
  check_port "File server" "$FILE_PORT"
fi
if [ "$TARGET" = "all" ] || [ "$TARGET" = "frontend" ]; then
  check_pid "Frontend" "$LOG_DIR/frontend.pid"
  check_port "Frontend" "$FRONTEND_PORT"
fi
