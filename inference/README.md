# inference/

Everything about model runtime, mock-vs-real inference, and GB10 smoke tests.

## Layout

- `local/mock_inference.py` — run the heuristic analysis on a transcript fixture.
- `local/sample_inputs/`, `local/sample_outputs/` — fixtures and golden outputs.
- `remote/start_qwen.sh` — warm `lifeos-qwen3-30b:latest` on Ollama.
- `remote/healthcheck.sh` — verify Qwen, Hermes, embedding NIM, and TTS NIM.
- `remote/run_model_server.sh` — stable entry point delegating to `start_qwen.sh`.

## Current GB10 Profile

The app's main/default conversational brain is direct local Qwen:

```env
INFERENCE_BACKEND=qwen
QWEN_BASE_URL=http://127.0.0.1:11434/v1
QWEN_MODEL=lifeos-qwen3-30b:latest
```

Hermes is still the agent/tool/alert gateway:

```env
CHAT_BACKEND=hermes
HERMES_BASE_URL=http://127.0.0.1:8642
```

NIM sidecars:

```env
EMBED_BASE_URL=http://127.0.0.1:8001/v1
EMBED_MODEL=nvidia/llama-nemotron-embed-1b-v2
TTS_BASE_URL=http://127.0.0.1:8003/v1
```

## Known Blockers

- `nemotron-asr-streaming` image is downloaded, but runtime model artifacts need
  `NGC_API_KEY` inside the container. Until then, ASR is blocked.
- `parakeet-0.6b-tdt` image exists locally but is `linux/amd64`; the GB10 host
  is `linux/arm64`, so it exits with `exec format error`.
- The 120B GGUF model is a deep-planning profile, not part of the normal hot path.

## Checks

```bash
inference/remote/healthcheck.sh
```

```bash
cd backend
INFERENCE_BACKEND=qwen \
QWEN_MODEL=lifeos-qwen3-30b:latest \
./.venv/bin/python test_hermes_inference.py
```

```bash
curl -fsS http://127.0.0.1:8090/api/health | python3 -m json.tool
```
