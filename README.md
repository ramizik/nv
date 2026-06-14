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
  PersonaPlex/fixture   │ InferenceAdapter: mock │ nemotron            └──▶ ChatAdapter: mock │ hermes
                        │   └▶ LOCAL Nemotron model server on GB10          └▶ Hermes (teammate's
                        └ clinic_context.json (BrightSmile rules)              bot) → Discord #front-desk
```

The entire system flows **one canonical object — `LeadAnalysis`**
(`shared/schemas/lead_analysis.schema.json`). Two swap-points behind interfaces —
`InferenceAdapter` and `ChatAdapter` — both **default to mock**, so the demo runs 100% on
one machine with zero external deps. Flip **one env var** to use the real GB10 / Hermes;
both **degrade to mock on error** so the demo can't hard-fail.

**Reasoning runs on the LOCAL Nemotron model server, never through Hermes** — Hermes' own
default model is cloud Gemini, so routing scoring through it would send patient
conversations off-box. We reason locally and only hand the *finished* alert to Hermes (which
owns the Discord bot). Details: `ARCHITECTURE.md` · `docs/hermes-integration.md`.

## Repo layout

| Path | What | Runs on |
|------|------|---------|
| `backend/` | FastAPI orchestrator + adapters | either |
| `frontend/` | React + Vite + TS dashboard | Windows dev |
| `inference/remote/` | GB10 model-server start/health scripts | **remote NVIDIA Linux** |
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
uvicorn app.main:app --port 8080
```
Smoke-test the golden path:
```bash
curl -X POST http://localhost:8080/api/simulate | python -m json.tool
# → HOT 92/100, $7.2k–$16k, actions[], notification, system_status
```

**Frontend** (Node 18+) — another terminal:
```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
```

Windows: `scripts/windows/*.ps1` + `docs/setup-windows.md`. GB10 wiring: `docs/setup-remote-nvidia.md`.

## Go live (flip mock → real, no code changes)

| Switch | Env vars |
|--------|----------|
| Real local inference on GB10 | `INFERENCE_BACKEND=nemotron` · `NEMOTRON_BASE_URL=http://127.0.0.1:11434/v1` · `NEMOTRON_MODEL=lifeos-nemotron-120b:latest` (Ollama, no key) |
| Real staff alert via Hermes bot | `CHAT_BACKEND=hermes` · `HERMES_API_KEY=<Hermes API_SERVER_KEY>` (backend must run on the GB10 box or tunnel `:8642`) |
| Raw Discord webhook (fallback) | `CHAT_BACKEND=discord` · `DISCORD_WEBHOOK_URL=...` |

> **GB10 demo reality:** Nemotron-120B is served via **Ollama** on `:11434`; Hermes (teammate's
> service, owns Discord) binds `127.0.0.1:8642`; **`:8080` is taken so run our backend on `:8090`**.
> ⚠️ ~120 GB total ⇒ **only ONE local model resident at a time** — pre-warm exactly the demo
> model. See `docs/hermes-integration.md` for the seam, topology, and the Hermes-owner checklist.

## API (full contract in `docs/integration-plan.md`)

| Method | Route | Purpose |
|--------|-------|---------|
| `POST` | `/api/simulate` | **demo button** — analyze the bundled veneers scenario |
| `POST` | `/api/analyze` | analyze a `scenario` or raw `transcript` |
| `GET`  | `/api/leads` · `/api/leads/{id}` | list / fetch analyzed leads |
| `GET`  | `/api/clinic` · `/api/health` | clinic context · liveness + active backends |

## Docs map
`ROADMAP.md` (full project reference + phases) · `ARCHITECTURE.md` · `DEMO_SCRIPT.md` ·
`docs/judging-story.md` · `docs/integration-plan.md` (FE↔BE API) ·
**`docs/hermes-integration.md`** (the Hermes seam) · `docs/ask-hermes-owner.md` (teammate checklist) ·
`docs/setup-windows.md` · `docs/setup-remote-nvidia.md`
