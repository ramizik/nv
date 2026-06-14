#!/usr/bin/env bash
# Remote NVIDIA GB10: warm the local Qwen3-30B model on Ollama (:11434/v1, OpenAI-compatible).
#
# NOTE: this is the DIRECT-OLLAMA *FALLBACK* warmer. The real demo path routes reasoning
# through Hermes (http://127.0.0.1:8642/v1), which itself delegates to this same local
# Qwen3-30B on Ollama — so for the normal demo you do NOT need to run this script (Hermes
# already serves Qwen). Use it only when driving Ollama directly with INFERENCE_BACKEND=qwen:
#   INFERENCE_BACKEND=qwen
#   QWEN_BASE_URL=http://127.0.0.1:11434/v1
#   QWEN_MODEL=Qwen3-30B:latest
#   QWEN_API_KEY=not-needed
#
# ⚠️ ~120 GB unified memory ⇒ ONLY ONE large model resident at a time. Qwen3-30B (~18 GB,
# ~3B active) is fast and coexists with the NIM voice stack; Nemotron-120B (~82 GB) is an
# optional heavier alternative that monopolizes the box. Switching models = unload+reload.
set -euo pipefail

MODEL="${MODEL:-Qwen3-30B:latest}"

# Ollama usually runs as a service already; start it if not, then warm the model so the first
# real request isn't a cold load.
echo "Ensuring Ollama is up and warming $MODEL ..."
pgrep -x ollama >/dev/null 2>&1 || (ollama serve >/tmp/ollama.log 2>&1 &) && sleep 2
ollama run "$MODEL" "Reply with the single word: ok" || {
  echo "Failed to warm $MODEL. Is it pulled?  ollama list"; exit 1; }
echo "Ready. OpenAI-compatible endpoint: http://127.0.0.1:11434/v1  (model: $MODEL)"

# ---------------------------------------------------------------------------
# Alternative (NOT the demo path): serve via vLLM on :8000 instead of Ollama.
#   vllm serve <hf-model-id> --port 8000 --host 0.0.0.0 --max-model-len 8192
# then QWEN_BASE_URL=http://<host>:8000/v1 + QWEN_MODEL=<hf-model-id>.
