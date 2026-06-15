"""FastAPI routes for the LifeOS hackathon compatibility layer."""
from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app import config
from app.services import lifeos_store as store
from app.services.system_health import collect_runtime_health

router = APIRouter(prefix="/v1")


def require_token(authorization: str | None = Header(default=None)) -> None:
    expected = config.LIFEOS_API_TOKEN or config.HERMES_API_KEY
    if not expected:
        return
    token = (authorization or "").strip()
    if token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1].strip()
    if token != expected:
        raise HTTPException(status_code=401, detail="invalid token")


def _chat_completion_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("messages"), list):
        normalized = dict(payload)
    else:
        message = str(payload.get("message") or payload.get("text") or "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="message or messages is required")
        normalized = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Hermes powering LifeOS. Respond conversationally and use Hermes "
                        "native tools only when the user asks for an action."
                    ),
                },
                {"role": "user", "content": message},
            ],
            "temperature": payload.get("temperature", 0.2),
            "max_tokens": payload.get("max_tokens", 800),
        }
    # Local-model lock: ignore any client-provided model such as "hermes-agent".
    # All LifeOS/Hermes compatibility chat must run on the GB10 Qwen model.
    normalized["model"] = config.QWEN_MODEL
    normalized.setdefault("max_tokens", 800)
    return normalized


async def _call_hermes_chat(payload: dict[str, Any]) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if config.HERMES_API_KEY:
        headers["Authorization"] = f"Bearer {config.HERMES_API_KEY}"
    started = time.time()
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=4.0, read=120.0, write=10.0, pool=5.0)) as client:
        try:
            resp = await client.post(f"{config.HERMES_BASE_URL}/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            store.audit(
                event_type="chat_completed",
                actor="hermes",
                latency_ms=int((time.time() - started) * 1000),
                details={"model": result.get("model")},
            )
            return result
        except httpx.HTTPStatusError as exc:
            store.audit(
                event_type="chat_failed",
                actor="hermes",
                latency_ms=int((time.time() - started) * 1000),
                error=f"{exc.response.status_code}: {exc.response.text[:500]}",
            )
            raise HTTPException(status_code=502, detail="Hermes chat failed") from exc


@router.get("/health")
def lifeos_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "LifeOS compatibility layer",
        "storage": {"sqlite": str(config.LIFEOS_DB_PATH), "audio_dir": str(config.LIFEOS_AUDIO_DIR)},
        "panic": store.panic_enabled(),
        "runtime": collect_runtime_health(),
    }


@router.get("/models")
async def models(_: None = Depends(require_token)) -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {"id": config.QWEN_MODEL, "object": "model", "owned_by": "lifeos-local"},
        ],
    }


@router.get("/timeline")
def timeline(_: None = Depends(require_token), limit: int = 50) -> dict[str, Any]:
    return store.list_timeline(limit=limit)


@router.get("/memory")
def memory(_: None = Depends(require_token), q: str = "", limit: int = 20) -> dict[str, Any]:
    return store.search_memory(q, limit=limit)


@router.post("/memory/utterances")
async def add_utterance(request: Request, _: None = Depends(require_token)) -> dict[str, Any]:
    payload = await request.json()
    text = str(payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    return store.add_utterance(
        text=text,
        speaker=str(payload.get("speaker") or "owner"),
        source=str(payload.get("source") or "manual"),
        stream_id=payload.get("stream_id"),
    )


@router.get("/actions")
def actions(_: None = Depends(require_token), limit: int = 100) -> list[dict[str, Any]]:
    return store.list_actions(limit=limit)


@router.post("/actions/propose")
async def propose_action(request: Request, _: None = Depends(require_token)) -> dict[str, Any]:
    try:
        return store.propose_action(await request.json())
    except RuntimeError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc


@router.post("/actions/{action_id}/approve")
async def approve_action(action_id: str, request: Request, _: None = Depends(require_token)) -> dict[str, Any]:
    payload = await request.json() if request.headers.get("content-length") not in (None, "0") else {}
    approved = store.transition_action(action_id, "APPROVED", {"approved_at": int(time.time() * 1000), **payload})
    if not approved:
        raise HTTPException(status_code=404, detail="action not found")
    # Keep Hermes as the only tool runner: this compatibility layer records approval and asks Hermes
    # to execute/verify. The gateway can route to its native tools according to its config.
    started = time.time()
    result: dict[str, Any]
    try:
        headers = {"Content-Type": "application/json"}
        if config.HERMES_API_KEY:
            headers["Authorization"] = f"Bearer {config.HERMES_API_KEY}"
        prompt = {
            "model": config.QWEN_MODEL,
            "messages": [
                {"role": "system", "content": "You are Hermes. Execute approved LifeOS actions using your native tools when possible. Return concise JSON-like status."},
                {"role": "user", "content": f"Approved LifeOS action {action_id}: {approved}"},
            ],
            "max_tokens": 800,
        }
        with httpx.Client(timeout=httpx.Timeout(connect=4.0, read=120.0, write=10.0, pool=5.0)) as client:
            resp = client.post(f"{config.HERMES_BASE_URL}/v1/chat/completions", headers=headers, json=prompt)
            resp.raise_for_status()
            result = resp.json()
        executed = store.transition_action(action_id, "VERIFIED", {"hermes": result, "latency_ms": int((time.time() - started) * 1000)})
    except Exception as exc:
        executed = store.transition_action(action_id, "FAILED", {"error": str(exc)})
    return executed or approved


@router.post("/actions/{action_id}/decline")
def decline_action(action_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
    action = store.transition_action(action_id, "DECLINED")
    if not action:
        raise HTTPException(status_code=404, detail="action not found")
    return action


@router.post("/panic")
async def panic(request: Request, _: None = Depends(require_token)) -> dict[str, Any]:
    payload = await request.body()
    reason = "owner panic stop"
    if payload:
        try:
            reason = (await request.json()).get("reason") or reason
        except Exception:
            pass
    return store.set_panic(True, reason=reason)


@router.post("/panic/clear")
async def clear_panic(request: Request, _: None = Depends(require_token)) -> dict[str, Any]:
    payload = await request.json() if request.headers.get("content-length") not in (None, "0") else {}
    return store.set_panic(False, reason=payload.get("reason"), actor="owner")


@router.get("/audit")
def audit(_: None = Depends(require_token), limit: int = 100) -> list[dict[str, Any]]:
    return store.list_audit(limit=limit)


@router.post("/chat/completions")
async def chat_completions(request: Request, _: None = Depends(require_token)) -> dict[str, Any]:
    return await _call_hermes_chat(_chat_completion_payload(await request.json()))


@router.post("/chat")
async def chat(request: Request, _: None = Depends(require_token)) -> dict[str, Any]:
    return await _call_hermes_chat(_chat_completion_payload(await request.json()))
