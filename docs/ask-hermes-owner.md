# For the Hermes owner — what we need to integrate (copy/paste to them)

> Context: I (the Lead Analyzer / dashboard side) score inbound cosmetic-dental leads on the
> **local** Nemotron model and produce one `LeadAnalysis` JSON. I want your **Hermes** service
> to deliver the staff alert to Discord — you already own that bot, so I won't rebuild it. Here's
> exactly what I need from you. None of this requires you to touch scoring or the dashboard.

## 1. Give me the Hermes API key (bearer)
- **What:** the value of `API_SERVER_KEY` from `~/.hermes/.env` (the bearer for `:8642`).
- **Why:** without it every call to `/v1/chat/completions` is 401 and my alert silently falls
  back to a preview-only panel.
- I'll put it in my `.env` as `HERMES_API_KEY=` — I will **not** commit it.

## 2. Expose a DETERMINISTIC Discord-send endpoint  ← the important one
- **What:** a thin endpoint that posts a message verbatim via your bot, no LLM in the loop. Ideal:
  ```
  POST /discord/send
  { "channel": "1509734278206984194", "content": "<pre-formatted markdown>" }
  → 200 { "sent": true, "message_id": "..." }
  ```
- **Why:** right now my only option is `/v1/chat/completions`, i.e. *asking the agent* to post a
  fixed alert. That's non-deterministic (it may reword, summarize, or skip). For a live demo I
  need the alert to post **exactly** as formatted, every time.
- If you already have a tool/function that does this internally, just wrap it in one HTTP route
  and tell me the path + payload shape. I'll point my `HermesChatAdapter` straight at it.

## 3. Confirm the alert channel
- **What:** is `DISCORD_HOME_CHANNEL = 1509734278206984194` the channel staff will watch for
  these lead alerts? If there's a dedicated #front-desk / #leads channel, give me that id.
- **Why:** so the demo alert lands where the judges (and "staff") are looking.

## 4. Make Hermes reachable from my backend
- Hermes binds `127.0.0.1:8642`, so my backend can't reach it from another host as-is.
- **Simplest:** let me run my backend **on the GB10 box** (repo's already pulled there) — then
  it's all localhost, no bind change needed. Tell me a port I can use (I default to `:8080`).
- **Or:** I SSH-tunnel `:8642` (and the model port). Either works — just tell me which you prefer.

## 5. Serve Nemotron-Super for scoring (separate from Hermes)
- **What:** serve **Nemotron-Super** on an OpenAI-compatible port (vLLM or NIM), and send me:
  1. base URL, e.g. `http://127.0.0.1:8000/v1`
  2. the exact model id from `GET /v1/models`
  3. whether it needs an API key
- **Why:** this is my **reasoning** path — I call it **directly**, not through Hermes (so patient
  conversations stay on-box; Hermes' default model is cloud Gemini). It's independent of items 1–4.

## 6. Security hygiene (you flagged it — flagging back)
- `~/.hermes/gateway_state.json` has a **live Telegram token** in an error string. Please scrub +
  rotate it, and don't attach that file to anything. Not mine to touch.

---
### What you do NOT need to do
- ❌ Change Hermes' default model or route my scoring through Hermes.
- ❌ Build any lead scoring, qualification, or dashboard — I own all of that.
- ❌ Format the alert — I send you ready-to-post markdown; you just relay it.
