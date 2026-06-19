#!/usr/bin/env bash
# Run the read-only learning KB HTTP API (binds localhost by default).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${LEARNING_KB_API_VENV:-/root/.venv-langchain-course}"
HOST="${LEARNING_KB_API_HOST:-127.0.0.1}"
PORT="${LEARNING_KB_API_PORT:-8791}"

# shellcheck source=/dev/null
source /mnt/blockstorage/env/load.sh

cd "$ROOT"
export LANGCHAIN_COURSE_REPO="${LANGCHAIN_COURSE_REPO:-/root/langchain-course}"
export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"

if ! "$VENV/bin/python" -c "import fastapi" 2>/dev/null; then
  echo "Installing API deps into $VENV ..."
  "$VENV/bin/pip" install -q -r requirements-api.txt
fi

exec "$VENV/bin/uvicorn" api.app:app --host "$HOST" --port "$PORT" --proxy-headers
