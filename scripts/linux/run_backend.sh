#!/usr/bin/env bash
# Linux (dev box or GB10): start the FastAPI backend.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO/backend"
if command -v uv >/dev/null 2>&1; then
  [ -d .venv ] || uv venv .venv
  . .venv/bin/activate
  uv pip install -q -r requirements.txt
else
  [ -d .venv ] || python3 -m venv .venv
  . .venv/bin/activate
  pip install -q -r requirements.txt
fi
echo "Backend on http://localhost:8080 (health: /api/health)"
exec uvicorn app.main:app --port 8080
