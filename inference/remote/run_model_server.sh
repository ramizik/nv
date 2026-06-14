#!/usr/bin/env bash
# Generic entry point for the DIRECT-OLLAMA fallback warmer — delegates to start_qwen.sh.
# Kept as the stable name the docs reference; swap the delegate if you serve a different
# model/engine. NB: the real demo path is Hermes→Qwen (no model server to start here).
set -euo pipefail
exec "$(dirname "${BASH_SOURCE[0]}")/start_qwen.sh"
