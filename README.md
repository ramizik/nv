# Local Voice Lead Closer 🦷🔥

**An always-on, on-prem AI agent that answers inbound voice leads for a cosmetic dental
clinic, qualifies them, scores intent locally, alerts staff in chat, and shows the whole
decision on an observability dashboard.** Runs entirely on the **Dell Pro Max with GB10** —
no cloud, patient conversations never leave the building.

> **Track:** Dell × NVIDIA — Local AI on Dell Pro Max with GB10.
> **Vertical:** cosmetic dental (**BrightSmile Aesthetics**). **Workflow:** after-hours
> inbound lead qualification + escalation. **Story:** recover high-value leads staff miss.

---

## For judges — the 30-second version

A $16k veneer lead calls a **closed** clinic at 9pm. Today that's a voicemail and a lost
patient. Here, the agent:

1. **Answers naturally** and asks 2–3 qualifying questions (voice).
2. **Extracts** structured facts — service, deadline, financing, buying stage.
3. **Reasons** against *this clinic's own rules* (financing, veneer lead-time, premium-lead policy) — **locally on the GB10**.
4. **Scores** the lead → **HOT 92/100**, conf 0.91, with plain-English reasons and a **$7.2k–$16k** deal value.
5. **Acts:** posts a staff alert to Discord, drafts a concierge follow-up, sets a 30-min callback task.
6. **Shows its work** on a 9-panel operator dashboard (no raw chain-of-thought).

**ROI:** one recovered case pays for the hardware many times over. See `docs/judging-story.md`
and the run-of-show in `DEMO_SCRIPT.md`.

## What makes it agentic (not a chatbot)
Extract → reason against clinic rules → decide a score + urgency → **act across three
surfaces** (chat alert, drafted message, callback task) → render the decision trail.

---

## Architecture (one glance)

```
[Voice transcript]──▶ Lead Analyzer (FastAPI) ──▶ LeadAnalysis JSON ──┬──▶ React dashboard
  fixture / ASR later   │ InferenceAdapter: mock │ qwen                └──▶ ChatAdapter: mock │ hermes
                        │   └▶ Ollama (:11434/v1) ──▶ LOCAL Qwen3-30B       └▶ Hermes (teammate's
                        │      on-box reasoning                                bot) → Discord #front-desk
                        └ clinic_context.json (BrightSmile rules)
```

The entire system flows **one canonical object — `LeadAnalysis`**
(`shared/schemas/lead_analysis.schema.json`). Two swap-points behind interfaces —
`InferenceAdapter` and `ChatAdapter` — both **default to mock**, so the demo runs 100% on
one machine with zero external deps. Flip env vars to use the real GB10 Qwen / Hermes stack;
both **degrade to mock on error** so the demo can't hard-fail.

**Reasoning routes directly to LOCAL Qwen3-30B served via Ollama (`:11434`) on the GB10.** So
inference stays **on-box** (patient conversations never leave the building). Hermes owns the
Discord bot and agent/tool gateway, so the *finished* alert is handed to it via its
`deliver_only` webhook. Details: `ARCHITECTURE.md` · `docs/hermes-integration.md`.

The backend also exposes a token-authed **LifeOS compatibility layer** under `/v1/*`
(health, models, timeline, memory, actions) plus a WebSocket `/v1/audio/stream` audio-ingest
endpoint backed by a local SQLite store — so this app can stand in for the LifeOS API surface
on the box. `/api/health` reports live probes of the whole fleet (Qwen, embeddings, TTS, ASR, Hermes).

> **Pitch:** Reasoning runs on local Qwen, Hermes handles alerts/actions, and the NIM
> sidecars run on the Dell Pro Max GB10.

## Repo layout

| Path | What | Runs on |
|------|------|---------|
| `backend/` | FastAPI orchestrator + adapters | either |
| `frontend/` | React + Vite + TS dashboard | Windows dev |
| `inference/remote/` | GB10 Hermes/Ollama health scripts | **remote NVIDIA Linux** |
| `inference/local/` | mock inference + sample I/O | either |
| `shared/` | clinic context, schemas, sample payloads (cross-machine source of truth) | either |
| `scripts/{windows,linux}/` | setup + run helpers | Windows / Linux |
| `docs/` | setup, API contract, judging story | — |

