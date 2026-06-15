#!/usr/bin/env python3
"""Small terminal chat client for the local Hermes gateway.

Usage:
  cd /home/dell/ram/nv
  scripts/linux/chat_hermes.py

The script reads HERMES_API_KEY from this repo's .env, or API_SERVER_KEY from
~/.hermes/.env. It never prints the key.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw or raw.lstrip().startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def _load_config() -> tuple[str, str]:
    repo_root = Path(__file__).resolve().parents[2]
    repo_env = _env_file(repo_root / ".env")
    hermes_env = _env_file(Path.home() / ".hermes/.env")
    base = (
        os.getenv("HERMES_BASE_URL")
        or repo_env.get("HERMES_BASE_URL")
        or hermes_env.get("API_SERVER_BASE_URL")
        or "http://127.0.0.1:8642"
    ).rstrip("/")
    key = (
        os.getenv("HERMES_API_KEY")
        or repo_env.get("HERMES_API_KEY")
        or hermes_env.get("API_SERVER_KEY")
        or ""
    )
    if not key:
        raise SystemExit("Missing HERMES_API_KEY/API_SERVER_KEY")
    return base, key


def _chat(base: str, key: str, messages: list[dict[str, str]]) -> str:
    payload = {
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 1000,
    }
    req = urllib.request.Request(
        f"{base}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Hermes HTTP {exc.code}: {body[:500]}") from exc
    return data["choices"][0]["message"]["content"]


def main() -> int:
    base, key = _load_config()
    messages = [
        {
            "role": "system",
            "content": "You are Hermes running on the local GB10. Be concise and practical.",
        }
    ]
    print(f"Hermes chat: {base}  (type 'exit' or Ctrl-D to quit)")
    while True:
        try:
            user = input("\nyou> ").strip()
        except EOFError:
            print()
            return 0
        if not user:
            continue
        if user.lower() in {"exit", "quit", ":q"}:
            return 0
        messages.append({"role": "user", "content": user})
        assistant = _chat(base, key, messages)
        messages.append({"role": "assistant", "content": assistant})
        print(f"\nhermes> {assistant}")


if __name__ == "__main__":
    raise SystemExit(main())
