"""SQLite-backed LifeOS state, memory, actions, and audit log."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app import config


def _now_ms() -> int:
    return int(time.time() * 1000)


def _json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def normalized_hash(data: Any) -> str:
    return hashlib.sha256(_json(data).encode("utf-8")).hexdigest()


def init_lifeos() -> None:
    config.LIFEOS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.LIFEOS_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS streams (
              stream_id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL DEFAULT 'owner',
              device_id TEXT,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL,
              last_ack_sequence INTEGER NOT NULL DEFAULT -1,
              status TEXT NOT NULL DEFAULT 'open'
            );

            CREATE TABLE IF NOT EXISTS audio_frames (
              stream_id TEXT NOT NULL,
              sequence INTEGER NOT NULL,
              captured_at INTEGER NOT NULL,
              received_at INTEGER NOT NULL,
              byte_count INTEGER NOT NULL,
              audio_path TEXT NOT NULL,
              payload_sha256 TEXT NOT NULL,
              PRIMARY KEY(stream_id, sequence)
            );

            CREATE TABLE IF NOT EXISTS utterances (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              session_id TEXT,
              stream_id TEXT,
              speaker TEXT NOT NULL DEFAULT 'owner',
              text TEXT NOT NULL,
              source TEXT NOT NULL DEFAULT 'manual',
              confidence REAL,
              started_at INTEGER,
              ended_at INTEGER,
              created_at INTEGER NOT NULL,
              pii_classification TEXT DEFAULT 'unknown'
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS utterances_fts
              USING fts5(id UNINDEXED, text, content='');

            CREATE TABLE IF NOT EXISTS episodes (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              title TEXT,
              summary TEXT,
              started_at INTEGER,
              ended_at INTEGER,
              salience REAL DEFAULT 0.5,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS facts (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              subject TEXT,
              predicate TEXT,
              object TEXT,
              confidence REAL DEFAULT 0.5,
              normalized_hash TEXT NOT NULL,
              created_at INTEGER NOT NULL,
              superseded_by TEXT
            );

            CREATE TABLE IF NOT EXISTS commitments (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              beneficiary TEXT,
              description TEXT NOT NULL,
              due_at INTEGER,
              status TEXT NOT NULL DEFAULT 'open',
              confidence REAL DEFAULT 0.5,
              source TEXT,
              history_json TEXT NOT NULL DEFAULT '[]',
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS entities (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              name TEXT NOT NULL,
              kind TEXT,
              normalized_hash TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evidence (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              memory_id TEXT NOT NULL,
              memory_table TEXT NOT NULL,
              source_type TEXT NOT NULL,
              source_ref TEXT,
              excerpt TEXT,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS embeddings (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              target_table TEXT NOT NULL,
              target_id TEXT NOT NULL,
              model TEXT NOT NULL,
              input_hash TEXT NOT NULL,
              vector_json TEXT,
              created_at INTEGER NOT NULL,
              UNIQUE(target_table, target_id, model)
            );

            CREATE TABLE IF NOT EXISTS memory_relations (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              from_table TEXT NOT NULL,
              from_id TEXT NOT NULL,
              relation TEXT NOT NULL,
              to_table TEXT NOT NULL,
              to_id TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS actions (
              id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              state TEXT NOT NULL,
              category TEXT NOT NULL,
              tool TEXT NOT NULL,
              arguments_json TEXT NOT NULL,
              preview TEXT,
              expected_effects TEXT,
              verifier TEXT,
              idempotency_key TEXT NOT NULL,
              fingerprint TEXT NOT NULL UNIQUE,
              expiry_at INTEGER,
              result_json TEXT,
              verification_json TEXT,
              created_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_events (
              id TEXT PRIMARY KEY,
              timestamp INTEGER NOT NULL,
              owner_id TEXT,
              device_id TEXT,
              session_id TEXT,
              task_id TEXT,
              action_id TEXT,
              actor TEXT NOT NULL,
              event_type TEXT NOT NULL,
              state_from TEXT,
              state_to TEXT,
              arguments_hash TEXT,
              result_hash TEXT,
              latency_ms INTEGER,
              error TEXT,
              details_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS panic_state (
              id INTEGER PRIMARY KEY CHECK (id = 1),
              enabled INTEGER NOT NULL,
              reason TEXT,
              updated_at INTEGER NOT NULL
            );
            INSERT OR IGNORE INTO panic_state(id, enabled, reason, updated_at)
              VALUES(1, 0, NULL, strftime('%s','now') * 1000);
            """
        )


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    config.LIFEOS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(config.LIFEOS_DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        yield db
        db.commit()
    finally:
        db.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    out = dict(row)
    for key in ("arguments_json", "result_json", "verification_json", "details_json", "history_json"):
        if key in out and isinstance(out[key], str):
            try:
                out[key.replace("_json", "")] = json.loads(out.pop(key))
            except json.JSONDecodeError:
                pass
    return out


def audit(
    event_type: str,
    *,
    actor: str = "lifeos",
    owner_id: str | None = "owner",
    device_id: str | None = None,
    session_id: str | None = None,
    task_id: str | None = None,
    action_id: str | None = None,
    state_from: str | None = None,
    state_to: str | None = None,
    arguments: Any | None = None,
    result: Any | None = None,
    latency_ms: int | None = None,
    error: str | None = None,
    details: dict[str, Any] | None = None,
) -> str:
    event_id = str(uuid.uuid4())
    with connect() as db:
        db.execute(
            """
            INSERT INTO audit_events(
              id, timestamp, owner_id, device_id, session_id, task_id, action_id, actor,
              event_type, state_from, state_to, arguments_hash, result_hash, latency_ms,
              error, details_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                event_id,
                _now_ms(),
                owner_id,
                device_id,
                session_id,
                task_id,
                action_id,
                actor,
                event_type,
                state_from,
                state_to,
                normalized_hash(arguments) if arguments is not None else None,
                normalized_hash(result) if result is not None else None,
                latency_ms,
                error,
                _json(details or {}),
            ),
        )
    return event_id


def panic_enabled() -> bool:
    with connect() as db:
        row = db.execute("SELECT enabled FROM panic_state WHERE id=1").fetchone()
    return bool(row and row["enabled"])


def set_panic(enabled: bool, reason: str | None = None, actor: str = "owner") -> dict[str, Any]:
    now = _now_ms()
    with connect() as db:
        db.execute(
            "UPDATE panic_state SET enabled=?, reason=?, updated_at=? WHERE id=1",
            (1 if enabled else 0, reason, now),
        )
        if enabled:
            db.execute(
                "UPDATE actions SET state='CANCELLED', updated_at=? WHERE state IN ('PROPOSED','WAITING_APPROVAL','APPROVED')",
                (now,),
            )
    audit("panic_enabled" if enabled else "panic_cleared", actor=actor, details={"reason": reason})
    return {"panic": enabled, "reason": reason, "updated_at": now}


def stream_audio_path(stream_id: str) -> Path:
    safe = stream_id.replace("/", "_")
    return config.LIFEOS_AUDIO_DIR / f"{safe}.pcm"


def upsert_stream(stream_id: str, device_id: str | None, owner_id: str = "owner") -> int:
    now = _now_ms()
    with connect() as db:
        db.execute(
            """
            INSERT INTO streams(stream_id, owner_id, device_id, created_at, updated_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(stream_id) DO UPDATE SET device_id=excluded.device_id, updated_at=excluded.updated_at, status='open'
            """,
            (stream_id, owner_id, device_id, now, now),
        )
        row = db.execute("SELECT last_ack_sequence FROM streams WHERE stream_id=?", (stream_id,)).fetchone()
    return int(row["last_ack_sequence"]) if row else -1


def store_audio_frame(stream_id: str, sequence: int, captured_at: int, payload: bytes) -> bool:
    config.LIFEOS_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    path = stream_audio_path(stream_id)
    digest = hashlib.sha256(payload).hexdigest()
    now = _now_ms()
    with connect() as db:
        try:
            db.execute(
                """
                INSERT INTO audio_frames(stream_id, sequence, captured_at, received_at, byte_count, audio_path, payload_sha256)
                VALUES(?,?,?,?,?,?,?)
                """,
                (stream_id, sequence, captured_at, now, len(payload), str(path), digest),
            )
            inserted = True
        except sqlite3.IntegrityError:
            inserted = False
        if inserted:
            with path.open("ab") as f:
                f.write(payload)
    return inserted


def update_stream_ack(stream_id: str, ack: int) -> None:
    with connect() as db:
        db.execute(
            "UPDATE streams SET last_ack_sequence=?, updated_at=? WHERE stream_id=? AND last_ack_sequence < ?",
            (ack, _now_ms(), stream_id, ack),
        )


def highest_contiguous_sequence(stream_id: str, start_after: int) -> int:
    expected = start_after + 1
    ack = start_after
    with connect() as db:
        rows = db.execute(
            "SELECT sequence FROM audio_frames WHERE stream_id=? AND sequence>=? ORDER BY sequence",
            (stream_id, expected),
        ).fetchall()
    for row in rows:
        seq = int(row["sequence"])
        if seq != expected:
            break
        ack = seq
        expected += 1
    update_stream_ack(stream_id, ack)
    return ack


def list_timeline(limit: int = 50) -> dict[str, Any]:
    with connect() as db:
        streams = [row_to_dict(r) for r in db.execute("SELECT * FROM streams ORDER BY updated_at DESC LIMIT ?", (limit,))]
        actions = [row_to_dict(r) for r in db.execute("SELECT * FROM actions ORDER BY updated_at DESC LIMIT ?", (limit,))]
        utterances = [row_to_dict(r) for r in db.execute("SELECT * FROM utterances ORDER BY created_at DESC LIMIT ?", (limit,))]
    return {"streams": streams, "actions": actions, "utterances": utterances}


def search_memory(query: str, limit: int = 20) -> dict[str, Any]:
    with connect() as db:
        if query.strip():
            try:
                utterances = [
                    dict(r)
                    for r in db.execute(
                        """
                        SELECT u.* FROM utterances_fts f
                        JOIN utterances u ON u.id=f.id
                        WHERE utterances_fts MATCH ?
                        ORDER BY rank
                        LIMIT ?
                        """,
                        (query, limit),
                    )
                ]
            except sqlite3.DatabaseError:
                utterances = []
            if not utterances:
                utterances = [
                    row_to_dict(r) or {}
                    for r in db.execute(
                        "SELECT * FROM utterances WHERE text LIKE ? ORDER BY created_at DESC LIMIT ?",
                        (f"%{query}%", limit),
                    )
                ]
        else:
            utterances = [row_to_dict(r) for r in db.execute("SELECT * FROM utterances ORDER BY created_at DESC LIMIT ?", (limit,))]
        facts = [row_to_dict(r) for r in db.execute("SELECT * FROM facts ORDER BY created_at DESC LIMIT ?", (limit,))]
        commitments = [row_to_dict(r) for r in db.execute("SELECT * FROM commitments ORDER BY updated_at DESC LIMIT ?", (limit,))]
    return {"utterances": utterances, "facts": facts, "commitments": commitments}


def add_utterance(text: str, speaker: str = "owner", source: str = "manual", stream_id: str | None = None) -> dict[str, Any]:
    item = {
        "id": str(uuid.uuid4()),
        "owner_id": "owner",
        "session_id": None,
        "stream_id": stream_id,
        "speaker": speaker,
        "text": text,
        "source": source,
        "confidence": None,
        "started_at": None,
        "ended_at": None,
        "created_at": _now_ms(),
        "pii_classification": "unknown",
    }
    with connect() as db:
        db.execute(
            """
            INSERT INTO utterances(id, owner_id, session_id, stream_id, speaker, text, source, confidence, started_at, ended_at, created_at, pii_classification)
            VALUES(:id,:owner_id,:session_id,:stream_id,:speaker,:text,:source,:confidence,:started_at,:ended_at,:created_at,:pii_classification)
            """,
            item,
        )
        db.execute("INSERT INTO utterances_fts(id, text) VALUES(?, ?)", (item["id"], text))
    audit("utterance_created", details={"id": item["id"], "source": source})
    return item


def propose_action(payload: dict[str, Any]) -> dict[str, Any]:
    if panic_enabled():
        raise RuntimeError("panic stop is active")
    category = str(payload.get("category") or "terminal")
    tool = str(payload.get("tool") or "hermes")
    arguments = payload.get("arguments") or {}
    idempotency_key = str(payload.get("idempotency_key") or normalized_hash({"category": category, "tool": tool, "arguments": arguments}))
    fingerprint = normalized_hash({"category": category, "tool": tool, "idempotency_key": idempotency_key, "arguments": arguments})
    now = _now_ms()
    expiry_seconds = (
        config.LIFEOS_ACTION_EXPIRY_TERMINAL_SECONDS
        if category in {"terminal", "email"}
        else config.LIFEOS_ACTION_EXPIRY_STANDARD_SECONDS
    )
    item = {
        "id": str(uuid.uuid4()),
        "owner_id": "owner",
        "state": "WAITING_APPROVAL",
        "category": category,
        "tool": tool,
        "arguments_json": _json(arguments),
        "preview": payload.get("preview") or _json(arguments),
        "expected_effects": payload.get("expected_effects"),
        "verifier": payload.get("verifier") or category,
        "idempotency_key": idempotency_key,
        "fingerprint": fingerprint,
        "expiry_at": now + expiry_seconds * 1000,
        "result_json": None,
        "verification_json": None,
        "created_at": now,
        "updated_at": now,
    }
    with connect() as db:
        existing = db.execute("SELECT * FROM actions WHERE fingerprint=?", (fingerprint,)).fetchone()
        if existing:
            return row_to_dict(existing) or {}
        db.execute(
            """
            INSERT INTO actions(id, owner_id, state, category, tool, arguments_json, preview, expected_effects, verifier,
              idempotency_key, fingerprint, expiry_at, result_json, verification_json, created_at, updated_at)
            VALUES(:id,:owner_id,:state,:category,:tool,:arguments_json,:preview,:expected_effects,:verifier,
              :idempotency_key,:fingerprint,:expiry_at,:result_json,:verification_json,:created_at,:updated_at)
            """,
            item,
        )
    audit("action_waiting_approval", action_id=item["id"], state_to="WAITING_APPROVAL", arguments=arguments)
    public = dict(item)
    public.pop("arguments_json", None)
    public["arguments"] = arguments
    return public


def transition_action(action_id: str, state: str, result: dict[str, Any] | None = None) -> dict[str, Any] | None:
    now = _now_ms()
    with connect() as db:
        row = db.execute("SELECT * FROM actions WHERE id=?", (action_id,)).fetchone()
        if not row:
            return None
        old = str(row["state"])
        if old in {"DECLINED", "EXPIRED", "CANCELLED", "FAILED", "VERIFICATION_FAILED", "VERIFIED"}:
            return row_to_dict(row)
        db.execute(
            "UPDATE actions SET state=?, result_json=COALESCE(?, result_json), updated_at=? WHERE id=?",
            (state, _json(result) if result is not None else None, now, action_id),
        )
        updated = db.execute("SELECT * FROM actions WHERE id=?", (action_id,)).fetchone()
    audit("action_transition", action_id=action_id, state_from=old, state_to=state, result=result)
    return row_to_dict(updated)


def expire_actions() -> int:
    now = _now_ms()
    with connect() as db:
        rows = db.execute("SELECT id FROM actions WHERE state='WAITING_APPROVAL' AND expiry_at IS NOT NULL AND expiry_at < ?", (now,)).fetchall()
        db.execute("UPDATE actions SET state='EXPIRED', updated_at=? WHERE state='WAITING_APPROVAL' AND expiry_at IS NOT NULL AND expiry_at < ?", (now, now))
    for row in rows:
        audit("action_expired", action_id=row["id"], state_to="EXPIRED")
    return len(rows)


def list_actions(limit: int = 100) -> list[dict[str, Any]]:
    expire_actions()
    with connect() as db:
        return [row_to_dict(r) or {} for r in db.execute("SELECT * FROM actions ORDER BY updated_at DESC LIMIT ?", (limit,))]


def list_audit(limit: int = 100) -> list[dict[str, Any]]:
    with connect() as db:
        return [row_to_dict(r) or {} for r in db.execute("SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT ?", (limit,))]
