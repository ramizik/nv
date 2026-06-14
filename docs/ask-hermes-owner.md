# For the Hermes owner — what we need to integrate (copy/paste to them)

> Context: I (the Lead Analyzer / dashboard side) score inbound cosmetic-dental leads on the
> **local** Nemotron model and produce one `LeadAnalysis` JSON. I want your **Hermes** service
> to deliver the staff alert to Discord — you already own that bot, so I won't rebuild it. Here's
> exactly what I need from you. None of this requires you to touch scoring or the dashboard.

## 1. Enable a webhook `deliver_only` route  ← the ONE task (config, not code)

Your investigation already found the right mechanism — the **webhook platform** in
`deliver_only` mode with `deliver: discord`. It posts a body **verbatim** to a channel, **no
LLM**, on-box, sub-second. It's just not enabled in `~/.hermes/config.yaml` yet (no `webhook:`
block). Please add a route, restart the gateway, and send me the details.

- **What I need it to do:** accept a POST whose `content` field is the message, post it
verbatim to the Discord home channel (`chat_id` in the body can override the channel).
- **Auth:** `INSECURE_NO_AUTH` is fine for the demo. If you'd rather use the per-route HMAC
secret, tell me the **header name + algorithm** (I default to `X-Signature: sha256=<hex over raw body>`).
- **Send me back (3 things):**
  1. the **route URL** (e.g. `http://127.0.0.1:8642/webhook/lead-alert`),
  2. the **auth mode** (`INSECURE_NO_AUTH`, or the HMAC secret + header/algo),
  3. confirm the body field is `content` (and `chat_id` overrides the channel).
- I'll set `HERMES_WEBHOOK_URL` (+ `HERMES_WEBHOOK_SECRET` if any) and my `HermesChatAdapter`
posts straight to it. Done.

> If for any reason the webhook can't be enabled, my adapter falls back to `/v1/chat/completions`
> — but that needs the gateway bearer (`API_SERVER_KEY`) **and** routes through cloud
> `gemini-flash-latest` (off-box, may reword). It's a last resort, not the demo path.

## 2. Confirm the alert channel

- **What:** is `DISCORD_HOME_CHANNEL = 1509734278206984194` the channel staff will watch for
these lead alerts? If there's a dedicated #front-desk / #leads channel, give me that id.
- **Why:** so the demo alert lands where the judges (and "staff") are looking.

## 3. Make Hermes reachable from my backend

- Hermes binds `127.0.0.1:8642`, so my backend can't reach it from another host as-is.
- **Simplest:** let me run my backend **on the GB10 box** (repo's already pulled there) — then
it's all localhost, no bind change needed. I'll use `**:8090`** (since `:8080` is already taken).
- **Or:** I SSH-tunnel `:8642` (and `:11434`). Either works — just tell me which you prefer.

## 4. Nemotron scoring — already up, nothing to do ✅

- **Confirmed:** Nemotron-120B is already served via **Ollama** at `http://127.0.0.1:11434/v1`
(`lifeos-nemotron-120b:latest`, no API key). I call it **directly**, not through Hermes (so
patient conversations stay on-box; Hermes' default model is cloud Gemini).
- **Only ask:** ⚠️ ~120 GB total means **one model resident at a time** — please keep the 120B
loaded (pre-warmed) for the demo and don't spin up voice/embed/Qwen alongside it. If we decide
the 120B is too slow live, we'll switch the resident model to `lifeos-qwen3-30b:latest` *before*
the run, not during.

## 5. Security hygiene (you flagged it — flagging back)

- `~/.hermes/gateway_state.json` has a **live Telegram token** in an error string. Please scrub +
rotate it, and don't attach that file to anything. Not mine to touch.

---

### What you do NOT need to do

- ❌ Change Hermes' default model or route my scoring through Hermes.
- ❌ Build any lead scoring, qualification, or dashboard — I own all of that.
- ❌ Format the alert — I send you ready-to-post markdown; you just relay it.

