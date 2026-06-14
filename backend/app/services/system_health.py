"""Live runtime health for the GB10 model/Hermes/NIM stack."""
from __future__ import annotations

from typing import Any, Dict, Tuple

import httpx

from app import config


def _client() -> httpx.Client:
    timeout = httpx.Timeout(
        connect=1.5,
        read=config.NIM_HEALTH_TIMEOUT,
        write=2.0,
        pool=1.0,
    )
    return httpx.Client(timeout=timeout)


def _status(ok: bool, detail: str, **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"status": "online" if ok else "degraded", "detail": detail}
    payload.update(extra)
    return payload


def _get_json(client: httpx.Client, url: str, headers: Dict[str, str] | None = None) -> Tuple[bool, Any]:
    try:
        resp = client.get(url, headers=headers, timeout=client.timeout)
        resp.raise_for_status()
        return True, resp.json()
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _model_ids(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    ids: list[str] = []
    for item in data:
        if isinstance(item, dict) and item.get("id"):
            ids.append(str(item["id"]))
    return ids


def collect_runtime_health() -> Dict[str, Any]:
    """Return non-secret health for all configured local pipeline pieces."""
    with _client() as client:
        hermes_headers = {}
        if config.HERMES_API_KEY:
            hermes_headers["Authorization"] = f"Bearer {config.HERMES_API_KEY}"

        hermes_ok, hermes_payload = _get_json(client, f"{config.HERMES_BASE_URL}/health")
        qwen_ok, qwen_payload = _get_json(client, f"{config.QWEN_BASE_URL.rstrip('/')}/models")
        embed_ready_ok, embed_ready = _get_json(client, f"{config.EMBED_BASE_URL.rstrip('/')}/health/ready")
        embed_models_ok, embed_models = _get_json(client, f"{config.EMBED_BASE_URL.rstrip('/')}/models")
        tts_ok, tts_payload = _get_json(client, f"{config.TTS_BASE_URL.rstrip('/')}/health/ready")
        asr_ok, asr_payload = _get_json(client, f"{config.ASR_BASE_URL.rstrip('/')}/health/ready")

    qwen_models = _model_ids(qwen_payload)
    embed_model_ids = _model_ids(embed_models)

    qwen_detail = f"{config.QWEN_MODEL} listed at {config.QWEN_BASE_URL}"
    if qwen_ok and qwen_models and config.QWEN_MODEL not in qwen_models:
        qwen_detail = f"{config.QWEN_MODEL} not listed; available={qwen_models[:6]}"
        qwen_ok = False
    elif not qwen_ok:
        qwen_detail = str(qwen_payload)

    embed_ok = embed_ready_ok and (not embed_models_ok or config.EMBED_MODEL in embed_model_ids)
    embed_detail = f"{config.EMBED_MODEL} ready at {config.EMBED_BASE_URL}"
    if not embed_ok:
        embed_detail = str(embed_ready if not embed_ready_ok else embed_models)

    return {
        "hermes": _status(
            hermes_ok,
            f"{config.HERMES_BASE_URL} health OK" if hermes_ok else str(hermes_payload),
            auth_configured=bool(config.HERMES_API_KEY),
        ),
        "qwen": _status(qwen_ok, qwen_detail, model=config.QWEN_MODEL, base_url=config.QWEN_BASE_URL),
        "embedding": _status(
            embed_ok,
            embed_detail,
            model=config.EMBED_MODEL,
            base_url=config.EMBED_BASE_URL,
            input_type=config.EMBED_INPUT_TYPE_QUERY,
        ),
        "tts": _status(
            tts_ok,
            f"{config.TTS_VOICE} ready at {config.TTS_BASE_URL}" if tts_ok else str(tts_payload),
            voice=config.TTS_VOICE,
            language=config.TTS_LANGUAGE,
            base_url=config.TTS_BASE_URL,
        ),
        "asr": {
            "status": "online" if asr_ok else "blocked",
            "detail": "ASR NIM ready" if asr_ok else config.ASR_RUNTIME_STATUS,
            "base_url": config.ASR_BASE_URL,
            "probe": None if asr_ok else str(asr_payload),
        },
        "parakeet": {
            "status": "blocked",
            "detail": config.PARAKEET_RUNTIME_STATUS,
            "base_url": config.PARAKEET_BASE_URL,
        },
    }
