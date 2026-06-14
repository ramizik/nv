"""Central config. Reads .env once. All toggles for mock-vs-real live here.

Connects to: adapters (which backend to instantiate), main (CORS, paths).
The two demo-safety switches are INFERENCE_BACKEND and CHAT_BACKEND — both
default to 'mock' so the demo runs 100% on the Windows box with zero externals.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# repo_root/backend/app/config.py -> repo_root
REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

# shared/ is the cross-machine source of truth for context + fixtures
SHARED_DIR = REPO_ROOT / "shared"
CLINIC_CONTEXT_PATH = SHARED_DIR / "clinic_context" / "brightsmile.json"
SAMPLE_PAYLOADS_DIR = SHARED_DIR / "sample_payloads"
GOLDEN_OUTPUTS_DIR = REPO_ROOT / "inference" / "local" / "sample_outputs"

# 'mock' | 'nemotron'  — mock is the safe default for the demo
INFERENCE_BACKEND = os.getenv("INFERENCE_BACKEND", "mock").lower()
# 'mock' | 'hermes' | 'discord'  — how the staff alert is delivered
CHAT_BACKEND = os.getenv("CHAT_BACKEND", "mock").lower()

# Local GB10 model server — used when INFERENCE_BACKEND=nemotron. CONFIRMED on the box:
# a Nemotron-120B is served via **Ollama** (OpenAI-compatible) at :11434/v1, no API key.
# We call this DIRECTLY, NOT through Hermes: Hermes' default model is cloud Gemini, and
# routing reasoning through it would send patient conversations off-box and break the
# "nothing leaves the building" claim. NOTE: ~120 GB unified memory ⇒ only ONE local
# model resident at a time — keep exactly this model loaded for the demo (no voice/embed).
NEMOTRON_BASE_URL = os.getenv("NEMOTRON_BASE_URL", "http://127.0.0.1:11434/v1")
NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "lifeos-nemotron-120b:latest")
NEMOTRON_API_KEY = os.getenv("NEMOTRON_API_KEY", "not-needed")
# Read timeout (s) for a model call. The 120B can be slow on a cold first token, so allow
# room — but PRE-WARM before the demo so it's resident. Connect stays fail-fast (see adapter).
NEMOTRON_TIMEOUT_READ = float(os.getenv("NEMOTRON_TIMEOUT_READ", "90"))

# Hermes — the teammate's RUNNING service on the GB10 box. OpenAI-compatible agent
# gateway at :8642 that OWNS Discord (bot), memory, and tasks. We hand a finished
# LeadAnalysis off to it for the staff alert. Hermes runs LOCALLY and needs NO API key —
# HERMES_API_KEY is optional (only sent as a bearer if you set it). Cross-host note: Hermes
# binds 127.0.0.1, so this only works if our backend runs ON the GB10 box (recommended) or
# through an SSH tunnel. See docs/hermes-integration.md.
HERMES_BASE_URL = os.getenv("HERMES_BASE_URL", "http://127.0.0.1:8642")
HERMES_API_KEY = os.getenv("HERMES_API_KEY", "")  # optional — Hermes is keyless on localhost
HERMES_DISCORD_CHANNEL = os.getenv("HERMES_DISCORD_CHANNEL", "1509734278206984194")

# Secondary standalone path only (NOT the bot Hermes owns) — raw Discord webhook.
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
