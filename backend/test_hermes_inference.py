"""One-shot test of the REAL inference path: backend -> Hermes -> local Qwen3-30B.

Hermes delegates the reasoning to its local default model (Qwen3-30B on the GB10), so this
exercises the on-box path end to end without us running a model server ourselves.

    cd backend
    INFERENCE_BACKEND=hermes \
    HERMES_BASE_URL=http://127.0.0.1:8642 \
    HERMES_API_KEY=$(grep -E '^API_SERVER_KEY=' ~/.hermes/.env | cut -d= -f2-) \
    ./.venv/bin/python test_hermes_inference.py

Prints whether Hermes/Qwen actually answered ('hermes') or we fell back ('mock_fallback').
To test the DIRECT-to-Ollama fallback instead: INFERENCE_BACKEND=qwen QWEN_MODEL=Qwen3-30B:latest.
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
print(f"Hermes   : {config.HERMES_BASE_URL}/v1  (model override: {config.HERMES_INFERENCE_MODEL or '<Hermes default = Qwen3-30B>'})")
print(f"Bearer   : {'set' if config.HERMES_API_KEY else 'MISSING — gateway will 401'}")

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
    print(f"  curl -s {config.HERMES_BASE_URL}/health")
    print(f"  # chat needs the bearer:  -H 'Authorization: Bearer <API_SERVER_KEY>'")
    print(f"  curl -s {config.HERMES_BASE_URL}/v1/chat/completions -H 'Authorization: Bearer $HERMES_API_KEY' \\")
    print(f"       -H 'Content-Type: application/json' -d '{{\"messages\":[{{\"role\":\"user\",\"content\":\"ping\"}}]}}'")
sys.exit(0 if ok else 1)
