# Setup — Remote NVIDIA (GB10) Linux box

The real path routes reasoning through **Hermes** (OpenAI-compatible gateway on
`http://127.0.0.1:8642/v1`), which **delegates to its local default model Qwen3-30B** on the
GB10 (Ollama). We run **no model server of our own** — inference stays on-prem via Hermes.
The backend goes real by setting `INFERENCE_BACKEND=hermes`.

## Prereqs
- NVIDIA drivers + CUDA (`nvidia-smi` works)
- Python 3.12 / Docker (depending on serving choice)
- The repo pulled here too (`shared/` is the cross-machine source of truth)
- Hermes running on `:8642` (teammate's gateway) — see `docs/hermes-integration.md`

## 1. Go real — point the backend at Hermes (PRIMARY path)
No model server to start: Hermes already serves Qwen3-30B locally. Just set the env. In `.env`
(grab `HERMES_API_KEY` from `~/.hermes/.env`'s `API_SERVER_KEY` — don't paste the value here):
```
INFERENCE_BACKEND=hermes
CHAT_BACKEND=hermes
HERMES_BASE_URL=http://127.0.0.1:8642
HERMES_API_KEY=<API_SERVER_KEY from ~/.hermes/.env>
HERMES_DISCORD_CHANNEL=1509734278206984194
HERMES_INFERENCE_MODEL=        # blank = Hermes default (local Qwen3-30B)
```
Health check (expect **"Qwen via Hermes" online**):
```bash
curl -fsS http://127.0.0.1:8642/health
curl -fsS -X POST http://127.0.0.1:8642/v1/chat/completions \
  -H "Authorization: Bearer $HERMES_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"","messages":[{"role":"user","content":"Reply with the single word: ok"}],"max_tokens":5}'
```

## 2. (Optional) Direct-Ollama FALLBACK — `INFERENCE_BACKEND=qwen`
If Hermes is unavailable, the backend can talk to Ollama directly. This is the only case where
the warm scripts below are needed (Hermes otherwise already serves Qwen).
```bash
cd inference/remote
./start_qwen.sh                # ensures Ollama is up and WARMS Qwen3-30B:latest
./healthcheck.sh               # curls /v1/models and a tiny completion on :11434
```
In `.env`:
```
INFERENCE_BACKEND=qwen
QWEN_BASE_URL=http://127.0.0.1:11434/v1
QWEN_MODEL=Qwen3-30B:latest
QWEN_API_KEY=not-needed
QWEN_TIMEOUT_READ=60
QWEN_THINKING_DIRECTIVE=/no_think
```
The adapter tolerates servers that reject `response_format: json_object` (it retries without it)
and strips any `<think>` blocks, so Ollama output parses cleanly. (Legacy `NEMOTRON_*` envs are
still honored.)

> ⚠️ **~120 GB unified memory ⇒ only ONE large model resident at a time.** Qwen3-30B (~18 GB,
> ~3B active) is fast, stays resident, and coexists with the NIM voice stack. Nemotron-120B
> (~82 GB) is an optional heavier alternative that monopolizes the box; switch to it BEFORE the
> demo (Ollama unloads Qwen and loads it, a one-time cold delay).
>
> Alternative (not the demo path): vLLM on :8000 — see the commented block in `start_qwen.sh`.

## 3. (Optional) PersonaPlex voice
`./start_personaplex.sh` is a placeholder for the voice service. For the hackathon demo we
use a transcript fixture; wire live voice only after the dashboard + chat are solid.

## 4. Run the backend on the GB10
**Recommended: run the backend ON the GB10** so Hermes (`:8642`) and Ollama (`:11434`, both
bound to localhost) are reachable. ⚠️ **Port collision:** `:8080` is already taken on the box.
Run our backend on **`:8090`**: `uvicorn app.main:app --port 8090`, and set
`VITE_API_BASE`/`CORS_ORIGINS` to match. If the backend runs off-box, tunnel to Hermes:
`ssh -L 8642:localhost:8642 user@<box>` (and `11434` too if using the fallback).

## 5. Verify the full path
```bash
curl -fsS http://127.0.0.1:8642/health                            # Hermes up
curl -s -X POST http://127.0.0.1:8090/api/simulate | python -m json.tool | grep -A2 system_status
# Inference status should read "online" (Qwen via Hermes) with a GB10 latency.
```
Connectivity smoke test: `backend/test_hermes_inference.py`.

## Notes
- Both inference adapters (`backend/app/adapters/inference.py`) **fall back to mock** on any
  error — a flaky path never breaks the demo, it just shows `status: mock`/`degraded`.
- Running the backend ON the GB10 gives the most "fully local" story AND keeps Hermes
  (`:8642`, localhost-only) reachable for both reasoning and the Discord hand-off. See
  `docs/hermes-integration.md`.
