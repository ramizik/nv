#!/usr/bin/env bash
# Linux one-time setup: env file + backend deps.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"
[ -f .env ] || { cp .env.example .env; echo "Created .env (GB10 Qwen/Hermes defaults)"; }
cd "$REPO/backend"
if command -v uv >/dev/null 2>&1; then uv venv .venv && . .venv/bin/activate && uv pip install -r requirements.txt
else python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt; fi
echo "Setup done. Run scripts/linux/run_backend.sh"
