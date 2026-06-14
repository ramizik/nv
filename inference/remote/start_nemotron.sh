#!/usr/bin/env bash
# Remote NVIDIA GB10: serve Nemotron behind an OpenAI-compatible endpoint on :8000.
# Backend connects with INFERENCE_BACKEND=nemotron + NEMOTRON_BASE_URL=http://<host>:8000/v1
#
# Edit MODEL to the exact id you've pulled. Nemotron family preferred; Llama/Qwen work as
# drop-ins (then set NEMOTRON_MODEL in .env to match). Requires vLLM (pip install vllm).
set -euo pipefail

MODEL="${MODEL:-nvidia/Nemotron-4-340B-Instruct}"   # <-- set to your actually-available model id
PORT="${PORT:-8000}"

echo "Serving $MODEL on :$PORT (OpenAI-compatible)..."
exec vllm serve "$MODEL" \
  --port "$PORT" \
  --host 0.0.0.0 \
  --max-model-len "${MAX_LEN:-8192}"
# NIM alternative: run the Nemotron NIM container exposing :8000 instead of this script.
