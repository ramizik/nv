# Hermes Integration — the seam between our Lead Analyzer and the teammate's Hermes

> **TL;DR of the division of labor.** **Hermes** (the teammate's running service) is now our
> **single integration point for BOTH reasoning AND alerts**. We (the **Lead Analyzer**,
> `backend/app`) POST the transcript to Hermes for scoring — **Hermes delegates to its local
> default model Qwen3-30B (Ollama on the GB10)** and returns the `LeadAnalysis` JSON — then we
> hand the finished alert back to Hermes to relay into Discord. Everything stays on-box because
> Hermes' default model is local, not cloud. Hermes also owns the **Discord bot**, memory, and
> tasks. This doc is the contract so neither side builds the same thing twice.

---

## 1. What Hermes actually is (confirmed from the GB10 box)

- A **running service** on the GB10 — **confirmed up**: `GET /health` → 200, `hermes-agent v0.16.0`,
  bound to **`http://127.0.0.1:8642`**.
- **Gateway auth: a bearer IS required on every route.** `_check_auth()` compares
  `Authorization: Bearer <token>` to `API_SERVER_KEY` (set in `~/.hermes/.env`); missing/wrong →
  `401 {"error":{"code":"invalid_api_key"}}`. The server won't even start without the key set.
  → The "invalid api key" we saw was *this*, not a cloud-model key. (Earlier "keyless" note: wrong.)
- **Owns Discord** via a **bot** (`DISCORD_BOT_TOKEN`) — connected; home channel
  **`1509734278206984194`** (`DISCORD_HOME_CHANNEL`), DM allowlist (`DISCORD_ALLOWED_USERS`).
- **CORRECTION — the default model is LOCAL, not cloud.** Verified on the box: `config.yaml`
  `model.default: Qwen3-30B:latest`, provider `custom:lifeos-local`,
  `base_url: http://127.0.0.1:11435/v1`, `api_key: no-key-required`. Earlier notes that claimed
  the default was cloud **`gemini-flash-latest`** were **wrong**. Because the default model runs
  on the GB10 (Ollama), **routing reasoning through Hermes keeps patient conversations on-box** —
  nothing leaves the building. The model behind Hermes is **keyless**; only the gateway itself
  requires the bearer.
- **No `/discord/send` route exists** (every registered route enumerated: `/v1/chat/completions`,
  `/v1/responses`, `/v1/runs`, `/api/sessions/*`, `/api/jobs/*`). BUT the deterministic verbatim
  path we want **already exists as a platform**: the **webhook platform** (`gateway/platforms/webhook.py`)
  in **`deliver_only: true`** mode with **`deliver: discord`** — skips the agent, routes the POST body
  straight through the live Discord adapter to a channel (defaults to the home channel). It is just
  **not enabled in `config.yaml` yet** (no `webhook:` platform block). Enabling it = config, not code.
- Config lives in **`~/.hermes/.env`** + **`~/.hermes/config.yaml`**.

### Why this is the architecture
Because Hermes' default model is **local Qwen3-30B on the GB10**, routing through Hermes does
**not** leave the box — so Hermes becomes our **single integration point for both reasoning and
alerts**, and the "nothing leaves the building" pitch holds. So:

| Concern | Owner | How |
|---|---|---|
| Reasoning / lead scoring | **Hermes (local Qwen3-30B)** | POST the transcript to Hermes `/v1/chat/completions`; it delegates to its local default model and returns the `LeadAnalysis` JSON (`INFERENCE_BACKEND=hermes`) |
| Discord alert / agent tasks | **Hermes** | we hand off the finished `LeadAnalysis` (`CHAT_BACKEND=hermes`) |

Both paths require the gateway bearer (`HERMES_API_KEY = API_SERVER_KEY` from `~/.hermes/.env`);
the model behind the gateway is keyless.

---

## 2. How we call Hermes

Two adapters, two concerns, one gateway.

### 2a. Reasoning — `backend/app/adapters/inference.py`

`HermesInferenceAdapter` is the **primary** inference path: it POSTs the transcript to Hermes
`/v1/chat/completions` (bearer = `HERMES_API_KEY`), Hermes delegates to its local default model
**Qwen3-30B** (Ollama `:11435`), and the returned JSON overlays the `LeadAnalysis` skeleton.
`QwenInferenceAdapter` is a **direct fallback** that talks to Ollama if the gateway is
unreachable. (The old `nemotron.py` direct-Nemotron adapter has been **removed**.) The
connectivity smoke test is `backend/test_hermes_inference.py`.

```
INFERENCE_BACKEND=hermes
HERMES_BASE_URL=http://127.0.0.1:8642
HERMES_API_KEY=                       # = API_SERVER_KEY (from ~/.hermes/.env)
HERMES_INFERENCE_MODEL=               # blank → Hermes' default (Qwen3-30B)
```

Fail-safe: any error degrades to the mock skeleton, so scoring never hard-fails the demo.

### 2b. Alerts — `HermesChatAdapter` (`backend/app/adapters/chat.py`)

`backend/app/adapters/chat.py` supports both delivery paths; it picks the webhook when its URL is set.

**PRIMARY — webhook `deliver_only` (deterministic, no LLM, on-box).** Confirmed from the gateway
source `gateway/platforms/webhook.py`: a webhook platform route with `deliver_only: true` +
`deliver: discord` posts the request **body verbatim** to Discord with **no LLM**. The URL is
`POST http://<host>:<port>/webhooks/<route_name>` — and crucially it is on the **webhook
platform's OWN port (default `8644`), NOT the gateway `8642`**. When `HERMES_WEBHOOK_URL` is set
we POST the rendered markdown straight to that route:
```
POST {HERMES_WEBHOOK_URL}            # e.g. http://127.0.0.1:8644/webhooks/<route_name>
{ "content": "<verbatim markdown alert>", "chat_id": "1509734278206984194" }
```
The route template `"{content}"` renders the body's **`content`** field verbatim, and
`deliver_extra.chat_id: "{chat_id}"` lets the body's `chat_id` override the channel (else it
falls back to the Discord home channel `1509734278206984194`). No model, never leaves the box,
sub-second. The body field names (`content`, `chat_id`) are **co-designed with the route
template** in `config.yaml` (see §5) — keep them matching.

