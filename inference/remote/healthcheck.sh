#!/usr/bin/env bash
# Remote NVIDIA GB10: verify the model server is up and answering.
#
# This checks the DIRECT-OLLAMA fallback path (INFERENCE_BACKEND=qwen). The REAL demo path
# routes through Hermes; check that with:
#   curl -fsS http://127.0.0.1:8642/health
#   curl -fsS -X POST http://127.0.0.1:8642/v1/chat/completions \
#     -H "Authorization: Bearer $HERMES_API_KEY" -H "Content-Type: application/json" \
#     -d '{"model":"","messages":[{"role":"user","content":"Reply with the single word: ok"}],"max_tokens":5}'
# (blank model = Hermes default, which is local Qwen3-30B).
set -euo pipefail
BASE="${QWEN_BASE_URL:-${NEMOTRON_BASE_URL:-http://127.0.0.1:11434/v1}}"
MODEL="${QWEN_MODEL:-${NEMOTRON_MODEL:-Qwen3-30B:latest}}"
echo "== GPU =="; nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader || true
echo "== Models @ $BASE =="; curl -fsS "$BASE/models" | head -c 600; echo
echo "== Tiny completion =="
curl -fsS -X POST "$BASE/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"'"$MODEL"'","messages":[{"role":"user","content":"Reply with the single word: ok"}],"max_tokens":5}' \
  | head -c 600; echo
echo "OK if you saw a model list and a completion above."