---

## Quickstart (all-mock — the safe demo, one machine)

**Backend** (Python 3.12) — from repo root:
```bash
cp .env.example .env                      # defaults are all-mock
cd backend
uv venv .venv && . .venv/bin/activate     # or: python -m venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt        # or: pip install -r requirements.txt
uvicorn app.main:app --port 8090
```
Smoke-test the golden path:
```bash
curl -X POST http://localhost:8090/api/simulate | python -m json.tool
# → HOT 92/100, $7.2k–$16k, actions[], notification, system_status
```

**Frontend** (Node 18+) — another terminal:
```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
```

Windows: `scripts/windows/*.ps1`. GB10 wiring: `docs/setup-remote-nvidia.md`.

## Go live (flip mock → real, no code changes)

| Switch | Env vars |
|--------|----------|
| Real on-box inference via Qwen | `INFERENCE_BACKEND=qwen` · `QWEN_BASE_URL=http://127.0.0.1:11434/v1` · `QWEN_MODEL=lifeos-qwen3-30b:latest` · `QWEN_THINKING_DIRECTIVE=/no_think` |
| Real staff alert via Hermes bot | `CHAT_BACKEND=hermes` · `HERMES_BASE_URL=http://127.0.0.1:8642` · `HERMES_API_KEY=<API_SERVER_KEY from ~/.hermes/.env>` · `HERMES_DISCORD_CHANNEL=1509734278206984194` |
| Optional Hermes inference path | `INFERENCE_BACKEND=hermes` · routes reasoning through Hermes' configured provider — **not guaranteed to be local Qwen**, so the on-box pitch may not hold |
| Raw Discord webhook (fallback) | `CHAT_BACKEND=discord` · `DISCORD_WEBHOOK_URL=...` |

> **GB10 demo reality:** Qwen3-30B runs locally through Ollama on `:11434/v1` and is the
> main scoring/conversation brain. Hermes on `:8642` owns agent/tool/alert delivery.
> Embeddings (`:8001`) and TTS (`:8003`) are running NIM sidecars; `/api/health` probes them
> live. ASR (`nemotron-asr-streaming`, `:8002`) is pending the NGC key; Parakeet was dropped
> (its amd64-only image won't run on GB10 arm64). **`:8080` is taken, so our backend runs on `:8090`.**
> ⚠️ 128 GB unified ⇒ **only ONE large local model resident at a time** — pre-warm exactly the
> demo model. See `docs/hermes-integration.md` for the seam, topology, and the Hermes-owner checklist.

## API (full contract in `docs/integration-plan.md`)

| Method | Route | Purpose |
|--------|-------|---------|
| `POST` | `/api/simulate` | **demo button** — analyze the bundled veneers scenario |
| `POST` | `/api/analyze` | analyze a `scenario` or raw `transcript` |
| `GET`  | `/api/leads` · `/api/leads/{id}` | list / fetch analyzed leads |
| `GET`  | `/api/clinic` | BrightSmile clinic context |
| `GET`  | `/api/health` | liveness + active backends + **live fleet probes** (Qwen / embed / TTS / ASR / Hermes) |
| `*`    | `/v1/*` | **LifeOS compatibility layer** (token-authed): `health`, `models`, `timeline`, `memory`, `actions`, `actions/propose` |
| `WS`   | `/v1/audio/stream` | LifeOS audio ingest → SQLite store (streams + frames) |

## Docs map
`ARCHITECTURE.md` · `DEMO_SCRIPT.md` · `docs/judging-story.md` ·
`docs/integration-plan.md` (FE↔BE API) · **`docs/hermes-integration.md`** (the Hermes seam) ·
`docs/setup-remote-nvidia.md` (GB10 wiring)
