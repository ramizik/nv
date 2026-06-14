#!/usr/bin/env bash
# Remote NVIDIA GB10: ensure the local Nemotron model is served behind an OpenAI-compatible
# endpoint. CONFIRMED reality on the box: it's served via **Ollama** at :11434/v1 (no API key).
# Backend connects with:
#   INFERENCE_BACKEND=nemotron
#   NEMOTRON_BASE_URL=http://127.0.0.1:11434/v1
#   NEMOTRON_MODEL=lifeos-nemotron-120b:latest
#
# ⚠️ ~120 GB unified memory ⇒ ONLY ONE local model resident at a time. Keep exactly the demo
# model loaded; don't run voice/embed/Qwen alongside it. Switching models = unload+reload.
set -euo pipefail

MODEL="${MODEL:-lifeos-nemotron-120b:latest}"

# Ollama usually runs as a service already; start it if not, then warm the model so the first
# real request isn't a cold 120B load (which can take tens of seconds).
echo "Ensuring Ollama is up and warming $MODEL ..."
pgrep -x ollama >/dev/null 2>&1 || (ollama serve >/tmp/ollama.log 2>&1 &) && sleep 2
ollama run "$MODEL" "Reply with the single word: ok" || {
  echo "Failed to warm $MODEL. Is it pulled?  ollama list"; exit 1; }
echo "Ready. OpenAI-compatible endpoint: http://127.0.0.1:11434/v1  (model: $MODEL)"

# ---------------------------------------------------------------------------
# Alternative (NOT the demo path): serve via vLLM on :8000 instead of Ollama.
#   vllm serve <hf-model-id> --port 8000 --host 0.0.0.0 --max-model-len 8192
# then NEMOTRON_BASE_URL=http://<host>:8000/v1 + NEMOTRON_MODEL=<hf-model-id>.
