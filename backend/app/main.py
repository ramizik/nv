"""FastAPI app — the backend orchestrator + API server.

Entry point: `uvicorn app.main:app --reload --port 8080` (run from backend/).
Routes (the frontend↔backend contract — see docs/integration-plan.md):
  GET  /api/health            -> liveness + which backends are active
  GET  /api/clinic            -> the BrightSmile clinic context (for a context panel)
  POST /api/analyze           -> run full analysis on a live lead transcript
  GET  /api/leads             -> all analyzed leads (persisted records book)
  GET  /api/leads/{lead_id}   -> one lead's full LeadAnalysis
"""
from fastapi import FastAPI, HTTPException
from fastapi import WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.schemas.models import AnalyzeRequest
from app.services import analyze as svc
from app.services.clinic import get_clinic_context
from app.services.lifeos_audio import audio_stream
from app.services.lifeos_routes import router as lifeos_router
from app.services.lifeos_store import init_lifeos
from app.services.system_health import collect_runtime_health

app = FastAPI(title="Local Voice Lead Closer", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(lifeos_router)


@app.on_event("startup")
def startup() -> None:
    init_lifeos()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "inference_backend": config.INFERENCE_BACKEND,
        "chat_backend": config.CHAT_BACKEND,
        "discord_configured": bool(config.DISCORD_WEBHOOK_URL),
        "runtime": collect_runtime_health(),
    }


@app.websocket("/v1/audio/stream")
async def lifeos_audio_stream(websocket: WebSocket):
    await audio_stream(websocket)


@app.get("/api/clinic")
def clinic():
    return get_clinic_context()


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    """Analyze a live lead transcript (e.g. a Discord voice/text interaction) and file it."""
    if not req.transcript:
        raise HTTPException(status_code=400, detail="Provide a `transcript`.")
    return svc.run_analysis(
        transcript=[t.model_dump() for t in req.transcript],
        lead=req.lead.model_dump() if req.lead else None,
        channel=req.channel,
        after_hours=req.after_hours,
        notify=req.notify,
    )


@app.get("/api/leads")
def leads():
    return svc.list_leads()


@app.get("/api/appointments")
def appointments():
    """All patients who called AND scheduled a consult — shown in the dashboard."""
    return svc.list_appointments()


@app.post("/api/leads/{lead_id}/schedule")
def schedule(lead_id: str, body: dict | None = None):
    """Schedule a consult for a lead. Emails BOTH clinic owners every time (fail-safe)."""
    body = body or {}
    result = svc.schedule_appointment(lead_id, when=body.get("when"), notes=body.get("notes"))
    if not result:
        raise HTTPException(status_code=404, detail="Lead not found")
    return result


@app.get("/api/leads/{lead_id}")
def lead(lead_id: str):
    found = svc.get_lead(lead_id)
    if not found:
        raise HTTPException(status_code=404, detail="Lead not found")
    return found
