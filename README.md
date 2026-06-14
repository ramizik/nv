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
[Voice transcript]──▶ FastAPI orchestrator (Hermes) ──▶ LeadAnalysis JSON ──┬──▶ React dashboard
  PersonaPlex/fixture     │ InferenceAdapter: mock │ nemotron→GB10           └──▶ ChatAdapter: mock │ discord
                          └ clinic_context.json (BrightSmile rules)
```

The entire system flows **one canonical object — `LeadAnalysis`**
(`shared/schemas/lead_analysis.schema.json`). Two swap-points behind interfaces —
`InferenceAdapter` and `ChatAdapter` — both **default to mock**, so the demo runs 100% on
one machine with zero external deps. Flip **one env var** to use the real GB10 / Discord;
both **degrade to mock on error** so the demo can't hard-fail. Details: `ARCHITECTURE.md`.

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
| Real local inference on GB10 | `INFERENCE_BACKEND=nemotron` · `NEMOTRON_BASE_URL=http://<gb10>:8000/v1` |
| Real Discord staff alert | `CHAT_BACKEND=discord` · `DISCORD_WEBHOOK_URL=...` |

## API (full contract in `docs/integration-plan.md`)

| Method | Route | Purpose |
|--------|-------|---------|
| `POST` | `/api/simulate` | **demo button** — analyze the bundled veneers scenario |
| `POST` | `/api/analyze` | analyze a `scenario` or raw `transcript` |
| `GET`  | `/api/leads` · `/api/leads/{id}` | list / fetch analyzed leads |
| `GET`  | `/api/clinic` · `/api/health` | clinic context · liveness + active backends |

## Docs map
`ROADMAP.md` (full project reference + phases) · `ARCHITECTURE.md` · `DEMO_SCRIPT.md` ·
`docs/judging-story.md` · `docs/integration-plan.md` · `docs/setup-windows.md` · `docs/setup-remote-nvidia.md`
