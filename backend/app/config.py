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

# 'mock' | 'hermes'  — mock is the safe default for the demo. 'hermes' = the REAL path:
# we send the transcript to Hermes, which delegates the reasoning to its local default model
# (Qwen3-30B) on the GB10. ('qwen'/'nemotron' = optional DIRECT-to-Ollama fallback, used only
# if Hermes is unavailable — see the QWEN_* block below.)
INFERENCE_BACKEND = os.getenv("INFERENCE_BACKEND", "mock").lower()
# 'mock' | 'hermes' | 'discord'  — how the staff alert is delivered
CHAT_BACKEND = os.getenv("CHAT_BACKEND", "mock").lower()

# Hermes — the teammate's RUNNING service on the GB10 box (binds 127.0.0.1:8642; OpenAI-
# compatible; owns the Discord bot + #front-desk channel). It is our SINGLE integration point:
#   • Reasoning  (INFERENCE_BACKEND=hermes): we POST the transcript to /v1/chat/completions and
#     Hermes delegates to its local default model — CONFIRMED Qwen3-30B served via Ollama on the
#     GB10 (NOT cloud Gemini, as an earlier note wrongly assumed). So reasoning stays ON-BOX and
#     patient conversations never leave the building — and we don't run our own model server.
#   • Alerts     (CHAT_BACKEND=hermes): Hermes relays the finished LeadAnalysis to Discord.
# Every Hermes route needs the gateway bearer HERMES_API_KEY (= API_SERVER_KEY from
# ~/.hermes/.env); the gateway _check_auth() 401s ("invalid_api_key") without it. The model
# behind Hermes is itself keyless. Cross-host: Hermes binds 127.0.0.1, so this only works when
# our backend runs ON the GB10 box (recommended) or via an SSH tunnel. See docs/hermes-integration.md.
HERMES_BASE_URL = os.getenv("HERMES_BASE_URL", "http://127.0.0.1:8642")
# Optional model override for the reasoning call. Blank = let Hermes use its configured default
# (Qwen3-30B), which is what we want. Set e.g. "lifeos-nemotron-120b:latest" only to force the
# heavier deep-reasoning model (slower, monopolizes the box).
HERMES_INFERENCE_MODEL = os.getenv("HERMES_INFERENCE_MODEL", "")
# Read timeout (s) for the reasoning call via Hermes. Qwen3-30B is fast when resident; bump it
# if you point Hermes at the 120B. Connect stays fail-fast (see adapter).
HERMES_TIMEOUT_READ = float(os.getenv("HERMES_TIMEOUT_READ", "60"))

# DIRECT-to-Ollama FALLBACK (INFERENCE_BACKEND=qwen) — bypasses Hermes and calls the local
# Ollama OpenAI endpoint ourselves. Use only if Hermes is down. Qwen3-30B (~18 GB, MoE ~3B
# active) is fast and coexists with the NIM voice stack; lifeos-nemotron-120b:latest (~82 GB)
# is the heavier alternative. Legacy NEMOTRON_* env vars are still honored as a fallback.
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", os.getenv("NEMOTRON_BASE_URL", "http://127.0.0.1:11434/v1"))
QWEN_MODEL = os.getenv("QWEN_MODEL", os.getenv("NEMOTRON_MODEL", "Qwen3-30B:latest"))
QWEN_API_KEY = os.getenv("QWEN_API_KEY", os.getenv("NEMOTRON_API_KEY", "not-needed"))
QWEN_TIMEOUT_READ = float(os.getenv("QWEN_TIMEOUT_READ", os.getenv("NEMOTRON_TIMEOUT_READ", "60")))
# Reasoning-off directive prepended to the system prompt. Qwen3 uses "/no_think"; for the
# Nemotron alias set this to "detailed thinking off". Leftover <think> blocks are stripped either way.
QWEN_THINKING_DIRECTIVE = os.getenv("QWEN_THINKING_DIRECTIVE", "/no_think")
HERMES_WEBHOOK_URL = os.getenv("HERMES_WEBHOOK_URL", "")          # PRIMARY deliver_only route
HERMES_WEBHOOK_SECRET = os.getenv("HERMES_WEBHOOK_SECRET", "")    # HMAC secret; blank = no auth
HERMES_API_KEY = os.getenv("HERMES_API_KEY", "")                  # bearer for the chat fallback
HERMES_DISCORD_CHANNEL = os.getenv("HERMES_DISCORD_CHANNEL", "1509734278206984194")

# Secondary standalone path only (NOT the bot Hermes owns) — raw Discord webhook.
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
