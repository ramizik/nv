# GB10 Hermes And Model Integration

This repo runs the **Local Voice Lead Closer** demo on the Dell Pro Max GB10 at
`/home/dell/ram/nv`. It reuses the LifeOS/Hermes stack without importing
OpenClaw, OpenShell, or NemoClaw.

## Runtime Contract

| Concern | Runtime | Endpoint | Status |
|---|---|---|---|
| Main conversational/scoring brain | Qwen3-30B-A3B GGUF via Ollama | `http://127.0.0.1:11434/v1` | Primary |
| Hermes agent/tools/actions/alerts | Hermes gateway | `http://127.0.0.1:8642` | Primary gateway |
| Text memory embeddings | `nvidia/llama-nemotron-embed-1b-v2` NIM | `http://127.0.0.1:8001/v1` | Running |
| Voice output | Magpie multilingual TTS NIM | `http://127.0.0.1:8003/v1` | Running |
| Streaming ASR | `nemotron-asr-streaming` NIM | `http://127.0.0.1:8002/v1` | Running, realtime sessions enabled |
| Parakeet ASR fallback | `parakeet-0.6b-tdt` NIM | unset | **Dropped (intentional)** — redundant backup; amd64-only image won't run on arm64; role covered by nemotron-asr-streaming |

## Important Correction

Hermes is not assumed to be the local-Qwen inference brain for this repo.
Hermes was restored to its reliable `gemini-flash-latest` default after the
local-Qwen Hermes path proved slow and unstable with the full Hermes prompt. The
local provider is still registered in Hermes, but this app uses direct Ollama
for deterministic on-box Qwen inference:

```env
INFERENCE_BACKEND=qwen
QWEN_BASE_URL=http://127.0.0.1:11434/v1
QWEN_MODEL=lifeos-qwen3-30b:latest
QWEN_THINKING_DIRECTIVE=/no_think
```

Hermes remains the durable gateway for tool execution, memory/actions, and
alert delivery:

```env
CHAT_BACKEND=hermes
HERMES_BASE_URL=http://127.0.0.1:8642
HERMES_API_KEY=<API_SERVER_KEY from ~/.hermes/.env>
```

Do not commit `HERMES_API_KEY` or any token copied from `~/.hermes/.env`.

## Backend Configuration

The backend reads `.env` from the repo root. The GB10 profile is:

```env
INFERENCE_BACKEND=qwen
CHAT_BACKEND=hermes

HERMES_BASE_URL=http://127.0.0.1:8642
HERMES_API_KEY=
HERMES_DISCORD_CHANNEL=1509734278206984194

QWEN_BASE_URL=http://127.0.0.1:11434/v1
QWEN_MODEL=lifeos-qwen3-30b:latest
QWEN_API_KEY=not-needed
QWEN_TIMEOUT_READ=240
QWEN_THINKING_DIRECTIVE=/no_think

EMBED_BASE_URL=http://127.0.0.1:8001/v1
EMBED_MODEL=nvidia/llama-nemotron-embed-1b-v2
EMBED_INPUT_TYPE_QUERY=query

TTS_BASE_URL=http://127.0.0.1:8003/v1
TTS_VOICE=Magpie-Multilingual.EN-US.Mia.Neutral
TTS_LANGUAGE=en-US
TTS_SAMPLE_RATE_HZ=22050

ASR_BACKEND=nemotron-asr-streaming
ASR_BASE_URL=http://127.0.0.1:8002/v1
ASR_RUNTIME_STATUS=ready: nemotron-asr-streaming NIM on :8002, realtime sessions enabled
```

Port `8080` is already occupied by the LifeOS backend on the GB10. Run this app
on port `8090`:

```bash
PORT=8090 scripts/linux/run_backend.sh
```

## Health And Smoke Tests

Repo-level health:

```bash
curl -fsS http://127.0.0.1:8090/api/health | python3 -m json.tool
```

Model/NIM stack health:

```bash
inference/remote/healthcheck.sh
```

Qwen inference path:

```bash
cd backend
INFERENCE_BACKEND=qwen \
QWEN_BASE_URL=http://127.0.0.1:11434/v1 \
QWEN_MODEL=lifeos-qwen3-30b:latest \
./.venv/bin/python test_hermes_inference.py
```

Embedding smoke:

```bash
curl -fsS -X POST http://127.0.0.1:8001/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model":"nvidia/llama-nemotron-embed-1b-v2","input":["LifeOS embedding smoke test"],"input_type":"query"}'
```

TTS smoke:

```bash
curl -fsS http://127.0.0.1:8003/v1/audio/synthesize \
  -F 'text=LifeOS TTS smoke test.' \
  -F 'language=en-US' \
  -F 'voice=Magpie-Multilingual.EN-US.Mia.Neutral' \
  -F 'sample_rate_hz=22050' \
  -F 'encoding=LINEAR_PCM' \
  -o /tmp/lifeos-tts.wav
```

## Failure Modes

- If Qwen is missing from `/v1/models`, check `lifeos-ollama.service` and warm
  the model with `inference/remote/start_qwen.sh`.
- If Hermes returns `401 invalid_api_key`, copy `API_SERVER_KEY` from
  `~/.hermes/.env` into this repo's `.env` as `HERMES_API_KEY`.
- If ASR fails with `ManifestDownloadError` or mentions missing API key, restart
  it with `inference/remote/start_asr.sh`; the script reads `NVIDIA_API_KEY` from
  `~/.hermes/.env` and passes it as `NGC_API_KEY` to the container.
- Do not try to run the downloaded Parakeet image on this GB10. The available
  image is `linux/amd64`; the machine is `linux/arm64`.
