#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-all}"

case "$TARGET" in
  all|backend|frontend) ;;
  *)
    echo "Usage: $0 [all|backend|frontend]"
    exit 1
    ;;
esac

"$ROOT_DIR/scripts/stop_services.sh" "$TARGET"
"$ROOT_DIR/scripts/start_services.sh" "$TARGET"
