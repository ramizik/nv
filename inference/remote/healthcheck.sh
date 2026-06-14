#!/usr/bin/env bash
# Remote NVIDIA GB10: verify the model server is up and answering.
set -euo pipefail
BASE="${NEMOTRON_BASE_URL:-http://localhost:8000/v1}"
echo "== GPU =="; nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader || true
echo "== Models @ $BASE =="; curl -fsS "$BASE/models" | head -c 600; echo
echo "== Tiny completion =="
curl -fsS -X POST "$BASE/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"'"${NEMOTRON_MODEL:-nvidia/nemotron}"'","messages":[{"role":"user","content":"Reply with the single word: ok"}],"max_tokens":5}' \
  | head -c 600; echo
echo "OK if you saw a model list and a completion above."
