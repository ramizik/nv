# ROADMAP — Local Voice Lead Closer

This is the **canonical project reference**. It holds the full idea (so anyone pulling the
repo on either machine understands what we're building and why) plus the phased,
checkbox-tracked build plan. We update this doc as we build.

**Clock:** started ~14:00, hackathon ends **18:00** (4-hour sprint).
**Prime directive:** one flawless, memorable workflow > broad features. Stability > completeness.

---

## 1. The idea (full reference)

### One-line pitch
An on-prem AI lead-conversion agent for cosmetic dental clinics that answers inbound voice
leads in natural conversation, qualifies them using company context + business rules, scores
lead intent **locally on the GB10**, alerts staff in chat, and shows an observability
dashboard of what the agent understood, decided, and did.

### The problem
Cosmetic dental is high-ticket (veneers $7k–$16k, smile makeovers $12k–$30k) and
competitive. Clinics lose these leads because:
- **After-hours calls** go to voicemail and never call back.
- **Busy front desks** miss or rush calls during the day.
- **Inconsistent qualifying** — staff forget to ask timeline / financing / readiness.
- **Slow follow-up** — the first clinic to respond wins; competitors call back faster.

### The solution
An **always-on, on-prem agent** that owns the *first interaction* — instantly, privately,
consistently — and hands staff a qualified, scored, ready-to-act lead with a drafted
follow-up. It drops in alongside any existing clinic CRM; it is not trying to be the CRM.

### Why local / on-prem (the Dell × NVIDIA GB10 angle)
- **Privacy:** patient health conversations never leave the building (no cloud / BAA risk).
- **Always-on, low per-call cost:** no per-token cloud bill on every after-hours call.
- **Latency:** reasoning in ~100–150ms locally on the GB10.
- Directly fulfills the track's brief: an always-on business agent running locally on the box.

### The clinic (mock business)
**BrightSmile Aesthetics**, Austin TX — premium cosmetic dentistry. Full context (services,
hours, financing policy, insurance stance, premium-lead rules, follow-up tone, FAQ) lives in
`shared/clinic_context/brightsmile.json`. This is the "company context" the agent reasons
against.

### The demo scenario (golden path)
A prospective patient, **Jessica**, calls after hours: *"I'm interested in veneers, I have a
wedding in six weeks, and do you offer financing?"* The agent talks naturally, asks 2–3
qualifying questions, and the system:
1. extracts slots (veneers · 6-week deadline · financing interest · ready to book),
2. consults BrightSmile rules (financing 0% APR, veneer lead-time fits, premium-lead rule),
3. scores **HOT 92/100** (conf 0.91) with reason chips and **$7.2k–$16k** deal value,
4. posts a Discord alert, drafts a concierge follow-up, sets a 30-min callback task,
5. renders all of it on the observability dashboard.

### Three demo surfaces
1. **Voice** — natural inbound intake (transcript fixture for demo reliability; live optional).
2. **Chat** — Discord staff alert with summary, score, urgency, next action.
3. **Dashboard** — the "brain" view: what the agent heard, extracted, checked, decided, did.

### The architectural spine
One canonical object — **`LeadAnalysis`** (`shared/schemas/lead_analysis.schema.json`) —
flows through the whole system. Voice produces a transcript → backend enriches into a full
`LeadAnalysis` → dashboard renders it → chat summarizes it. Define once, render everywhere.

### Tech-stack mapping
| Capability | Tech | Status |
|------------|------|--------|
| Real-time / simulated voice intake | PersonaPlex (fixture default) | mock |
| **Our** lead-analysis orchestrator | **Lead Analyzer** = FastAPI (`backend/app`) | live |
| Reasoning + lead scoring + next-best-action | **Hermes** gateway → local **Qwen3-30B** on GB10 (mock heuristic fallback) | mock→real |
| Heavier reasoning (optional) | Nemotron-120B via Hermes (`HERMES_INFERENCE_MODEL=lifeos-nemotron-120b:latest`) | stretch |
| Messaging / memory / tasks + Discord bot | **Hermes** = teammate's running service `:8642` (reasoning + Discord alert) | live (theirs) |
| Dashboard | React + Vite + TypeScript | done |
| Staff notifications | **Discord** via Hermes' bot (mock preview default) | mock→real |

> ⚠️ **Correction (learned mid-build):** "Hermes" is the **teammate's** service, not our
> backend. Our backend is the **Lead Analyzer**. We do **not** run our own model server —
> we route reasoning **through Hermes**, which delegates to its **local default model,
> Qwen3-30B** (Ollama on the GB10). Inference stays **on-box**. (Earlier note that Hermes'
> default was cloud Gemini was wrong — its default is local Qwen3-30B; routing through it is
> intended.) Hermes also owns the Discord alert. See `docs/hermes-integration.md`.

### Two swap-points (mock ↔ real, env-toggled, fail-safe)
- `InferenceAdapter`: `mock` (rule-based scoring off clinic context) ↔ `hermes` (route reasoning through Hermes → local Qwen3-30B). Optional `qwen` (legacy alias `nemotron`) = DIRECT-to-Ollama (`:11434/v1`) fallback, used ONLY if Hermes is down.
- `ChatAdapter`: `mock` (preview) ↔ `hermes` (hand off to teammate's bot) ↔ `discord` (raw webhook fallback).
Both default to mock and **degrade to mock/preview on any error** — the demo can never hard-fail.

### Observability dashboard (9 panels — operator-friendly, NO raw chain-of-thought)
Lead Summary · Transcript · Qualification Score · Extracted Intents/Entities · Company
Context Retrieved · Agent Action Timeline · Next Best Action · Chat Notification Preview ·
System Health / Model Status. (Plus the Estimated Deal Value money-shot.)

---

## 2. Scope

### In scope (we ARE building)
- One vertical: cosmetic dental clinic (BrightSmile).
- One workflow: after-hours inbound lead qualification + escalation.
- One story: recover and convert high-value leads.
- One visible agent flow across voice → reasoning → chat → dashboard.

### Non-goals (we are NOT building — hard cuts)
- ❌ Full CRM / scheduling / call-center platform / clinic-ops software.
- ❌ Multi-tenant SaaS, auth, DB persistence (in-memory store, single clinic).
- ❌ Live telephony on the critical path (transcript fixture; live voice is stretch only).
- ❌ RAG / vector DB (clinic context is one small flat JSON).
- ❌ Streaming token UI / exposing chain-of-thought.
- ❌ Multi-industry support.

---

## 3. Build plan — phases, milestones, checkboxes

### Phase / Layer 1 — Skeleton + mock end-to-end ✅ DONE (~14:00–14:40)
**Milestone M1: backend serves a full `LeadAnalysis` from a transcript, all-mock.**
- [x] Dual-machine repo structure
- [x] Canonical `LeadAnalysis` schema (`shared/schemas/`)
- [x] BrightSmile clinic context + veneers scenario payload + golden output fixture
- [x] FastAPI orchestrator: `/api/health|clinic|analyze|simulate|leads`
- [x] `InferenceAdapter` (mock = genuine rule-based extraction + scoring) + `ChatAdapter` (mock)
- [x] Real inference adapters (`HermesInferenceAdapter` + `QwenInferenceAdapter`, in
      `backend/app/adapters/inference.py`) + `DiscordChatAdapter` written behind flags (fail-safe)
- [x] **Verified**: `/api/simulate` → HOT 92/0.91, actions, notification, system status
- [x] Core docs: README, ARCHITECTURE, DEMO_SCRIPT, integration-plan, setup-windows/remote, judging-story

### Phase / Layer 2 — Dashboard ✅ DONE (14:40–15:15)
**Milestone M2: judge can watch the full decision on screen, end-to-end, fully mocked.** ✅
- [x] Vite + React + TS scaffold + dark operator theme
- [x] `lib/api.ts` client + `types/` mirroring the schema + bundled JSON fixture fallback
- [x] **"Simulate Inbound Call"** button → `POST /api/simulate` → populate state
- [x] 9 panels wired to `LeadAnalysis` fields (see `docs/integration-plan.md` mapping)
- [x] Hero: score badge (HOT/WARM/COLD, pulsing) + **Estimated Deal Value** money-shot
- [x] Header health pills (API / infer / chat backend); fixture fallback if backend down
- [x] **Verified**: typecheck clean, prod build green, dev server serves 200, live data path OK
- [ ] (optional later) polish pass: transcript auto-scroll/stream feel, micro-animations

### Phase / Layer 3 — Real integrations (target 15:30–16:40)
**Milestone M3: Hermes (→ local Qwen3-30B) produces the score + alert hands off to Hermes.**

_Scoring (route through Hermes → local Qwen3-30B):_
- [x] Inference adapter hardened: overlay-on-mock-skeleton, `<think>`/fence/prose-tolerant JSON
      parse, response_format retry, fail-fast connect (5s) + long read (60s), `_source` marker
- [x] Decision: route reasoning **through Hermes**, which delegates to its **local default
      Qwen3-30B** (fast, resident, coexists with the NIM voice stack). No own model server.
- [x] System Health reflects real state: online (Hermes @ Xms) / degraded (fallback) / mock
- [x] `backend/test_hermes_inference.py` one-shot connectivity test
- [x] **RESOLVED (confirmed on the GB10 box):** Hermes' OpenAI-compatible gateway is up at
      `http://127.0.0.1:8642/v1`, defaulting to local **Qwen3-30B** (~18 GB, MoE ~3B active →
      fast). Optional heavier reasoning via `HERMES_INFERENCE_MODEL=lifeos-nemotron-120b:latest`
      (≈82 GB, slower, monopolizes the box). Underneath, models are served by Ollama on the box;
      a direct `:11434/v1` call is kept ONLY as a fallback if Hermes is down (`qwen` adapter).
      ⚠️ Reality differs from the earlier "serve Nemotron-Super via vLLM on :8000" plan.
- [ ] Run `test_hermes_inference.py` against `:8642/v1` → confirm `_source: hermes`
- [ ] End-to-end: `INFERENCE_BACKEND=hermes` → dashboard shows "Hermes → Qwen3-30B @ Xms"

_Messaging (hand off to teammate's Hermes — `:8642`, owns Discord bot):_
- [x] Learned Hermes' real shape: OpenAI-compatible gateway, bearer `API_SERVER_KEY`, Discord
      bot + channel `1509734278206984194`, default model **local Qwen3-30B** (⇒ on-box reasoning)
- [x] `HermesChatAdapter` scaffolded (`CHAT_BACKEND=hermes`), fail-safe to preview
- [x] Docs corrected: our backend = Lead Analyzer, NOT Hermes; `docs/hermes-integration.md` + ask doc
- [x] **CONFIRMED from gateway source:** Hermes running, `GET /health` → 200 (`hermes-agent v0.16.0`),
      Discord connected, home channel `1509734278206984194`. **Gateway REQUIRES a bearer** on every
      route (`_check_auth` → 401 `invalid_api_key`); `API_SERVER_KEY` is set in `~/.hermes/.env`.
      (Earlier "keyless" note was wrong — the curl 401 was the gateway, not a cloud-model key.)
- [x] **Deterministic path identified:** no `/discord/send` route exists, BUT the **webhook platform**
      (`deliver_only: true` + `deliver: discord`) does exactly what we want — verbatim, no LLM, on-box.
      It's just not enabled in `config.yaml`. ⇒ enabling it is **config, not new route code**.
- [x] `HermesChatAdapter` reworked: webhook `deliver_only` PRIMARY (`HERMES_WEBHOOK_URL`, optional
      HMAC), `/v1/chat/completions`+bearer FALLBACK; both fail-safe to preview. Verified.
- [ ] **BLOCKED on teammate:** enable the webhook `deliver_only` route in `~/.hermes/config.yaml` +
      send back {route URL, auth mode, body field}; co-locate our backend on the GB10 (`:8090`);
      confirm `1509734278206984194` is the staff-watched channel
- [ ] End-to-end: `CHAT_BACKEND=hermes` + `HERMES_WEBHOOK_URL` → real alert appears in Discord
- [ ] (stretch) PersonaPlex recorded voice → transcript

### Phase / Layer 5 — Integration execution on the GB10 box ⬅ NEXT MUST-DO
**Milestone M5: live, deterministic end-to-end on one box — `/api/simulate` → real reasoning
(Hermes → local Qwen3-30B) → verbatim Discord alert.** Ordered by dependency; each step is
small and reversible.

_Reasoning path (route through Hermes, which delegates to the local model):_
- [ ] Set backend `.env`: `INFERENCE_BACKEND=hermes`, `CHAT_BACKEND=hermes`,
      `HERMES_BASE_URL=http://127.0.0.1:8642`, `HERMES_API_KEY=<API_SERVER_KEY from ~/.hermes/.env>`,
      `HERMES_INFERENCE_MODEL=` (blank = Hermes default Qwen3-30B; set `lifeos-nemotron-120b:latest`
      for heavier reasoning), `HERMES_DISCORD_CHANNEL=1509734278206984194`.
- [ ] **Decision (reasoning serving):** route reasoning **through Hermes → its local default
      Qwen3-30B** (on-box, fast, coexists with voice) rather than running our own model server.
      Direct-to-Ollama (`:11434/v1`, the `qwen`/legacy `nemotron` adapter) is kept ONLY as a
      fallback for when Hermes is down. Update `inference/remote/*.sh` + README/ARCH wording from
      "vLLM :8000" / "Ollama direct" to "via Hermes :8642/v1 → local Qwen3-30B" so docs match reality.
- [ ] Run `backend/test_hermes_inference.py` against `:8642/v1`; confirm clean JSON + `_source: hermes`.
      Qwen3-30B is fast on first token; if you switch `HERMES_INFERENCE_MODEL` to the 120B, sanity-check
      latency vs the 60s read timeout before the demo.

_Messaging path (enable the deterministic seam — CONFIG on the Hermes side, no new route code):_
- [ ] **Hermes owner: enable a webhook `deliver_only` route** in `~/.hermes/config.yaml`
      (`platforms.webhook.extra.routes`): `deliver: discord`, `deliver_only: true`, channel defaults
      to the home channel, auth `INSECURE_NO_AUTH` (demo) or HMAC. Template emits the body's
      `content` field verbatim. Restart gateway; send back the route URL + auth mode.
- [x] `HermesChatAdapter` already posts to `HERMES_WEBHOOK_URL` (`{content, chat_id}`, optional
      `X-Signature` HMAC) and falls back to `/v1/chat/completions`+bearer. Nothing left on our side
      but to set the env once the route URL arrives.
- [ ] Set `CHAT_BACKEND=hermes`, `HERMES_BASE_URL=http://127.0.0.1:8642`,
      `HERMES_WEBHOOK_URL=<route>`, `HERMES_DISCORD_CHANNEL=1509734278206984194`.

_Co-location & wiring (Hermes binds 127.0.0.1, so the backend must live on this box):_
- [ ] Run our FastAPI backend **on the GB10** so Hermes (`:8642`, and its local Ollama at `:11434`) is localhost.
- [ ] ⚠️ **Port collision:** `:8080` is already taken on this box (a uvicorn is bound there).
      Run our backend on a free port (e.g. `:8090`) and update `VITE_API_BASE` / `CORS_ORIGINS` to match.
- [ ] End-to-end smoke: `curl -X POST http://127.0.0.1:8090/api/simulate` → HOT score from
      Hermes → local Qwen3-30B + the alert visibly lands in Discord, exactly as formatted.

_Security (carry-over, do not skip):_
- [ ] Rotate the GitHub PAT used to push this update (it was shared in plaintext).
- [ ] Hermes owner: scrub + rotate the live Telegram token leaked in `~/.hermes/gateway_state.json`.

### Phase / Layer 4 — Demo hardening (target 16:40–17:40)
**Milestone M4: 3-minute run rehearsed and bulletproof.**
- [ ] Rehearse `DEMO_SCRIPT.md` end-to-end (≥2 dry runs)
- [ ] Verify every fallback path renders cleanly
- [ ] Second-screen layout: dashboard + Discord side by side
- [ ] Pre-cache / pin the golden run so it's identical every time
- [ ] (stretch) Second scenario: cold price-shopper → COLD, to show the agent discriminates

### Buffer / freeze (17:40–18:00)
- [ ] Code freeze. No new features. Last dry run. Breathe.

---

## 4. Risk register & fallbacks
| Risk | Fallback |
|------|----------|
| Hermes gateway flaky/slow | `INFERENCE_BACKEND=mock` — heuristic scores identically; or `INFERENCE_BACKEND=qwen` (direct-to-Ollama `:11434/v1`) as a backstop if Hermes is down |
| Heavier 120B model cold/slow on first token | Keep the default **Qwen3-30B** (fast, resident); only set `HERMES_INFERENCE_MODEL=lifeos-nemotron-120b:latest` after pre-warming; read timeout 90s |
| ~120 GB ⇒ only ONE model resident | Default Qwen3-30B (~18 GB) coexists with the NIM voice stack; the 120B (~82 GB) monopolizes the box — switch to it only *before* the run, never mid-demo |
| Discord webhook fails | Chat Notification Preview panel shows the alert anyway |
| Live voice unreliable | Transcript fixture (default) — never put a mic on the critical path |
| Frontend not done in time | Backend `/docs` (Swagger) + `curl /api/simulate` still tells the story |
| Cross-machine drift | `shared/` is the single source of truth; both machines pull it |

## 5. Definition of done (for the demo)
A judge clicks one button and within seconds sees: a natural transcript, a HOT 92 score with
reasons + a dollar value, a posted staff alert, a drafted follow-up, and a System Health
panel proving it ran locally on the GB10 — in under 3 minutes, repeatable on demand.
