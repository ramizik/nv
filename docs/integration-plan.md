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

### `POST /api/simulate`  ← the demo button
No body. Loads the bundled `veneers_wedding` scenario, runs full analysis, fires the
(mock or real) chat alert, returns a complete **`LeadAnalysis`**. **Use this for the demo.**

### `POST /api/analyze`
Body (either `scenario` OR `transcript`):
```json
{
  "scenario": "veneers_wedding",
  "transcript": [{ "speaker": "lead", "text": "..." , "ts": "00:06" }],
  "lead": { "name": "Jessica Moreno", "phone": "+1-512-555-0822" },
  "channel": "voice", "after_hours": true, "notify": true
}
```
Returns a complete `LeadAnalysis`.

### `GET /api/leads` / `GET /api/leads/{lead_id}`
List all / fetch one analyzed lead (in-memory store).

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
const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8080";
export const simulate = () => fetch(`${BASE}/api/simulate`, { method: "POST" }).then(r => r.json());
export const analyze  = (body) => fetch(`${BASE}/api/analyze`, { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body) }).then(r => r.json());
```
TS types live in `frontend/src/types/` — mirror the schema. For dev with no backend,
import `inference/local/sample_outputs/veneers_wedding.analysis.json` as a fixture.

## Mock → real swap (no frontend changes)
| Switch | Env | Effect |
|--------|-----|--------|
| Real inference | `INFERENCE_BACKEND=nemotron` + `NEMOTRON_BASE_URL` | `score`/`extracted` come from GB10 Nemotron |
| Real chat | `CHAT_BACKEND=discord` + `DISCORD_WEBHOOK_URL` | `notification.sent=true`, message posts to Discord |

Both degrade to mock on error — the contract never changes.
