"""Central config. Reads .env once.

The GB10 demo path is:
  - inference: direct local Qwen3-30B via Ollama (:11434/v1)
  - actions/alerts: Hermes gateway (:8642)
  - voice/memory sidecars: NVIDIA NIM services for embeddings and TTS

Hermes remains the agent/tool gateway. It is not assumed to be the primary
inference brain for this app because the current Hermes default model is cloud
Gemini for reliability, while local Qwen is exposed as a separate on-box model.
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

# 'mock' | 'qwen' | 'hermes'
# qwen = primary GB10 path: direct local Qwen3-30B via Ollama.
# hermes = gateway path, useful for actions/agent testing, but currently Hermes
#          defaults to Gemini unless its config is explicitly switched.
INFERENCE_BACKEND = os.getenv("INFERENCE_BACKEND", "mock").lower()
# 'mock' | 'hermes' | 'discord'  — how the staff alert is delivered
CHAT_BACKEND = os.getenv("CHAT_BACKEND", "mock").lower()

# Hermes — running on the GB10 (127.0.0.1:8642). Hermes owns agent/tool execution,
# memory/tasks, and alert delivery. Every protected Hermes route needs the gateway
# bearer HERMES_API_KEY (= API_SERVER_KEY from ~/.hermes/.env). Cross-host access
# requires co-location or an SSH tunnel because Hermes binds loopback.
HERMES_BASE_URL = os.getenv("HERMES_BASE_URL", "http://127.0.0.1:8642")
# Optional model override for Hermes chat/completions calls. Blank = Hermes default.
# On this machine Hermes' stable default is Gemini; use INFERENCE_BACKEND=qwen for
# guaranteed on-box Qwen reasoning.
HERMES_INFERENCE_MODEL = os.getenv("HERMES_INFERENCE_MODEL", "")
HERMES_TIMEOUT_READ = float(os.getenv("HERMES_TIMEOUT_READ", "60"))

# Direct local Qwen (INFERENCE_BACKEND=qwen). This is the primary GB10 model path.
# Qwen3-30B (~18 GiB GGUF, MoE) coexists with the NIM embedding/TTS stack.
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", os.getenv("NEMOTRON_BASE_URL", "http://127.0.0.1:11434/v1"))
QWEN_MODEL = os.getenv("QWEN_MODEL", os.getenv("NEMOTRON_MODEL", "lifeos-qwen3-30b:latest"))
QWEN_API_KEY = os.getenv("QWEN_API_KEY", os.getenv("NEMOTRON_API_KEY", "not-needed"))
QWEN_TIMEOUT_READ = float(os.getenv("QWEN_TIMEOUT_READ", os.getenv("NEMOTRON_TIMEOUT_READ", "240")))
# Reasoning-off directive prepended to the system prompt. Qwen3 uses "/no_think"; for the
# Nemotron alias set this to "detailed thinking off". Leftover <think> blocks are stripped either way.
QWEN_THINKING_DIRECTIVE = os.getenv("QWEN_THINKING_DIRECTIVE", "/no_think")
HERMES_WEBHOOK_URL = os.getenv("HERMES_WEBHOOK_URL", "")          # PRIMARY deliver_only route
HERMES_WEBHOOK_SECRET = os.getenv("HERMES_WEBHOOK_SECRET", "")    # HMAC secret; blank = no auth
HERMES_API_KEY = os.getenv("HERMES_API_KEY", "")                  # bearer for the chat fallback
HERMES_DISCORD_CHANNEL = os.getenv("HERMES_DISCORD_CHANNEL", "1509734278206984194")

# Secondary standalone path only (NOT the bot Hermes owns) — raw Discord webhook.
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# NVIDIA NIM sidecars on the GB10. The app currently consumes Qwen for lead
# analysis, while these endpoints make the wider LifeOS-style voice/memory
# pipeline visible and ready for follow-on integration.
NIM_HEALTH_TIMEOUT = float(os.getenv("NIM_HEALTH_TIMEOUT", "3"))

EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "http://127.0.0.1:8001/v1")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nvidia/llama-nemotron-embed-1b-v2")
EMBED_INPUT_TYPE_QUERY = os.getenv("EMBED_INPUT_TYPE_QUERY", "query")

TTS_BASE_URL = os.getenv("TTS_BASE_URL", "http://127.0.0.1:8003/v1")
TTS_VOICE = os.getenv("TTS_VOICE", "Magpie-Multilingual.EN-US.Mia.Neutral")
TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "en-US")
TTS_SAMPLE_RATE_HZ = int(os.getenv("TTS_SAMPLE_RATE_HZ", "22050"))

ASR_BACKEND = os.getenv("ASR_BACKEND", "nemotron-asr-streaming")
ASR_BASE_URL = os.getenv("ASR_BASE_URL", "http://127.0.0.1:8002/v1")
ASR_RUNTIME_STATUS = os.getenv(
    "ASR_RUNTIME_STATUS",
    "blocked: nemotron-asr-streaming image is present, but runtime model-artifact download needs NGC_API_KEY",
)

PARAKEET_BASE_URL = os.getenv("PARAKEET_BASE_URL", "")
PARAKEET_RUNTIME_STATUS = os.getenv(
    "PARAKEET_RUNTIME_STATUS",
    "blocked: parakeet-0.6b-tdt image on this host is linux/amd64 and cannot run on GB10 linux/arm64",
)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
