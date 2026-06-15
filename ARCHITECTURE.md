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
| Reasoning | **Qwen3-30B** via local Ollama on GB10 (`:11434/v1`) or mock heuristic | Extraction, lead scoring, next-best-action |
| Clinic context | flat JSON (`shared/clinic_context/brightsmile.json`) | Services, hours, financing, premium-lead rules |
| Messaging / tasks | **Hermes** (teammate's service, `:8642`) | Owns the Discord bot + channel; we hand off the finished alert to it |
| Dashboard | React + Vite + TS (`frontend/`) | Observability: 9 operator panels |

> **Hermes is NOT our backend.** Earlier drafts labeled `backend/app` "Hermes" — that was
> wrong. Hermes is the teammate's separate running service (OpenAI-compatible agent gateway
> on `:8642`, Discord bot, memory, tasks). Our service is the **Lead Analyzer**; it does NOT
> run Hermes. It routes reasoning to local Qwen and hands `LeadAnalysis` to Hermes for the alert.
> See `docs/hermes-integration.md`.

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
`backend/app/adapters/__init__.py` from env (`config.py`). The inference adapter lives in
`backend/app/adapters/inference.py` (`QwenInferenceAdapter` primary, `HermesInferenceAdapter`
optional gateway path); the old `backend/app/adapters/nemotron.py` was removed.

## Swap-points (the only places mock↔real differ)

1. **`InferenceAdapter`** (`adapters/base.py`, impls in `adapters/inference.py`)
   - `MockInferenceAdapter` (default) — rule-based extraction + scoring off clinic context
     (zero deps). Grafts hand-tuned prose for the veneers+wedding showcase path.
   - `QwenInferenceAdapter` (REAL) — direct local call to Qwen on Ollama (`:11434/v1`);
     falls back to mock on any error.
   - `HermesInferenceAdapter` (optional) — OpenAI-compatible call to **Hermes** (`:8642/v1`)
     using Hermes' configured provider; also falls back to mock on any error.
2. **`ChatAdapter`** (`adapters/base.py`)
   - `MockChatAdapter` — returns alert markdown as a preview.
   - `HermesChatAdapter` — hands the alert to Hermes (`:8642`), which relays it via its
     Discord bot. The real path. Never raises; degrades to preview.
   - `DiscordChatAdapter` — secondary fallback: raw Discord webhook (no bot).

## Hermes integration (the seam)
- **Hermes does messaging/actions; Qwen does reasoning.** Our Lead Analyzer scores the lead
  by calling local Qwen (`:11434/v1`) and then hands the finished `LeadAnalysis` to Hermes,
  which owns the Discord bot + channel `1509734278206984194`.
- **Why not route inference through Hermes?** The local-Qwen Hermes path was unstable with
  the full Hermes prompt, so Hermes was restored to a reliable Gemini default. This repo keeps
  patient/demo inference on-box by calling Qwen directly.
- **Model choice:** `QWEN_MODEL=lifeos-qwen3-30b:latest` is the normal hot model. Nemotron-120B
  is a deep-planning profile and not part of this app's hot path.
- **Fallback:** both real adapters degrade to mock/preview on any error.
- **Cross-host:** Hermes binds `127.0.0.1:8642`. Our backend reaches it only if it runs **on
  the GB10 box** (recommended topology) or via an SSH tunnel. Full detail + the teammate's
  required changes: `docs/hermes-integration.md`.

## Reliability stance
Stability > completeness. Defaults are all-mock and single-machine. Every external call
(Hermes inference, direct-Ollama fallback, Hermes alert) degrades to mock/preview so the
dashboard always renders. The connectivity test is `backend/test_hermes_inference.py` (the
old `test_nemotron.py` was removed). Voice is a fixture by default — live audio is never on
the demo critical path.

## Dual-machine model
- **Windows dev machine:** frontend + backend dev, all-mock demo.
- **Remote NVIDIA (GB10) Linux box:** runs local Qwen3-30B through **Ollama** (`:11434/v1`)
  for reasoning, plus Hermes (`:8642`) for alerts/actions. For the live demo, run our backend
  **on the GB10** so it reaches all loopback services:
  `INFERENCE_BACKEND=qwen` + `CHAT_BACKEND=hermes` + `QWEN_MODEL=lifeos-qwen3-30b:latest`
  + `HERMES_BASE_URL=http://127.0.0.1:8642` + `HERMES_API_KEY=<API_SERVER_KEY from ~/.hermes/.env>`.
  `shared/` is the source of truth.
- ⚠️ **`:8080` is taken on the box — run our backend on `:8090`** (`uvicorn app.main:app --port 8090`).
- ⚠️ **Single-model residency:** 128 GB unified memory holds only ONE large local model at a
  time. Qwen3-30B (≈18 GB) coexists with the NIM voice/embed stack; Nemotron-120B (≈82 GB)
  monopolizes the box. Keep exactly the demo reasoning model loaded; voice stays a fixture
  (never on the critical path).
