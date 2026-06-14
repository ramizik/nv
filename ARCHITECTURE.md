# Architecture

## Principle
One canonical object — **`LeadAnalysis`** — flows through the entire system. Voice
produces a transcript; the backend enriches it into a full `LeadAnalysis`; the dashboard
renders it; chat summarizes it. Contract: `shared/schemas/lead_analysis.schema.json`.
Define once, render everywhere.

## Components

| Layer | Tech | Responsibility |
|-------|------|----------------|
| Voice | PersonaPlex (or transcript fixture) | Natural intake; emits transcript turns |
| Lead Analyzer (ours) | FastAPI (`backend/app`) | Sequences extract→score→context→notify; assembles `LeadAnalysis`; in-memory store |
| Reasoning | **Local** Nemotron model server on GB10 (or mock heuristic) | Extraction, lead scoring, next-best-action — called directly to stay on-box |
| Clinic context | flat JSON (`shared/clinic_context/brightsmile.json`) | Services, hours, financing, premium-lead rules |
| Messaging / tasks | **Hermes** (teammate's service, `:8642`) | Owns the Discord bot + channel; we hand off the finished alert to it |
| Dashboard | React + Vite + TS (`frontend/`) | Observability: 9 operator panels |

> **Hermes is NOT our backend.** Earlier drafts labeled `backend/app` "Hermes" — that was
> wrong. Hermes is the teammate's separate running service (OpenAI-compatible agent gateway
> on `:8642`, Discord bot, memory, tasks). Our service is the **Lead Analyzer**; it reasons
> locally and hands `LeadAnalysis` to Hermes for the alert. See `docs/hermes-integration.md`.

## Data flow

```
transcript ─▶ InferenceAdapter.analyze(transcript, clinic_context)
                 → {summary, extracted, score, estimated_deal_value,
                    clinic_context_hits, next_best_action}
           ─▶ ChatAdapter.send(analysis) → {platform, sent, preview_markdown}
           ─▶ assemble actions[] timeline + system_status[]
           ─▶ LeadAnalysis  →  store + return  →  dashboard / chat
```

Orchestration lives in `backend/app/services/analyze.py`. Adapters resolved by
`backend/app/adapters/__init__.py` from env (`config.py`).

## Swap-points (the only places mock↔real differ)

1. **`InferenceAdapter`** (`adapters/base.py`)
   - `MockInferenceAdapter` — rule-based extraction + scoring off clinic context (zero deps).
     Grafts hand-tuned prose for the veneers+wedding showcase path.
   - `NemotronInferenceAdapter` — OpenAI-compatible call to the GB10 server; falls back to
     mock on any error.
2. **`ChatAdapter`** (`adapters/base.py`)
   - `MockChatAdapter` — returns alert markdown as a preview.
   - `HermesChatAdapter` — hands the alert to Hermes (`:8642`), which relays it via its
     Discord bot. The real path. Never raises; degrades to preview.
   - `DiscordChatAdapter` — secondary fallback: raw Discord webhook (no bot).

## Hermes integration (the seam)
- **We do reasoning; Hermes does messaging.** Our Lead Analyzer scores the lead by calling
  the **local** Nemotron model server directly (keeps inference on-box). It then hands the
  finished `LeadAnalysis` to Hermes, which owns the Discord bot + channel `1509734278206984194`.
- **Why not route reasoning through Hermes?** Hermes' default model is **cloud Gemini** (plus
  a cloud NVIDIA NIM delegate). Routing scoring through it would send patient conversations
  off-box and break the on-prem guarantee. So scoring bypasses Hermes by design.
- **Cross-host:** Hermes binds `127.0.0.1:8642`. Our backend reaches it only if it runs **on
  the GB10 box** (recommended topology) or via an SSH tunnel. Full detail + the teammate's
  required changes: `docs/hermes-integration.md`.

## Reliability stance
Stability > completeness. Defaults are all-mock and single-machine. Every external call
(Nemotron, Hermes) degrades to mock/preview so the dashboard always renders. Voice is a
fixture by default — live audio is never on the demo critical path.

## Dual-machine model
- **Windows dev machine:** frontend + backend dev, all-mock demo.
- **Remote NVIDIA (GB10) Linux box:** serves Nemotron-120B via **Ollama** (`:11434/v1`,
  OpenAI-compatible, no key) **and** runs Hermes (`:8642`). For the live demo, run our backend
  **on the GB10** so it reaches both over localhost. Backend points at the model with
  `INFERENCE_BACKEND=nemotron` + `NEMOTRON_BASE_URL=http://127.0.0.1:11434/v1`, and at Hermes
  with `CHAT_BACKEND=hermes` + `HERMES_WEBHOOK_URL` (the deliver_only Discord route). `shared/` is
  the source of truth.
- ⚠️ **`:8080` is taken on the box — run our backend on `:8090`** (`uvicorn app.main:app --port 8090`).
- ⚠️ **Single-model residency:** ~120 GB unified memory holds only ONE local model at a time.
  Hermes uses *cloud* Gemini so it doesn't compete for VRAM — but voice/embed models would.
  Keep exactly the demo scoring model loaded; voice stays a fixture (never on the critical path).
