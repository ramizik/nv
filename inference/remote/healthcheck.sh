#!/usr/bin/env bash
# Remote NVIDIA GB10: verify the model/Hermes/NIM stack used by this repo.
set -euo pipefail
BASE="${QWEN_BASE_URL:-${NEMOTRON_BASE_URL:-http://127.0.0.1:11434/v1}}"
MODEL="${QWEN_MODEL:-${NEMOTRON_MODEL:-lifeos-qwen3-30b:latest}}"
EMBED_BASE="${EMBED_BASE_URL:-http://127.0.0.1:8001/v1}"
EMBED_MODEL="${EMBED_MODEL:-nvidia/llama-nemotron-embed-1b-v2}"
TTS_BASE="${TTS_BASE_URL:-http://127.0.0.1:8003/v1}"
ASR_BASE="${ASR_BASE_URL:-http://127.0.0.1:8002/v1}"
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
echo "== ASR NIM =="; curl -fsS "$ASR_BASE/health/ready"; echo
curl -fsS -X POST "$ASR_BASE/realtime/transcription_sessions" \
  -H "Content-Type: application/json" -d '{}' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("session", d["id"], d["input_audio_transcription"]["model"])'
echo "== Intentionally dropped =="
echo "Parakeet: DROPPED (redundant backup ASR). amd64-only image won't run on GB10 arm64; ASR role covered by nemotron-asr-streaming. NeMo-native is the only arm64 path if ever needed."
