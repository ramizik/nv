# Hermes Integration — the seam between our Lead Analyzer and the teammate's Hermes

> **TL;DR of the division of labor.** We (the **Lead Analyzer**, `backend/app`) reason on the
> **local** Nemotron model server and produce a complete `LeadAnalysis`. **Hermes** (the
> teammate's running service) owns the **Discord bot**, memory, and tasks. We hand the
> finished alert to Hermes; we do **not** route reasoning through it. This doc is the contract
> so neither side builds the same thing twice.

---

## 1. What Hermes actually is (confirmed from the GB10 box)

- A **running service** on the GB10 — already up (PID seen at report time), bound to
  **`http://127.0.0.1:8642`**.
- **OpenAI-compatible gateway.** Confirmed endpoints:
  - `GET /health`
  - `POST /v1/chat/completions` — bearer auth: `Authorization: Bearer $API_SERVER_KEY`
- **Owns Discord** via a **bot** (`DISCORD_BOT_TOKEN`), default channel **`1509734278206984194`**,
  with a DM allowlist (`DISCORD_ALLOWED_USERS`).
- **Default reasoning model is CLOUD:** `GOOGLE_API_KEY` → Gemini, plus a cloud NVIDIA NIM
  delegate (`NVIDIA_API_KEY`, `z-ai/glm-5.1`). It also has voice tool keys (`VOICE_TOOLS_OPENAI_KEY`).
- Config lives in **`~/.hermes/.env`**.

### Why this changes our architecture
Because Hermes defaults to **cloud** models, **we must not send patient conversations through
it for scoring** — that would leave the box and break our "nothing leaves the building" pitch.
So:

| Concern | Owner | How |
|---|---|---|
| Reasoning / lead scoring | **us** | call the **local** Nemotron model server directly (`INFERENCE_BACKEND=nemotron`) |
| Discord alert / agent tasks | **Hermes** | we hand off the finished `LeadAnalysis` (`CHAT_BACKEND=hermes`) |

---

## 2. How we call Hermes today (provisional)

`backend/app/adapters/chat.py → HermesChatAdapter` POSTs to the **confirmed** endpoint:

```
POST {HERMES_BASE_URL}/v1/chat/completions
Authorization: Bearer {HERMES_API_KEY}     # = Hermes' API_SERVER_KEY
{ "messages": [ {role:"system",...}, {role:"user", content:"Post this alert to channel <id>: <markdown>"} ] }
```

It is **fail-safe**: any error (unreachable, 401, timeout) degrades to the preview, so the
dashboard's Chat Notification panel always renders.

⚠️ **This is provisional.** Routing a *fixed* message through an LLM agent is non-deterministic
(the agent may reword or not post). We want a deterministic path — see the ask below. When the
teammate exposes it, we swap the body of `HermesChatAdapter.send()` to call it.

Env (in `.env`):
```
CHAT_BACKEND=hermes
HERMES_BASE_URL=http://127.0.0.1:8642
HERMES_API_KEY=<Hermes API_SERVER_KEY>
HERMES_DISCORD_CHANNEL=1509734278206984194
```

---

## 3. Network topology (this is a real gotcha)

Hermes **binds `127.0.0.1`** — it is **not reachable from another host** as-is. Two options:

- **Recommended: co-locate.** Run our `backend/` **on the GB10 box** (the repo is pulled there
  too). Then backend → Nemotron model server and backend → Hermes are both `localhost`. The
  React dashboard can run anywhere pointing `VITE_API_BASE` at the GB10 backend (bind our
  backend to `0.0.0.0:8080` for that).
- **Alternative: SSH tunnel** from wherever our backend runs:
  `ssh -L 8642:127.0.0.1:8642 <user>@<gb10>` (and similarly for the model server port).

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

1. Share **`API_SERVER_KEY`** (the bearer) so we can call `:8642`.
2. Expose a **deterministic Discord-send** — e.g. `POST /discord/send {channel, content}` that
   posts `content` verbatim via the bot (no LLM in the loop). This is the big one.
3. Confirm the **alert channel id** (default `1509734278206984194`) is the right #front-desk.
4. Help us **co-locate** our backend on the GB10 (or open a tunnel) so `:8642` is reachable.
5. Serve **Nemotron-Super** on an OpenAI-compatible port (separate from Hermes) and give us the
   base URL + model id — this is the *scoring* path, independent of Hermes.

What they explicitly do **not** need to do: change Hermes' default model, route our scoring, or
build any dashboard/scoring logic — we own all of that.
