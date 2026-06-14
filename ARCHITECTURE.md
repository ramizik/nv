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
| Reasoning | **Hermes** (`:8642`) → **local Qwen3-30B** via Ollama on GB10 (or mock heuristic) | Extraction, lead scoring, next-best-action — routed through Hermes to its on-box default model |
| Clinic context | flat JSON (`shared/clinic_context/brightsmile.json`) | Services, hours, financing, premium-lead rules |
| Messaging / tasks | **Hermes** (teammate's service, `:8642`) | Owns the Discord bot + channel; we hand off the finished alert to it |
| Dashboard | React + Vite + TS (`frontend/`) | Observability: 9 operator panels |

> **Hermes is NOT our backend.** Earlier drafts labeled `backend/app` "Hermes" — that was
> wrong. Hermes is the teammate's separate running service (OpenAI-compatible agent gateway
> on `:8642`, Discord bot, memory, tasks). Our service is the **Lead Analyzer**; it does NOT
> run its own model — it routes reasoning *through* Hermes (which delegates to its on-box
> default model, Qwen3-30B) and hands `LeadAnalysis` to Hermes for the alert.
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
`backend/app/adapters/inference.py` (`HermesInferenceAdapter` primary, `QwenInferenceAdapter`
direct fallback); the old `backend/app/adapters/nemotron.py` was removed.

## Swap-points (the only places mock↔real differ)

1. **`InferenceAdapter`** (`adapters/base.py`, impls in `adapters/inference.py`)
   - `MockInferenceAdapter` (default) — rule-based extraction + scoring off clinic context
     (zero deps). Grafts hand-tuned prose for the veneers+wedding showcase path.
   - `HermesInferenceAdapter` (REAL) — OpenAI-compatible call to **Hermes** (`:8642/v1`),
     which delegates to its on-box default model (Qwen3-30B via Ollama); falls back to mock
     on any error.
   - `QwenInferenceAdapter` (optional `qwen`, legacy alias `nemotron`) — DIRECT-to-Ollama
     call to `:11434/v1` ourselves; used only as a fallback if Hermes is down. Also falls
     back to mock on any error.
2. **`ChatAdapter`** (`adapters/base.py`)
   - `MockChatAdapter` — returns alert markdown as a preview.
   - `HermesChatAdapter` — hands the alert to Hermes (`:8642`), which relays it via its
     Discord bot. The real path. Never raises; degrades to preview.
   - `DiscordChatAdapter` — secondary fallback: raw Discord webhook (no bot).

## Hermes integration (the seam)
- **Hermes does both reasoning and messaging.** Our Lead Analyzer does NOT run its own model.
  It scores the lead by calling Hermes (`:8642/v1`), which **delegates reasoning to its local
  default model — Qwen3-30B, served via Ollama on the GB10** — so inference stays on-box. It
  then hands the finished `LeadAnalysis` to Hermes, which owns the Discord bot + channel
  `1509734278206984194`.
- **Is routing through Hermes still on-box?** Yes. Hermes' default model is **local
  Qwen3-30B, NOT cloud Gemini** — so routing scoring through Hermes keeps patient
  conversations on the box. This is the intended real path. (An earlier draft claimed Hermes
  defaulted to cloud Gemini and that we must bypass it; that is no longer true.)
- **Model choice:** blank `HERMES_INFERENCE_MODEL` = Hermes default Qwen3-30B (≈18 GB, MoE
  ~3B active → fast, coexists with the NIM voice stack). Set `lifeos-nemotron-120b:latest`
  to force the heavier/slower 120B (≈82 GB) that monopolizes the box. Only ONE large model
  is resident at a time (128 GB unified).
- **Fallback:** if Hermes is down, `INFERENCE_BACKEND=qwen` calls Ollama (`:11434/v1`)
  directly ourselves. Both paths degrade to mock/preview on any error.
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
- **Remote NVIDIA (GB10) Linux box:** runs Hermes (`:8642`), which delegates reasoning to
  **local Qwen3-30B** served via **Ollama** (`:11434/v1`, OpenAI-compatible, no key). For the
  live demo, run our backend **on the GB10** so it reaches Hermes over localhost. Backend
  points at Hermes for both reasoning and messaging:
  `INFERENCE_BACKEND=hermes` + `CHAT_BACKEND=hermes` + `HERMES_BASE_URL=http://127.0.0.1:8642`
  + `HERMES_API_KEY=<API_SERVER_KEY from ~/.hermes/.env>` (gateway bearer; the model itself is
  keyless) + `HERMES_DISCORD_CHANNEL=1509734278206984194` + `HERMES_INFERENCE_MODEL=` (blank =
  Qwen3-30B). `shared/` is the source of truth.
- ⚠️ **`:8080` is taken on the box — run our backend on `:8090`** (`uvicorn app.main:app --port 8090`).
- ⚠️ **Single-model residency:** 128 GB unified memory holds only ONE large local model at a
  time. Qwen3-30B (≈18 GB) coexists with the NIM voice/embed stack; Nemotron-120B (≈82 GB)
  monopolizes the box. Keep exactly the demo reasoning model loaded; voice stays a fixture
  (never on the critical path).
