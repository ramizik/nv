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
# 'mock' | 'discord'
CHAT_BACKEND = os.getenv("CHAT_BACKEND", "mock").lower()

# Remote GB10 box — only used when INFERENCE_BACKEND=nemotron
NEMOTRON_BASE_URL = os.getenv("NEMOTRON_BASE_URL", "http://localhost:8000/v1")
NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nvidia/nemotron")
NEMOTRON_API_KEY = os.getenv("NEMOTRON_API_KEY", "not-needed")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
