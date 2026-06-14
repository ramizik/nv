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
| Orchestrator (Hermes) | FastAPI (`backend/app`) | Sequences extract→score→context→notify; assembles `LeadAnalysis`; in-memory store |
| Reasoning | Nemotron on GB10 (or mock heuristic) | Extraction, lead scoring, next-best-action |
| Clinic context | flat JSON (`shared/clinic_context/brightsmile.json`) | Services, hours, financing, premium-lead rules |
| Chat | Discord webhook (or mock preview) | Staff alert with score + next action |
| Dashboard | React + Vite + TS (`frontend/`) | Observability: 9 operator panels |

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
   - `DiscordChatAdapter` — POSTs to a Discord webhook; never raises on failure.

## Reliability stance
Stability > completeness. Defaults are all-mock and single-machine. Every external call
(GB10, Discord) degrades to mock so the dashboard always renders. Voice is a fixture by
default — live audio is never on the demo critical path.

## Dual-machine model
- **Windows dev machine:** frontend + backend dev, all-mock demo.
- **Remote NVIDIA (GB10) Linux box:** serves Nemotron via an OpenAI-compatible endpoint
  (`inference/remote/`). Backend points at it with `INFERENCE_BACKEND=nemotron` +
  `NEMOTRON_BASE_URL`. `shared/` is the cross-machine source of truth, pulled on both.
