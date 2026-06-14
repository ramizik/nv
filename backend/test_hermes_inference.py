"""One-shot test of the REAL inference path.

Default GB10 test:
    backend -> local Ollama -> lifeos-qwen3-30b:latest

    cd backend
    INFERENCE_BACKEND=qwen \
    QWEN_BASE_URL=http://127.0.0.1:11434/v1 \
    QWEN_MODEL=lifeos-qwen3-30b:latest \
    ./.venv/bin/python test_hermes_inference.py

Hermes gateway test:
    INFERENCE_BACKEND=hermes \
    HERMES_API_KEY=$(grep -E '^API_SERVER_KEY=' ~/.hermes/.env | cut -d= -f2-) \
    ./.venv/bin/python test_hermes_inference.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import config  # noqa: E402
from app.adapters import get_inference_adapter  # noqa: E402
from app.services.clinic import get_clinic_context  # noqa: E402

payload = json.loads((config.SAMPLE_PAYLOADS_DIR / "veneers_wedding.json").read_text())

print(f"Backend  : {config.INFERENCE_BACKEND}")
print(f"Qwen     : {config.QWEN_BASE_URL}  (model: {config.QWEN_MODEL})")
print(f"Hermes   : {config.HERMES_BASE_URL}/v1  (model override: {config.HERMES_INFERENCE_MODEL or '<Hermes default>'})")
print(f"Bearer   : {'set' if config.HERMES_API_KEY else 'missing'}")

adapter = get_inference_adapter()
result = adapter.analyze(payload["transcript"], get_clinic_context())
source = result.get("_source", "?")
score = result.get("score", {})

print(f"\n_source  : {source}")
print(f"score    : {score.get('label')} {score.get('value')}/100  (conf {score.get('confidence')})")

ok = source in ("hermes", "qwen")
print("\n✅ Real on-box inference path worked." if ok else "⚠️  Fell back to the mock heuristic.")
if not ok:
    print("\nTroubleshoot:")
    print(f"  curl -s {config.QWEN_BASE_URL}/models")
    print(f"  curl -s {config.HERMES_BASE_URL}/health")
sys.exit(0 if ok else 1)
