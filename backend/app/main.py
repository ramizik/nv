"""FastAPI app — the backend orchestrator + API server.

Entry point: `uvicorn app.main:app --reload --port 8080` (run from backend/).
Routes (the frontend↔backend contract — see docs/integration-plan.md):
  GET  /api/health            -> liveness + which backends are active
  GET  /api/clinic            -> the BrightSmile clinic context (for a context panel)
  POST /api/analyze           -> run full analysis on a transcript or named scenario
  POST /api/simulate          -> convenience: analyze the bundled veneers_wedding scenario
  GET  /api/leads             -> all analyzed leads (in-memory)
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
    if req.scenario:
        payload = svc.load_scenario(req.scenario)
        return svc.run_analysis(
            transcript=payload["transcript"],
            lead=payload.get("lead"),
            channel=payload.get("channel", "voice"),
            after_hours=payload.get("after_hours", True),
            lead_id=payload.get("lead_id"),
            received_at=payload.get("received_at"),
            notify=req.notify,
        )
    if not req.transcript:
        raise HTTPException(status_code=400, detail="Provide either `scenario` or `transcript`.")
    return svc.run_analysis(
        transcript=[t.model_dump() for t in req.transcript],
        lead=req.lead.model_dump() if req.lead else None,
        channel=req.channel,
        after_hours=req.after_hours,
        notify=req.notify,
    )


@app.post("/api/simulate")
def simulate():
    """One-click demo path: analyze the bundled veneers+wedding scenario."""
    payload = svc.load_scenario("veneers_wedding")
    return svc.run_analysis(
        transcript=payload["transcript"],
        lead=payload.get("lead"),
        channel=payload.get("channel", "voice"),
        after_hours=payload.get("after_hours", True),
        lead_id=payload.get("lead_id"),
        received_at=payload.get("received_at"),
        notify=True,
    )


@app.get("/api/leads")
def leads():
    return svc.list_leads()


@app.get("/api/leads/{lead_id}")
def lead(lead_id: str):
    found = svc.get_lead(lead_id)
    if not found:
        raise HTTPException(status_code=404, detail="Lead not found")
    return found
