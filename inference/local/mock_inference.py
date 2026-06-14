#!/usr/bin/env python3
"""CLI: run the mock inference on a transcript fixture without starting the server.

Usage:
    python mock_inference.py ../../shared/sample_payloads/veneers_wedding.json

Reuses the backend's MockInferenceAdapter so the CLI and the API stay identical.
"""
import json
import sys
from pathlib import Path

# Make backend importable when run from anywhere in the repo.
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

from app.adapters.mock import MockInferenceAdapter  # noqa: E402
from app.services.clinic import get_clinic_context  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = MockInferenceAdapter().analyze(payload["transcript"], get_clinic_context())
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