Auth on the webhook route: secret **`INSECURE_NO_AUTH`** is allowed on a loopback bind (the
demo path). HMAC mode expects header **`X-Hub-Signature-256: sha256=<hex>`** (GitHub scheme) or
**`X-Webhook-Signature: <bare hex>`** over the raw body — **the gateway does NOT recognize a
plain `X-Signature` header** (earlier note was wrong). `HERMES_WEBHOOK_SECRET` selects the mode.

**FALLBACK — `/v1/chat/completions`** (only if no webhook URL): asks the agent to post the alert.
Requires the gateway bearer (`HERMES_API_KEY = API_SERVER_KEY`). This routes through Hermes'
default model (local Qwen3-30B, on-box) but is non-deterministic; prefer the webhook for the
real demo.

Both are **fail-safe**: any error (unreachable, 401, timeout) degrades to the preview, so the
dashboard's Chat Notification panel always renders.

Env (in `.env`):
```
CHAT_BACKEND=hermes
HERMES_BASE_URL=http://127.0.0.1:8642
HERMES_DISCORD_CHANNEL=1509734278206984194
HERMES_WEBHOOK_URL=                   # PRIMARY — the deliver_only route URL on port 8644 (from the owner)
HERMES_WEBHOOK_SECRET=                # blank = INSECURE_NO_AUTH demo; else the route's HMAC secret
HERMES_API_KEY=                       # gateway bearer (= API_SERVER_KEY) — required for reasoning + chat fallback
```

HMAC header (confirmed against `gateway/platforms/webhook.py`): use
`X-Hub-Signature-256: sha256=<hex>` or `X-Webhook-Signature: <bare hex>` over the raw body — a
plain `X-Signature` header is **not** recognized. For the demo, an `INSECURE_NO_AUTH` route
(blank secret) sidesteps signing entirely.

---

## 3. Network topology (this is a real gotcha)

Hermes **binds `127.0.0.1`** — it is **not reachable from another host** as-is. Two options:

- **Recommended: co-locate.** Run our `backend/` **on the GB10 box** (the repo is pulled there
  too). Then backend → Hermes gateway (`:8642`) and backend → Hermes webhook route (`:8644`) are
  both `localhost`, and Hermes itself reaches its local model (Ollama `:11435`). ⚠️ **`:8080` is
  already taken on the box — run our backend on `:8090`** (`uvicorn app.main:app --port 8090
  --host 0.0.0.0`); point the dashboard's `VITE_API_BASE` at it.
- **Alternative: SSH tunnel** from wherever our backend runs:
  `ssh -L 8642:127.0.0.1:8642 -L 8644:127.0.0.1:8644 <user>@<gb10>`.

We do **not** need Hermes to rebind to `0.0.0.0` if we co-locate. Co-location is the simplest
path for a reliable demo.

---

## 4. Security flags raised by the Hermes owner (do not ignore)

1. **`~/.hermes/gateway_state.json` leaks a live Telegram bot token** in an error string.
   Anything that ships/relays that file exfiltrates a credential. **Scrub + rotate** it; never
   attach it to a message, paste, or commit. (Not ours to fix — flagging to the owner.)
2. **Never commit `~/.hermes/.env`** or any of the keys above. Our repo's `.gitignore` already
   excludes `.env`; keep Hermes secrets out of this repo entirely.

---

## 5. What the Hermes owner needs to do for us (the ask)

See the ready-to-send checklist in **`docs/ask-hermes-owner.md`**. In short:

1. **Enable a webhook `deliver_only` route** in `~/.hermes/config.yaml` (the `webhook:` platform
   block doesn't exist yet): `deliver: discord`, `deliver_only: true`, template `"{content}"`,
   `deliver_extra.chat_id: "{chat_id}"`, channel defaulting to the home channel, auth
   `INSECURE_NO_AUTH` for the demo (or an HMAC secret). Restart the gateway. **This is the one task.**
2. Send back: the **route URL** (note it's on the **webhook port `8644`**, not the gateway `8642`),
   the **auth mode** (`INSECURE_NO_AUTH`, or HMAC secret + which header: `X-Hub-Signature-256` /
   `X-Webhook-Signature`), and confirm the body field is **`content`** (and `chat_id` overrides the channel).
3. Confirm the **home channel** (`1509734278206984194`) is where staff/judges watch.
4. Help us **co-locate** our backend on the GB10 on **`:8090`** (`:8080` is taken).

What they explicitly do **not** need to do: write a custom `/discord/send` route (the webhook
platform already does this — just enable it); stand up a separate model for us (**Hermes' own
default model, local Qwen3-30B via Ollama `:11435`, already serves our reasoning**); change the
default model; or build any scoring/dashboard — we own that.
