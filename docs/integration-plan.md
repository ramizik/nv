# Integration Plan — Frontend ↔ Backend API Contract

Base URL: `http://localhost:8080` (set `VITE_API_BASE`). All responses JSON.
The big object is **`LeadAnalysis`** — schema: `shared/schemas/lead_analysis.schema.json`.

## Endpoints

### `GET /api/health`
```json
{ "status": "ok", "inference_backend": "mock", "chat_backend": "mock", "discord_configured": false }
```

### `GET /api/clinic`
Returns the full BrightSmile clinic context (for a context/debug panel). Optional in UI.

### `POST /api/analyze`
Analyze a live lead transcript (e.g. a Discord voice/text interaction) and file it.
```json
{
  "transcript": [{ "speaker": "lead", "text": "..." , "ts": "00:06" }],
  "lead": { "name": "Jessica Moreno", "phone": "+1-512-555-0822" },
  "channel": "voice", "after_hours": true, "notify": true
}
```
Returns a complete `LeadAnalysis`.

### `GET /api/leads` / `GET /api/leads/{lead_id}`
List all / fetch one lead from the persisted records book.

## `LeadAnalysis` fields → dashboard panels

| Panel | Field(s) |
|-------|----------|
| Lead Summary | `lead`, `summary`, `after_hours`, `received_at` |
| Transcript | `transcript[]` |
| Qualification Score | `score.{label,value,confidence,reason_tags,urgency_reasoning}` |
| Extracted Intents/Entities | `extracted.*` |
| Company Context Retrieved | `clinic_context_hits[]` |
| Agent Action Timeline | `actions[]` |
| Next Best Action | `next_best_action.{recommendation,draft_followup,channel}` |
| Chat Notification Preview | `notification.{platform,sent,preview_markdown}` |
| System Health / Model Status | `system_status[]` |
| Deal Value (money-shot) | `estimated_deal_value.{low,high,basis}` |

## Frontend client (suggested)
`frontend/src/lib/api.ts`:
```ts
const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8090";
export const listLeads = () => fetch(`${BASE}/api/leads`).then(r => r.json());
export const analyze  = (body) => fetch(`${BASE}/api/analyze`, { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body) }).then(r => r.json());
```
TS types live in `frontend/src/types/` — mirror the schema.

## Mock → real swap (no frontend changes)
Both reasoning and alerts now go through **Hermes** (the on-box agent gateway). Hermes' default
model is **local Qwen3-30B** (Ollama on the GB10), so routing through it keeps everything on-box.
See `docs/hermes-integration.md` for the full contract.

| Switch | Env | Effect |
|--------|-----|--------|
| Real inference | `INFERENCE_BACKEND=hermes` + `HERMES_BASE_URL` + `HERMES_API_KEY` | `score`/`extracted` come from Hermes' local Qwen3-30B (`HERMES_INFERENCE_MODEL` blank = default) |
| Real chat | `CHAT_BACKEND=hermes` + `HERMES_WEBHOOK_URL` (+ `HERMES_WEBHOOK_SECRET`) | `notification.sent=true`, alert posts to Discord via the `deliver_only` webhook route (chat-completions fallback if no webhook URL) |

Both degrade to mock on error — the contract never changes.
