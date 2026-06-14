# For the Hermes owner — what we need to integrate (copy/paste to them)

> Context: I (the Lead Analyzer / dashboard side) score inbound cosmetic-dental leads on the
> **local** Nemotron model and produce one `LeadAnalysis` JSON. I want your **Hermes** service
> to deliver the staff alert to Discord — you already own that bot, so I won't rebuild it. Here's
> exactly what I need from you. None of this requires you to touch scoring or the dashboard.

## 1. Hermes API key — not needed ✅
- Confirmed: Hermes runs locally on the box and is **keyless**, so I don't need `API_SERVER_KEY`.
  My adapter only sends a bearer if one is set, and leaves it blank otherwise. Nothing to do here.

## 2. Expose a DETERMINISTIC Discord-send endpoint  ← the important one (confirmed missing)
- **What:** a thin endpoint that posts a message verbatim via your bot, no LLM in the loop. Ideal:
  ```
  POST /discord/send
  { "channel": "1509734278206984194", "content": "<pre-formatted markdown>" }
  → 200 { "sent": true, "message_id": "..." }
  ```
- **Why:** I checked — this doesn't exist yet. The verbatim path is your in-process
  `send_message_tool` / `DiscordAdapter.send()`; the HTTP API (`:8642`) is agent-chat only. My only
  current option is *asking the agent* to post a fixed alert via `/v1/chat/completions`, which is
  non-deterministic (it may reword, summarize, or skip). For a live demo the alert must post
  **exactly** as formatted, every time.
- **Lift:** ~30 lines — wrap the existing `DiscordAdapter.send()` in one bearer-authed route. Tell
  me the path + payload shape and I'll point my `HermesChatAdapter` straight at it.

## 3. Confirm the alert channel
- **What:** is `DISCORD_HOME_CHANNEL = 1509734278206984194` the channel staff will watch for
  these lead alerts? If there's a dedicated #front-desk / #leads channel, give me that id.
- **Why:** so the demo alert lands where the judges (and "staff") are looking.

## 4. Make Hermes reachable from my backend
- Hermes binds `127.0.0.1:8642`, so my backend can't reach it from another host as-is.
- **Simplest:** let me run my backend **on the GB10 box** (repo's already pulled there) — then
  it's all localhost, no bind change needed. I'll use **`:8090`** (since `:8080` is already taken).
- **Or:** I SSH-tunnel `:8642` (and `:11434`). Either works — just tell me which you prefer.

## 5. Nemotron scoring — already up, nothing to do ✅
- **Confirmed:** Nemotron-120B is already served via **Ollama** at `http://127.0.0.1:11434/v1`
  (`lifeos-nemotron-120b:latest`, no API key). I call it **directly**, not through Hermes (so
  patient conversations stay on-box; Hermes' default model is cloud Gemini).
- **Only ask:** ⚠️ ~120 GB total means **one model resident at a time** — please keep the 120B
  loaded (pre-warmed) for the demo and don't spin up voice/embed/Qwen alongside it. If we decide
  the 120B is too slow live, we'll switch the resident model to `lifeos-qwen3-30b:latest` *before*
  the run, not during.

## 6. Security hygiene (you flagged it — flagging back)
- `~/.hermes/gateway_state.json` has a **live Telegram token** in an error string. Please scrub +
  rotate it, and don't attach that file to anything. Not mine to touch.

---
### What you do NOT need to do
- ❌ Change Hermes' default model or route my scoring through Hermes.
- ❌ Build any lead scoring, qualification, or dashboard — I own all of that.
- ❌ Format the alert — I send you ready-to-post markdown; you just relay it.
