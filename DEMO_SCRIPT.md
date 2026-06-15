# Demo Script — 3 minutes

**Goal:** judge instantly understands: *clinic was closed, a $16k lead called, the local
agent caught it, qualified it, scored it HOT, alerted staff, and drafted the callback —
all on-prem on the GB10.*

## Setup (before judges arrive)
- Backend running: `uvicorn app.main:app --port 8090` (repo root `.env` set).
- Frontend running: `npm run dev` → dashboard open at `http://localhost:5173`.
- For the live wow: `INFERENCE_BACKEND=qwen` + `CHAT_BACKEND=hermes` — reasoning runs on
  local Qwen (`:11434`) and Hermes posts the alert to Discord via its `deliver_only` webhook
  (verified working). Keep the Discord channel visible on a second screen.
- If anything is flaky: keep all-mock — the dashboard still shows the alert preview and
  System Health degrades to "mock" without hard-failing.

## Run of show

**0:00 — Frame the pain (15s)**
> "Cosmetic dental clinics lose multi-thousand-dollar leads after hours. A patient calls
> about veneers at 9pm, nobody answers, they book with a competitor. Our agent runs
> locally on the Dell GB10 — no cloud, patient data never leaves the building."

**0:15 — Trigger the call (15s)**
- Click **Simulate Inbound Call**. The transcript streams into the Transcript panel.
> "After-hours call. The agent talks naturally, asks two qualifying questions."

**0:30 — The brain lights up (60s)** — walk the panels left to right:
- **Extracted Intents/Entities:** veneers · wedding in 6 weeks · financing interest · ready to book.
- **Qualification Score:** **HOT 92/100**, confidence 0.91, reason chips.
- **Company Context Retrieved:** financing 0% APR, veneer lead-time fits, premium-lead rule hit.
- **Estimated Deal Value:** **$7,200–$16,000**. ← *point at this number.*
> "It didn't just transcribe — it reasoned against this clinic's own rules, locally."

**1:30 — It took action (45s)**
- **Agent Action Timeline:** extract → context check → score → **alert posted** → draft → callback reminder.
- Show the **Discord channel** (second screen): the HOT-lead alert is there.
- **Next Best Action:** read the drafted concierge follow-up aloud.
> "Staff get a structured alert and a ready-to-send message within seconds."

**2:15 — Proof it's local (20s)**
- **System Health:** live probes — Qwen **direct on :11434** · Hermes alerts online ·
  Embeddings (:8001) · TTS (:8003), all green on the GB10.
> "Reasoning runs on local Qwen, Hermes handles the alert/action handoff, and the NIM
> sidecars are ready on the Dell Pro Max GB10 — and this panel is probing them live."

**2:35 — Close on ROI (25s)**
> "One recovered veneer case pays for the hardware many times over. This is an always-on
> revenue recovery agent that runs entirely on-prem. That's the pitch."

## Failure fallbacks
- GB10 / Qwen down → stays HOT 92 via mock; System Health reads "mock" (don't dwell, story holds).
- Hermes / Discord down → alert still shows in the Chat Notification Preview panel.
- Never do live microphone audio. Always the fixture transcript.
