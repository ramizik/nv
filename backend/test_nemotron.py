#!/usr/bin/env python3
"""One-shot test of the REAL GB10 Nemotron path. Run after setting the endpoint env vars.

    cd backend
    INFERENCE_BACKEND=nemotron \
    NEMOTRON_BASE_URL=http://<gb10-host>:8000/v1 \
    NEMOTRON_MODEL=<served-model-id> \
    ./.venv/bin/python test_nemotron.py

Prints whether the model actually answered ('nemotron') or we fell back ('mock_fallback'),
plus the score it produced. Use this to confirm wiring before touching the demo.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import config  # noqa: E402
from app.adapters.nemotron import NemotronInferenceAdapter  # noqa: E402
from app.services.clinic import get_clinic_context  # noqa: E402

print(f"Endpoint : {config.NEMOTRON_BASE_URL}")
print(f"Model    : {config.NEMOTRON_MODEL}")

payload = json.loads((Path(__file__).resolve().parents[1] /
                      "shared/sample_payloads/veneers_wedding.json").read_text())

t0 = time.time()
result = NemotronInferenceAdapter().analyze(payload["transcript"], get_clinic_context())
dt = int((time.time() - t0) * 1000)

source = result.get("_source", "unknown")
ok = source == "nemotron"
print(f"\nSource   : {source}   {'✅ MODEL ANSWERED' if ok else '⚠️  FELL BACK TO HEURISTIC'}  ({dt}ms)")
print(f"Score    : {result['score']['label'].upper()} {result['score'].get('value')} (conf {result['score'].get('confidence')})")
print(f"Summary  : {result.get('summary', '')[:160]}")
if not ok:
    print("\nTroubleshoot: is NEMOTRON_BASE_URL reachable from here? Try:")
    print(f"  curl {config.NEMOTRON_BASE_URL}/models")
sys.exit(0 if ok else 1)
