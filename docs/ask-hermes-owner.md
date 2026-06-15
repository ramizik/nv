# For the Hermes owner — what we need to integrate (copy/paste to them)

> Context: I (the Lead Analyzer / dashboard side) score inbound cosmetic-dental leads and produce
> one `LeadAnalysis` JSON. Inference now goes directly to local Qwen3-30B via Ollama. I want
> Hermes to **deliver the staff alert to Discord** and remain the gateway for actions/tools —
> you already own that bot, so I won't rebuild it. Here's exactly what I need from you.
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

## 4. Hermes gateway bearer

- **What I need from you:** share the gateway bearer (**`API_SERVER_KEY`** from
  `~/.hermes/.env`) so my backend can call protected Hermes routes. I'll set `HERMES_API_KEY`
  from it.
- **Not needed for inference:** this repo calls local Qwen directly at
  `http://127.0.0.1:11434/v1`.

## 5. Voice (ASR/TTS) + embeddings — how should I reach the NIM models?  ← need a decision

I want the full local fleet in play, not just reasoning: **ASR** (nemotron-asr-streaming /
parakeet-0.6b-tdt) to turn the caller's audio into the transcript, **TTS** (magpie) for Ava's
side, and **embeddings** (llama-nemotron-embed-1b-v2) for semantic clinic-context retrieval.

**What I found on the box (so we don't guess):**
- `GET :8642/v1/models` returns **only `hermes-agent`** — i.e. Hermes is a *chat-completions
  agent gateway*, it does **not** currently proxy embeddings or voice. There's no
  `/v1/embeddings`, no ASR/TTS route on `:8642`.
- The NIM containers ARE up and reachable **directly**: embed `nvidia/llama-nemotron-embed-1b-v2`
  at **:8001** (OpenAI-style `/v1/models` works), TTS at **:8003** (custom/gRPC, not `/v1`).
  ASR isn't listening yet (still pulling).

So "everything through Hermes" can't cover voice/embed as-is. **Which do you want?**
  1. **I call the NIM containers directly** (on-box localhost — `:8001` embed, `:8003` TTS, ASR
     port TBD). These aren't LLM reasoning, so direct on-box calls don't weaken the on-prem
     pitch. Fastest path; no work for you. ← my default unless you object.
  2. **You add proxy routes on Hermes** for embeddings/ASR/TTS so I have a single integration
     point. Cleaner, but it's real work on your side and Hermes isn't built for it today.
  3. **Leave voice/embed mock** for the demo (transcript stays a fixture, context-match stays
     keyword-based) and only ship local-Qwen reasoning plus Hermes alerts.

Tell me 1/2/3 and (if 1) confirm the ASR container's port + API once it's running. Until you
answer, I'm keeping voice/embed on the safe mock path.

## 6. Security hygiene (you flagged it — flagging back)

- `~/.hermes/gateway_state.json` has a **live Telegram token** in an error string. Please scrub +
rotate it, and don't attach that file to anything. Not mine to touch.

---

### What you do NOT need to do

- ❌ Build any lead scoring, qualification, or dashboard logic — I own all of that.
- ❌ Change Hermes' default model for this repo — inference uses local Qwen directly.
- ❌ Format the alert — I send you ready-to-post markdown; you just relay it.
