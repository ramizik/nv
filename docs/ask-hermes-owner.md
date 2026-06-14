# For the Hermes owner — what we need to integrate (copy/paste to them)

> Context: I (the Lead Analyzer / dashboard side) score inbound cosmetic-dental leads and produce
> one `LeadAnalysis` JSON. I want to **route the reasoning through your Hermes gateway**, which
> delegates to its **local default model (Qwen3-30B via Ollama on this box)** — so inference stays
> on-box and I don't run my own model server. I also want Hermes to **deliver the staff alert to
> Discord** — you already own that bot, so I won't rebuild it. Here's exactly what I need from you.
> None of this requires you to touch scoring logic or the dashboard.

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

> If for any reason the webhook can't be enabled, my ChatAdapter falls back to
> `/v1/chat/completions` (with `deliver: discord`) — that just needs the gateway bearer
> (`API_SERVER_KEY`), see §4. It stays on-box (local Qwen3-30B), so it's a fine fallback.

## 2. Confirm the alert channel

- **What:** is `DISCORD_HOME_CHANNEL = 1509734278206984194` the channel staff will watch for
these lead alerts? If there's a dedicated #front-desk / #leads channel, give me that id.
- **Why:** so the demo alert lands where the judges (and "staff") are looking.

## 3. Make Hermes reachable from my backend

- Hermes binds `127.0.0.1:8642`, so my backend can't reach it from another host as-is.
- **Simplest:** let me run my backend **on the GB10 box** (repo's already pulled there) — then
it's all localhost, no bind change needed. I'll use `**:8090`** (since `:8080` is already taken).
- **Or:** I SSH-tunnel `:8642` (and `:11434`). Either works — just tell me which you prefer.

## 4. Reasoning through Hermes → local Qwen3-30B  ← I need the gateway bearer

- **The plan:** my backend POSTs the conversation to Hermes `/v1/chat/completions` and Hermes
delegates to its **local default model, Qwen3-30B** (served via Ollama on this box, ~18 GB MoE
/ ~3B active → fast, resident, coexists with the NIM voice stack). Scoring now goes **through
Hermes → Qwen**, on-box — nothing leaves the building.
- **What I need from you:**
  1. Keep **Hermes running** with its **local Qwen3-30B default** (no cloud model).
  2. Share the gateway bearer (**`API_SERVER_KEY`** from `~/.hermes/.env`) so my backend can
     call `/v1/chat/completions`. I'll set `HERMES_API_KEY` from it.
  3. Confirm the default model id, or what to pass — I'll leave `HERMES_INFERENCE_MODEL` blank
     to take the Qwen3-30B default unless you tell me otherwise.
- **Note:** Nemotron-120B (~82 GB) is an optional heavier/slower alternative; we are **not**
asking you to pre-warm it. Qwen3-30B is the default reasoning path. If you ever swap the
resident model, just tell me — I won't touch it.

## 5. Security hygiene (you flagged it — flagging back)

- `~/.hermes/gateway_state.json` has a **live Telegram token** in an error string. Please scrub +
rotate it, and don't attach that file to anything. Not mine to touch.

---

### What you do NOT need to do

- ❌ Build any lead scoring, qualification, or dashboard logic — I own all of that. I send
  Hermes the prompt; Hermes' local Qwen does the raw reasoning, I do everything around it.
- ❌ Switch Hermes' default off the local Qwen3-30B to a cloud model — that would send patient
  data off-box and break the on-prem pitch.
- ❌ Format the alert — I send you ready-to-post markdown; you just relay it.

