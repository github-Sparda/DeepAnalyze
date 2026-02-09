#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="/home/huangzw/miniforge3/envs/common/bin/python"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src/api_DIR="$ROOT_DIR/src/api"

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT_DIR/.env"
  set +a
fi

read -r src/api_PUBLIC_BASE_V1 DEFAULT_MODEL <<EOF
$(
  src/api_DIR="$src/api_DIR" "$PYTHON_BIN" - <<'PY'
import os
import sys

api_dir = os.environ.get("src/api_DIR")
if api_dir:
    sys.path.append(api_dir)

from config import src/api_PUBLIC_BASE_V1, DEFAULT_MODEL

print(src/api_PUBLIC_BASE_V1, DEFAULT_MODEL)
PY
)
EOF

DATA_FILE="${1:-$ROOT_DIR/data/examples/docs/analysis_on_student_loan/data/enrolled.csv}"

if [ ! -f "$DATA_FILE" ]; then
  echo "Data file not found: $DATA_FILE"
  exit 1
fi

echo "src/api base: $src/api_PUBLIC_BASE_V1"
echo "Model: $DEFAULT_MODEL"
echo "Data: $DATA_FILE"

FILE_RESPONSE=$(curl -s -X POST "$src/api_PUBLIC_BASE_V1/files" \
  -F "file=@${DATA_FILE}" \
  -F "purpose=file-extract")

FILE_ID=$("$PYTHON_BIN" - <<PY
import json
import sys
try:
    payload = json.loads(sys.argv[1])
    print(payload.get("id", ""))
except Exception:
    print("")
PY
"$FILE_RESPONSE")

if [ -z "$FILE_ID" ]; then
  echo "Failed to upload file. Response:"
  echo "$FILE_RESPONSE"
  exit 1
fi

echo "Uploaded file id: $FILE_ID"

CHAT_RESPONSE=$(curl -s -X POST "$src/api_PUBLIC_BASE_V1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${DEFAULT_MODEL}\",
    \"messages\": [
      {\"role\": \"user\", \"content\": \"请分析这份数据并给出关键结论\", \"file_ids\": [\"${FILE_ID}\"]}
    ],
    \"data/cache/temporaryerature\": 0.4
  }")

echo "Response:"
echo "$CHAT_RESPONSE"
