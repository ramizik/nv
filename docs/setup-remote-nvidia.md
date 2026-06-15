# Setup — Remote NVIDIA GB10

This repo's GB10 runtime uses local Qwen for inference and Hermes for actions/alerts:

- Qwen3-30B-A3B via Ollama: `http://127.0.0.1:11434/v1`
- Hermes gateway: `http://127.0.0.1:8642`
- llama-nemotron embedding NIM: `http://127.0.0.1:8001/v1`
- Magpie TTS NIM: `http://127.0.0.1:8003/v1`
- Nemotron ASR Streaming NIM: `http://127.0.0.1:8002/v1`

Port `8080` is already used by LifeOS. Run this backend on `8090`.

## Environment

```env
INFERENCE_BACKEND=qwen
CHAT_BACKEND=hermes

QWEN_BASE_URL=http://127.0.0.1:11434/v1
QWEN_MODEL=lifeos-qwen3-30b:latest
QWEN_API_KEY=not-needed
QWEN_TIMEOUT_READ=240
QWEN_THINKING_DIRECTIVE=/no_think

HERMES_BASE_URL=http://127.0.0.1:8642
HERMES_API_KEY=<API_SERVER_KEY from ~/.hermes/.env>
HERMES_DISCORD_CHANNEL=1509734278206984194

EMBED_BASE_URL=http://127.0.0.1:8001/v1
EMBED_MODEL=nvidia/llama-nemotron-embed-1b-v2

TTS_BASE_URL=http://127.0.0.1:8003/v1
TTS_VOICE=Magpie-Multilingual.EN-US.Mia.Neutral
TTS_LANGUAGE=en-US

ASR_BACKEND=nemotron-asr-streaming
ASR_BASE_URL=http://127.0.0.1:8002/v1
ASR_RUNTIME_STATUS=ready: nemotron-asr-streaming NIM on :8002, realtime sessions enabled
```

## Persistent Backend

```bash
mkdir -p ~/.config/systemd/user
cp /home/dell/ram/nv/scripts/linux/nv-backend.service ~/.config/systemd/user/nv-backend.service
systemctl --user daemon-reload
systemctl --user enable --now nv-backend.service
```

Check it:

```bash
systemctl --user status nv-backend.service
curl -fsS http://127.0.0.1:8090/api/health | python3 -m json.tool
```

## Smoke Tests

```bash
cd /home/dell/ram/nv
inference/remote/healthcheck.sh
```

```bash
cd /home/dell/ram/nv/backend
INFERENCE_BACKEND=qwen QWEN_MODEL=lifeos-qwen3-30b:latest ./.venv/bin/python test_hermes_inference.py
```

```bash
curl -fsS -X POST http://127.0.0.1:8090/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"veneers_wedding","notify":false}' | python3 -m json.tool
```

```bash
curl -fsS -X POST http://127.0.0.1:8090/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"veneers_wedding","notify":true}' | python3 -m json.tool
```

Talk to Hermes directly:

```bash
cd /home/dell/ram/nv
scripts/linux/chat_hermes.py
```

## Known Blockers

- ASR needs an NGC-compatible key at startup. `inference/remote/start_asr.sh` reads
  `NVIDIA_API_KEY` from `~/.hermes/.env` and passes it as `NGC_API_KEY`.
- `parakeet-0.6b-tdt` is present as a `linux/amd64` image and does not run on this `linux/arm64`
  GB10 host.
- Nemotron-120B GGUF is a deep-planning profile, not part of this app's normal hot path.
