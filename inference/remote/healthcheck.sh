#!/usr/bin/env bash
# Remote NVIDIA GB10: verify the model/Hermes/NIM stack used by this repo.
set -euo pipefail
BASE="${QWEN_BASE_URL:-${NEMOTRON_BASE_URL:-http://127.0.0.1:11434/v1}}"
MODEL="${QWEN_MODEL:-${NEMOTRON_MODEL:-lifeos-qwen3-30b:latest}}"
EMBED_BASE="${EMBED_BASE_URL:-http://127.0.0.1:8001/v1}"
EMBED_MODEL="${EMBED_MODEL:-nvidia/llama-nemotron-embed-1b-v2}"
TTS_BASE="${TTS_BASE_URL:-http://127.0.0.1:8003/v1}"
echo "== GPU =="; nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader || true
echo "== Models @ $BASE =="; curl -fsS "$BASE/models" | head -c 600; echo
echo "== Tiny completion =="
curl -fsS -X POST "$BASE/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"'"$MODEL"'","messages":[{"role":"user","content":"/no_think\nReply with the single word: ok"}],"temperature":0,"max_tokens":32}' \
  | head -c 600; echo
echo "== Hermes gateway =="; curl -fsS http://127.0.0.1:8642/health; echo
echo "== Embedding NIM =="; curl -fsS "$EMBED_BASE/health/ready"; echo
curl -fsS -X POST "$EMBED_BASE/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"model":"'"$EMBED_MODEL"'","input":["LifeOS embedding smoke test"],"input_type":"query"}' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("dim", len(d["data"][0]["embedding"]))'
echo "== TTS NIM =="; curl -fsS "$TTS_BASE/health/ready"; echo
echo "== Known blockers =="
echo "ASR: nemotron-asr-streaming image is present, but runtime artifact download needs NGC_API_KEY."
echo "Parakeet: local image is linux/amd64; GB10 is linux/arm64, so it cannot execute here."
