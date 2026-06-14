# Setup — Remote NVIDIA (GB10) Linux box

Serves the **local reasoning model (Nemotron)** behind an OpenAI-compatible endpoint so
the backend can call it with `INFERENCE_BACKEND=nemotron`. All inference stays on-prem.

## Prereqs
- NVIDIA drivers + CUDA (`nvidia-smi` works)
- Python 3.12 / Docker (depending on serving choice)
- The repo pulled here too (`shared/` is the cross-machine source of truth)

## 1. Serve the model (OpenAI-compatible) — CONFIRMED: Ollama on :11434
On the box, Nemotron-120B is served via **Ollama**, which exposes an OpenAI-compatible
`/v1/chat/completions` at `http://127.0.0.1:11434/v1` (no API key). Our adapter tolerates
servers that reject `response_format: json_object` (it retries without it) and strips any
`<think>` blocks, so Ollama output parses cleanly.

```bash
cd inference/remote
./start_nemotron.sh            # ensures Ollama is up and WARMS lifeos-nemotron-120b:latest
./healthcheck.sh               # curls /v1/models and a tiny completion on :11434
```

> ⚠️ **~120 GB unified memory ⇒ only ONE local model resident at a time.** Keep exactly the
> demo model loaded. The optional cheap path is `lifeos-qwen3-30b:latest` — if you switch to
> it, do so BEFORE the demo (Ollama unloads the 120B and loads Qwen, a one-time cold delay).
>
> Alternative (not the demo path): vLLM on :8000 — see the commented block in `start_nemotron.sh`.

## 2. (Optional) PersonaPlex voice
`./start_personaplex.sh` is a placeholder for the voice service. For the hackathon demo we
use a transcript fixture; wire live voice only after the dashboard + chat are solid.

## 3. Point the backend at this box
**Recommended: run the backend ON the GB10** so the model (`:11434`) and Hermes (`:8642`,
both bound to localhost) are reachable. In `.env`:
```
INFERENCE_BACKEND=nemotron
NEMOTRON_BASE_URL=http://127.0.0.1:11434/v1
NEMOTRON_MODEL=lifeos-nemotron-120b:latest
NEMOTRON_API_KEY=not-needed
```
⚠️ **Port collision:** `:8080` is already taken on the box. Run our backend on **`:8090`**:
`uvicorn app.main:app --port 8090`, and set `VITE_API_BASE`/`CORS_ORIGINS` to match.
If instead the backend runs off-box, tunnel: `ssh -L 11434:localhost:11434 user@<box>`.

## 4. Verify the full path
```bash
curl -s http://127.0.0.1:11434/v1/models                          # model server up
curl -s -X POST http://127.0.0.1:8090/api/simulate | python -m json.tool | grep -A2 system_status
# Nemotron status should read "online" with a GB10 latency.
```

## Notes
- The Nemotron adapter **falls back to mock** on any error — a flaky model never breaks
  the demo, it just shows `status: mock`/`degraded`.
- Running the backend ON the GB10 gives the most "fully local" story AND makes Hermes
  (`:8642`, localhost-only) reachable for the Discord hand-off. See `docs/hermes-integration.md`.
