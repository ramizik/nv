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

_STORE: Dict[str, Dict[str, Any]] = {}  # lead store
_COUNTER = {"n": 0}
# Persist to disk so analyzed leads survive a backend restart — this is what the Hermes
# "brightsmile-leads" skill queries (GET /api/leads, /api/leads/summary) to answer staff
# questions like "were there any hot leads after hours?".
_LEADS_PATH = config.REPO_ROOT / "backend" / ".leads_store.json"


def _load_store() -> None:
    try:
        data = json.loads(_LEADS_PATH.read_text(encoding="utf-8"))
        _STORE.update(data.get("leads", {}))
        _COUNTER["n"] = data.get("counter", len(_STORE))
    except Exception:
        pass  # no store yet / unreadable — start empty, never hard-fail


def _save_store() -> None:
    try:
        _LEADS_PATH.write_text(
            json.dumps({"leads": _STORE, "counter": _COUNTER["n"]}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass  # persistence is best-effort; the demo must never break on disk I/O


_load_store()


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
    notification = {"platform": config.CHAT_BACKEND, "sent": False, "preview_markdown": "", "skipped": not notify}
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
    #   'qwen' (direct local Ollama) | 'hermes' (Hermes configured provider) | 'mock_fallback'
    source = analysis.pop("_source", None)
    real_backends = ("hermes", "qwen", "nemotron")
    if config.INFERENCE_BACKEND in real_backends and source in ("hermes", "qwen"):
        path = "Hermes configured provider" if source == "hermes" else "GB10 Qwen (direct)"
        infer_status, infer_detail = "online", f"{path} @ {infer_ms}ms"
    elif config.INFERENCE_BACKEND in real_backends:
        infer_status, infer_detail = "degraded", f"GB10 unreachable — heuristic fallback @ {infer_ms}ms"
    else:
        infer_status, infer_detail = "mock", f"local heuristic @ {infer_ms}ms"
    chat_platform = notification.get("platform", "mock")
    if notification.get("skipped"):
        chat_detail = "notification skipped by request"
    elif chat_platform == "hermes":
        chat_detail = "handed off to Hermes bot" if notification.get("sent") else "Hermes unreachable — preview only"
    elif chat_platform == "discord":
        chat_detail = "live webhook" if notification.get("sent") else "webhook failed — preview only"
    else:
        chat_detail = "preview only"
    analysis["system_status"] = [
        {"component": "ASR (voice in)", "status": "blocked", "detail": config.ASR_RUNTIME_STATUS},
        {"component": "Qwen3-30B (scoring)", "status": infer_status, "detail": infer_detail},
        {"component": "Embeddings (memory)", "status": "available", "detail": f"{config.EMBED_MODEL} @ {config.EMBED_BASE_URL}"},
        {"component": "TTS (voice out)", "status": "available", "detail": f"{config.TTS_VOICE} @ {config.TTS_BASE_URL}"},
        {"component": "Lead Analyzer (orchestration)", "status": "online", "detail": "FastAPI in-process"},
        {"component": "Hermes / Discord (alerts)", "status": chat_platform, "detail": chat_detail},
    ]

    _STORE[analysis["lead_id"]] = analysis
    _save_store()
    return analysis


def schedule_appointment(lead_id: str, when: Optional[str] = None, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Mark a lead's consultation as scheduled and email BOTH clinic owners every time.
    Returns the updated lead, or None if the lead is unknown. Email is fail-safe."""
    from app.services.email_sender import appointment_email  # lazy: never block import

    lead = _STORE.get(lead_id)
    if not lead:
        return None
    appt: Dict[str, Any] = {"scheduled": True, "when": when, "notes": notes}
    email_result = appointment_email(lead, appt)
    appt["email"] = {
        "sent": email_result.get("sent", False),
        "to": email_result.get("to", config.APPOINTMENT_EMAIL_RECIPIENTS),
        "error": email_result.get("error"),
    }
    lead["appointment"] = appt
    # reflect on the actions timeline so the dashboard shows it
    lead.setdefault("actions", []).append({
        "type": "schedule_appointment",
        "label": (f"Scheduled consult — emailed {', '.join(appt['email']['to'])}"
                  if appt["email"]["sent"] else
                  f"Scheduled consult — email FAILED ({appt['email'].get('error', 'unknown')})"),
        "status": "done" if appt["email"]["sent"] else "failed",
    })
    _save_store()
    return lead


def list_appointments() -> List[Dict[str, Any]]:
    """All patients who called AND scheduled a meeting — full details for the UI."""
    out: List[Dict[str, Any]] = []
    for l in _STORE.values():
        appt = l.get("appointment")
        if not appt or not appt.get("scheduled"):
            continue
        person, ext = l.get("lead", {}), l.get("extracted", {})
        score, deal = l.get("score", {}), l.get("estimated_deal_value", {})
        nba = l.get("next_best_action", {})
        out.append({
            "lead_id": l.get("lead_id"),
            "name": person.get("name", "Unknown caller"),
            "phone": person.get("phone", "n/a"),
            "service_interest": ext.get("service_interest"),
            "timeline": ext.get("timeline"),
            "label": score.get("label"),
            "score": score.get("value"),
            "after_hours": l.get("after_hours"),
            "received_at": l.get("received_at") or "n/a",
            "estimated_value": f"${deal.get('low', 0):,}-${deal.get('high', 0):,}",
            "recommended_action": nba.get("recommendation"),
            "appointment": appt,
        })
    return out


def get_lead(lead_id: str) -> Optional[Dict[str, Any]]:
    return _STORE.get(lead_id)


def list_leads() -> List[Dict[str, Any]]:
    return list(_STORE.values())


def summarize_leads() -> Dict[str, Any]:
    """Compact, query-friendly digest of all analyzed leads. This is the endpoint the
    Hermes skill calls so the Discord bot can answer staff questions interactively."""
    leads = list(_STORE.values())
    order = {"hot": 0, "warm": 1, "cold": 2}

    def _row(l: Dict[str, Any]) -> Dict[str, Any]:
        sc, ex = l.get("score", {}), l.get("extracted", {})
        nba, deal = l.get("next_best_action", {}), l.get("estimated_deal_value", {})
        return {
            "lead_id": l.get("lead_id"),
            "name": l.get("lead", {}).get("name", "Unknown caller"),
            "phone": l.get("lead", {}).get("phone", "n/a"),
            "label": sc.get("label"),
            "score": sc.get("value"),
            "after_hours": l.get("after_hours"),
            "received_at": l.get("received_at") or "n/a",
            "service_interest": ex.get("service_interest"),
            "timeline": ex.get("timeline"),
            "estimated_value": f"${deal.get('low', 0):,}-${deal.get('high', 0):,}",
            "recommended_action": nba.get("recommendation"),
        }

    rows = sorted((_row(l) for l in leads), key=lambda r: (order.get(r["label"], 9), -(r["score"] or 0)))
    hot_ah = [r for r in rows if r["label"] == "hot" and r["after_hours"]]
    return {
        "total_leads": len(rows),
        "counts": {k: sum(1 for r in rows if r["label"] == k) for k in ("hot", "warm", "cold")},
        "hot_after_hours_count": len(hot_ah),
        "hot_after_hours": hot_ah,
        "leads": rows,
    }
