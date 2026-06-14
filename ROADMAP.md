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
| Orchestration / memory / messaging / tasks | **Hermes** = FastAPI (`backend/app`) | live |
| Reasoning + lead scoring + next-best-action | **Nemotron** on GB10 (mock heuristic fallback) | mock→real |
| Cheap extraction/routing (optional) | Qwen / Llama | stretch |
| Backend API/orchestrator | Python + FastAPI | live |
| Dashboard | React + Vite + TypeScript | building |
| Staff notifications | **Discord** webhook (mock preview default) | mock→real |

### Two swap-points (mock ↔ real, env-toggled, fail-safe)
- `InferenceAdapter`: `mock` (rule-based scoring off clinic context) ↔ `nemotron` (GB10).
- `ChatAdapter`: `mock` (preview) ↔ `discord` (live webhook).
Both default to mock and **degrade to mock on any error** — the demo can never hard-fail.

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
- [x] `NemotronInferenceAdapter` + `DiscordChatAdapter` written behind flags (fail-safe)
- [x] **Verified**: `/api/simulate` → HOT 92/0.91, actions, notification, system status
- [x] Core docs: README, ARCHITECTURE, DEMO_SCRIPT, integration-plan, setup-windows/remote, judging-story

### Phase / Layer 2 — Dashboard 🔜 NEXT (target 14:40–15:40)
**Milestone M2: judge can watch the full decision on screen, end-to-end, fully mocked.**
- [ ] Vite + React + TS scaffold + dark operator theme
- [ ] `lib/api.ts` client + `types/` mirroring the schema + bundled JSON fixture fallback
- [ ] **"Simulate Inbound Call"** button → `POST /api/simulate` → populate state
- [ ] 9 panels wired to `LeadAnalysis` fields (see `docs/integration-plan.md` mapping)
- [ ] Hero: score badge (HOT/WARM/COLD) + **Estimated Deal Value** money-shot
- [ ] Polish pass: spacing, color, transcript streaming feel, reason chips

### Phase / Layer 3 — Real integrations (target 15:40–16:40)
**Milestone M3: live Discord alert fires; GB10 Nemotron produces the score.**
- [ ] Discord: `CHAT_BACKEND=discord` + webhook → alert lands on a second screen
- [ ] Nemotron on GB10: serve model (`inference/remote/`), set `INFERENCE_BACKEND=nemotron`,
      verify JSON-out matches the contract; confirm System Health shows "GB10 @ Xms"
- [ ] Confirm fail-safe: kill GB10 / webhook → still renders via mock
- [ ] (stretch) PersonaPlex recorded/live voice → transcript

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
| GB10 model server flaky/slow | `INFERENCE_BACKEND=mock` — heuristic scores identically for the demo |
| Discord webhook fails | Chat Notification Preview panel shows the alert anyway |
| Live voice unreliable | Transcript fixture (default) — never put a mic on the critical path |
| Frontend not done in time | Backend `/docs` (Swagger) + `curl /api/simulate` still tells the story |
| Cross-machine drift | `shared/` is the single source of truth; both machines pull it |

## 5. Definition of done (for the demo)
A judge clicks one button and within seconds sees: a natural transcript, a HOT 92 score with
reasons + a dollar value, a posted staff alert, a drafted follow-up, and a System Health
panel proving it ran locally on the GB10 — in under 3 minutes, repeatable on demand.
