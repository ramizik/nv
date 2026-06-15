"""LifeOS WebSocket audio protocol."""
from __future__ import annotations

import json
import struct
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app import config
from app.services import lifeos_store as store

FRAME_HEADER = struct.Struct(">BBQQQQ")
FRAME_HEADER_BYTES = FRAME_HEADER.size
PAYLOAD_BYTES = 640
PROTOCOL_VERSION = 1


def _token_from_header(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip()
    if value.lower().startswith("bearer "):
        return value.split(" ", 1)[1].strip()
    return value


def _authorized(websocket: WebSocket) -> bool:
    expected = config.LIFEOS_API_TOKEN or config.HERMES_API_KEY
    if not expected:
        return True
    got = _token_from_header(websocket.headers.get("authorization")) or websocket.query_params.get("token", "")
    return got == expected


async def audio_stream(websocket: WebSocket) -> None:
    if not _authorized(websocket):
        await websocket.close(code=1008, reason="invalid token")
        return
    await websocket.accept()
    stream_id: str | None = None
    last_ack = -1
    frames_since_ack = 0
    try:
        hello = json.loads(await websocket.receive_text())
        if hello.get("type") != "hello":
            await websocket.send_json({"type": "error", "message": "expected hello"})
            await websocket.close(code=1002)
            return
        if int(hello.get("protocol", 0)) != PROTOCOL_VERSION:
            await websocket.send_json({"type": "error", "message": "unsupported protocol"})
            await websocket.close(code=1002)
            return
        stream_id = str(hello["stream_id"])
        device_id = hello.get("device_id")
        last_ack = store.upsert_stream(stream_id, device_id)
        resume_from = max(last_ack, int(hello.get("resume_from", -1)))
        await websocket.send_json({"type": "hello_ack", "stream_id": stream_id, "resume_from": resume_from})
        store.audit("audio_stream_open", device_id=device_id, session_id=stream_id, details={"resume_from": resume_from})

        while True:
            msg: dict[str, Any] = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            data = msg.get("bytes")
            if data is None:
                text = msg.get("text")
                if text:
                    payload = json.loads(text)
                    if payload.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                continue
            if len(data) != FRAME_HEADER_BYTES + PAYLOAD_BYTES:
                await websocket.send_json({"type": "error", "message": f"invalid frame length {len(data)}"})
                continue
            version, flags, msb, lsb, sequence, captured_at = FRAME_HEADER.unpack(data[:FRAME_HEADER_BYTES])
            if version != PROTOCOL_VERSION:
                await websocket.send_json({"type": "error", "message": "invalid frame protocol"})
                continue
            frame_stream_id = f"{msb:016x}{lsb:016x}"
            # Android sends the UUID bits in the frame; the hello stream_id is authoritative.
            inserted = store.store_audio_frame(stream_id, int(sequence), int(captured_at), data[FRAME_HEADER_BYTES:])
            frames_since_ack += 1 if inserted else 0
            if frames_since_ack >= config.LIFEOS_ACK_EVERY_FRAMES:
                last_ack = store.highest_contiguous_sequence(stream_id, last_ack)
                await websocket.send_json({"type": "ack", "sequence": last_ack, "stream_bits": frame_stream_id})
                frames_since_ack = 0
    except WebSocketDisconnect:
        pass
    finally:
        if stream_id:
            last_ack = store.highest_contiguous_sequence(stream_id, last_ack)
            try:
                await websocket.send_json({"type": "ack", "sequence": last_ack})
            except Exception:
                pass
            store.audit("audio_stream_closed", session_id=stream_id, details={"last_ack": last_ack})
