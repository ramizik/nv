# Hermes Integration — the seam between our Lead Analyzer and the teammate's Hermes

> **TL;DR of the division of labor.** We (the **Lead Analyzer**, `backend/app`) reason on the
> **local** Nemotron model server and produce a complete `LeadAnalysis`. **Hermes** (the
> teammate's running service) owns the **Discord bot**, memory, and tasks. We hand the
> finished alert to Hermes; we do **not** route reasoning through it. This doc is the contract
> so neither side builds the same thing twice.

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
- **Default chat model is CLOUD:** `gemini-flash-latest` (config.yaml) — off-box, non-deterministic.
- **No `/discord/send` route exists** (every registered route enumerated: `/v1/chat/completions`,
  `/v1/responses`, `/v1/runs`, `/api/sessions/*`, `/api/jobs/*`). BUT the deterministic verbatim
  path we want **already exists as a platform**: the **webhook platform** (`gateway/platforms/webhook.py`)
  in **`deliver_only: true`** mode with **`deliver: discord`** — skips the agent, routes the POST body
  straight through the live Discord adapter to a channel (defaults to the home channel). It is just
  **not enabled in `config.yaml` yet** (no `webhook:` platform block). Enabling it = config, not code.
- Config lives in **`~/.hermes/.env`** + **`~/.hermes/config.yaml`**.

### Why this changes our architecture
Because Hermes defaults to **cloud** models, **we must not send patient conversations through
it for scoring** — that would leave the box and break our "nothing leaves the building" pitch.
So:

| Concern | Owner | How |
|---|---|---|
| Reasoning / lead scoring | **us** | call the **local** Nemotron model server directly (`INFERENCE_BACKEND=nemotron`) |
| Discord alert / agent tasks | **Hermes** | we hand off the finished `LeadAnalysis` (`CHAT_BACKEND=hermes`) |

---

## 2. How we call Hermes (`HermesChatAdapter`)

`backend/app/adapters/chat.py` supports both paths; it picks the webhook when its URL is set.

**PRIMARY — webhook `deliver_only` (deterministic, no LLM, on-box).** When `HERMES_WEBHOOK_URL`
is set we POST the rendered markdown straight to the Hermes webhook route:
```
POST {HERMES_WEBHOOK_URL}
{ "content": "<verbatim markdown alert>", "chat_id": "1509734278206984194" }
# optional: X-Signature: sha256=<HMAC(secret, raw_body)>  when HERMES_WEBHOOK_SECRET is set
```
`deliver_only` makes the posted body the Discord message — no model, no `gemini-flash`, never
leaves the box, sub-second. The body field names (`content`, `chat_id`) are **co-designed with
the route template** in `config.yaml` (see §5) — keep them matching.

**FALLBACK — `/v1/chat/completions`** (only if no webhook URL): asks the agent to post the alert.
Requires the gateway bearer (`HERMES_API_KEY = API_SERVER_KEY`) and routes through the cloud
model — non-deterministic + off-box. Avoid for the real demo.

Both are **fail-safe**: any error (unreachable, 401, timeout) degrades to the preview, so the
dashboard's Chat Notification panel always renders.

Env (in `.env`):
```
CHAT_BACKEND=hermes
HERMES_BASE_URL=http://127.0.0.1:8642
HERMES_DISCORD_CHANNEL=1509734278206984194
HERMES_WEBHOOK_URL=                   # PRIMARY — the deliver_only route URL (from the owner)
HERMES_WEBHOOK_SECRET=                # blank = INSECURE_NO_AUTH demo; else the route's HMAC secret
HERMES_API_KEY=                       # only for the chat fallback (= API_SERVER_KEY)
```

⚠️ One thing to confirm against `gateway/platforms/webhook.py`: the **HMAC header name +
algorithm** (we assume `X-Signature: sha256=<hex over raw body>`). For the demo, an
`INSECURE_NO_AUTH` route (blank secret) sidesteps this entirely.

---

## 3. Network topology (this is a real gotcha)

Hermes **binds `127.0.0.1`** — it is **not reachable from another host** as-is. Two options:

- **Recommended: co-locate.** Run our `backend/` **on the GB10 box** (the repo is pulled there
  too). Then backend → Nemotron (Ollama `:11434`) and backend → Hermes (`:8642`) are both
  `localhost`. ⚠️ **`:8080` is already taken on the box — run our backend on `:8090`**
  (`uvicorn app.main:app --port 8090 --host 0.0.0.0`); point the dashboard's `VITE_API_BASE` at it.
- **Alternative: SSH tunnel** from wherever our backend runs:
  `ssh -L 8642:127.0.0.1:8642 -L 11434:127.0.0.1:11434 <user>@<gb10>`.

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
   block doesn't exist yet): `deliver: discord`, `deliver_only: true`, channel defaulting to the
   home channel, auth `INSECURE_NO_AUTH` for the demo (or an HMAC secret). Make the route template
   emit the POST body's **`content`** field verbatim. Restart the gateway. **This is the one task.**
2. Send back: the **route URL**, the **auth mode** (INSECURE_NO_AUTH or HMAC secret + header/algo),
   and confirm the body field is **`content`** (and `chat_id` overrides the channel).
3. Confirm the **home channel** (`1509734278206984194`) is where staff/judges watch.
4. Help us **co-locate** our backend on the GB10 on **`:8090`** (`:8080` is taken).

What they explicitly do **not** need to do: write a custom `/discord/send` route (the webhook
platform already does this — just enable it); serve a model for us (**Nemotron-120B is already up
via Ollama `:11434`**); change the default model; or build any scoring/dashboard — we own that.
