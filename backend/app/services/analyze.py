"""Orchestration — the Lead Analyzer service. Ties voice transcript -> inference ->
context -> chat -> assembled LeadAnalysis. This is what the /api/analyze endpoint calls.

NOTE: this is OUR service, NOT Hermes. Hermes is the teammate's separate running service
on the GB10 (Discord bot + memory + tasks); we reason locally here and HAND OFF the
finished LeadAnalysis to Hermes for the staff alert (CHAT_BACKEND=hermes).

Flow:
  1. resolve transcript (from a known scenario fixture or the raw request)
  2. inference adapter -> extracted/score/nba/etc
  3. chat adapter -> notification (fire the staff alert)
  4. assemble actions timeline + system_status + final canonical LeadAnalysis dict
"""
import json
import time
from typing import Any, Dict, List, Optional

from app import config
from app.adapters import get_chat_adapter, get_inference_adapter
from app.services.clinic import get_clinic_context

_STORE: Dict[str, Dict[str, Any]] = {}  # in-memory lead store (demo only)
_COUNTER = {"n": 0}


def load_scenario(name: str) -> Dict[str, Any]:
    path = config.SAMPLE_PAYLOADS_DIR / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _next_lead_id() -> str:
    _COUNTER["n"] += 1
    return f"lead_{_COUNTER['n']:03d}"


def run_analysis(
    transcript: List[Dict[str, Any]],
    lead: Optional[Dict[str, Any]] = None,
    channel: str = "voice",
    after_hours: bool = True,
    lead_id: Optional[str] = None,
    received_at: Optional[str] = None,
    notify: bool = True,
) -> Dict[str, Any]:
    ctx = get_clinic_context()
    inference = get_inference_adapter()

    t0 = time.time()
    ai = inference.analyze(transcript, ctx)
    infer_ms = int((time.time() - t0) * 1000)

    analysis: Dict[str, Any] = {
        "lead_id": lead_id or _next_lead_id(),
        "received_at": received_at or "",
        "channel": channel,
        "after_hours": after_hours,
        "lead": lead or {},
        "transcript": transcript,
        **ai,  # summary, extracted, score, estimated_deal_value, clinic_context_hits, next_best_action
    }

    # actions timeline
    n_slots = len([v for v in analysis.get("extracted", {}).values() if v not in (None, [], "", "unknown")])
    label = analysis.get("score", {}).get("label", "?")
    actions: List[Dict[str, Any]] = [
        {"type": "extract", "label": f"Extracted {n_slots} qualification slots from transcript", "status": "done"},
        {"type": "context_check", "label": "Consulted BrightSmile policy: services, financing, premium-lead rules", "status": "done"},
        {"type": "score", "label": f"Scored lead {label.upper()} ({analysis.get('score', {}).get('value')}/100)", "status": "done"},
    ]

    # chat notification
    notification = {"platform": config.CHAT_BACKEND, "sent": False, "preview_markdown": ""}
    if notify:
        notification = get_chat_adapter().send(analysis)
        actions.append({
            "type": "notify",
            "label": f"Posted {label}-lead alert to {notification.get('platform')} #front-desk",
            "status": "done" if notification.get("sent") else "failed",
        })
    analysis["notification"] = notification

    actions.append({"type": "draft_followup", "label": "Drafted concierge follow-up message", "status": "done"})
    if label == "hot":
        actions.append({"type": "create_task", "label": "Created callback reminder: within 30 minutes", "status": "pending"})
    analysis["actions"] = actions

    # system status — _source is set by the inference adapter:
    #   'hermes' (Hermes delegated to local Qwen) | 'qwen' (direct Ollama) | 'mock_fallback'
    source = analysis.pop("_source", None)
    real_backends = ("hermes", "qwen", "nemotron")
    if config.INFERENCE_BACKEND in real_backends and source in ("hermes", "qwen"):
        path = "GB10 Qwen via Hermes" if source == "hermes" else "GB10 Qwen (direct)"
        infer_status, infer_detail = "online", f"{path} @ {infer_ms}ms"
    elif config.INFERENCE_BACKEND in real_backends:
        infer_status, infer_detail = "degraded", f"GB10 unreachable — heuristic fallback @ {infer_ms}ms"
    else:
        infer_status, infer_detail = "mock", f"local heuristic @ {infer_ms}ms"
    chat_platform = notification.get("platform", "mock")
    if chat_platform == "hermes":
        chat_detail = "handed off to Hermes bot" if notification.get("sent") else "Hermes unreachable — preview only"
    elif chat_platform == "discord":
        chat_detail = "live webhook" if notification.get("sent") else "webhook failed — preview only"
    else:
        chat_detail = "preview only"
    analysis["system_status"] = [
        {"component": "PersonaPlex (voice)", "status": "mock", "detail": "transcript fixture"},
        {"component": "Qwen via Hermes (scoring)", "status": infer_status, "detail": infer_detail},
        {"component": "Lead Analyzer (orchestration)", "status": "online", "detail": "FastAPI in-process"},
        {"component": "Hermes / Discord (alerts)", "status": chat_platform, "detail": chat_detail},
    ]

    _STORE[analysis["lead_id"]] = analysis
    return analysis


def get_lead(lead_id: str) -> Optional[Dict[str, Any]]:
    return _STORE.get(lead_id)


def list_leads() -> List[Dict[str, Any]]:
    return list(_STORE.values())
