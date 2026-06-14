# Project: Lead Analyzer — Dell × NVIDIA Hackathon

## ⏰ Environment: live hackathon, hard ~3-hour limit
- **Dell × NVIDIA hackathon** — *Local AI on Dell Pro Max with GB10*. This is a timed sprint
  with a **hard deadline ~3 hours out**. Time is the scarcest resource.
- **Posture:** stability > completeness. A working demo beats a half-finished feature.
  - Smallest change that makes the demo work. No refactors, no "while I'm here."
  - Don't start long/irreversible work (big installs, multi-minute model loads, rebuilds)
    without flagging the cost first.
  - Verify cheaply (one `curl` against the golden path), then stop.
  - The demo is built to **degrade to mock and never hard-fail** — preserve that property.
- **Don't trust the wall clock for the deadline** (machines may be in different timezones);
  confirm remaining time with the user.

## Tech stack
- **Backend** (`backend/`): Python 3.12, **FastAPI** + uvicorn on **:8080**, `httpx`,
  `python-dotenv`. Venv via `uv` (or stdlib venv). Entry: `app.main:app`.
- **Frontend** (`frontend/`): **React + Vite + TypeScript**, npm, dev server on **:5173**.
- **Contract:** one canonical `LeadAnalysis` JSON object flows through everything
  (`shared/schemas/lead_analysis.schema.json`). Define once, render everywhere.
- **Two swap-points, both default to `mock`** (zero-dep single-machine demo):
  - `InferenceAdapter`: `mock` | `hermes` (REAL → route reasoning through Hermes → local
    Qwen3-30B). Optional `qwen` (legacy alias `nemotron`) = DIRECT-to-Ollama (`:11434/v1`)
    fallback, used ONLY if Hermes is down.
  - `ChatAdapter`: `mock` | `hermes` | `discord`
- **Reasoning routes through Hermes, which delegates to its local default model — Qwen3-30B
  (Ollama on the DGX).** Inference stays **on-box**; we don't run our own model server.
  (Hermes' default is **local Qwen3-30B, NOT cloud Gemini** — routing through it is intended
  and keeps patient data on-box.)

## Team: 2 teammates working concurrently
- **You / this repo:** the **Lead Analyzer** — backend orchestrator + React dashboard.
- **Teammate A — Hermes owner:** runs **Hermes**, a separate agent gateway
  (OpenAI-compatible, **:8642**, **bearer-authed** `API_SERVER_KEY` on every route) that
  **owns the Discord bot + channel** (`1509734278206984194`). Real alert path = its **webhook
  `deliver_only`** platform (verbatim, no LLM). Hermes is *not* our backend — we only hand it a
  finished `LeadAnalysis` for the staff alert. See `docs/hermes-integration.md`.
- **Teammate B — DGX/model owner:** manages the model server + NIM voice services on the box.
- **Rules of the road:** don't edit Hermes' service; don't restart shared services or swap
  the resident model without asking; keep `shared/` as the agreed cross-machine source of
  truth and avoid conflicting edits there.

## The remote server (Dell Pro Max "GB10" / DGX) — what this dev box must know
- **Topology:** you develop here; the GB10 is a **separate remote Linux box** that runs Hermes
  (which serves reasoning via its local model) + the NIM voice services. For the live demo, the
  backend is best run **on the GB10** so it reaches Hermes (and its local Ollama) over localhost.
- **Unified memory:** 128 GiB shared CPU+GPU (~121.6 GiB usable). **Only one large LLM fits
  resident at a time** — the 120B (~82 GB) evicts the lighter models and crowds the voice
  stack. `nvidia-smi` shows memory as "Not Supported" (unified); the box uses `free -h`.
- **Real reasoning routes through Hermes on `:8642`** (OpenAI-compatible gateway), which
  delegates to its local default model **Qwen3-30B** (served by Ollama on the box). We do NOT
  stand up our own model server. To go real, set in `.env`:
  ```
  INFERENCE_BACKEND=hermes
  CHAT_BACKEND=hermes
  HERMES_BASE_URL=http://127.0.0.1:8642             # localhost if backend runs on the GB10
  HERMES_API_KEY=<API_SERVER_KEY from ~/.hermes/.env>   # gateway bearer; model itself is keyless
  HERMES_DISCORD_CHANNEL=1509734278206984194
  HERMES_INFERENCE_MODEL=                            # blank = Hermes default Qwen3-30B
  ```
  - default **Qwen3-30B**: ~18 GB, MoE ~3B active → fast, resident, coexists with the voice
    services → the demo path.
  - optional heavier reasoning: set `HERMES_INFERENCE_MODEL=lifeos-nemotron-120b:latest`
    (~82 GB, ~2× slower, monopolizes the box). The inference adapter falls back to mock on any
    error, so latency/flakiness can't break the demo — but watch first-token latency on the 120B.
  - direct-to-Ollama (`:11434/v1`) via the `qwen`/legacy `nemotron` adapter is a fallback ONLY
    for when Hermes is down — not the normal path.
- **Hermes binds `127.0.0.1:8642`** → the `INFERENCE_BACKEND=hermes` and `CHAT_BACKEND=hermes`
  paths only work if the backend runs on the GB10 or you SSH-tunnel.
- **Also on the box:** NIM TTS (:8003), NIM embeddings (:8001), NIM ASR (being pulled).
- **Shared, multi-agent box:** teammates are live. Loading/unloading models and restarting
  containers affects others — coordinate, don't clobber.

## Quickstart (all-mock, this machine, zero deps)
```bash
cp .env.example .env            # defaults are all-mock
cd backend && uv venv .venv && . .venv/bin/activate
uv pip install -r requirements.txt
uvicorn app.main:app --port 8080
curl -X POST http://localhost:8080/api/simulate | python -m json.tool   # → HOT 92/100
```
Frontend: `cd frontend && npm install && npm run dev` → http://localhost:5173

## Docs map
`README.md` · `ARCHITECTURE.md` · `ROADMAP.md` / `DEMO_SCRIPT.md` ·
`docs/hermes-integration.md` (the Hermes integration guide)
