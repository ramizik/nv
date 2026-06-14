# inference/

Everything about the reasoning layer and how to swap mock ↔ real local inference.

## Layout
- `local/mock_inference.py` — CLI to run the mock analysis on a transcript fixture (no server).
- `local/sample_inputs/`, `local/sample_outputs/` — fixtures (golden veneers output lives here).
- `remote/` — scripts to serve the real model on the **GB10 NVIDIA box**:
  - `start_nemotron.sh` — serve Nemotron (vLLM) on :8000, OpenAI-compatible. **Set `MODEL`.**
  - `run_model_server.sh` — stable entry point delegating to the above.
  - `start_personaplex.sh` — voice service placeholder (stretch).
  - `healthcheck.sh` — verify GPU + `/v1/models` + a tiny completion.

## Mock vs real
The backend picks the adapter from `.env`:
- `INFERENCE_BACKEND=mock` (default) → `backend/app/adapters/mock.py` (rule-based, zero deps).
- `INFERENCE_BACKEND=nemotron` → `backend/app/adapters/nemotron.py` → calls `NEMOTRON_BASE_URL`.

The Nemotron adapter asks for the **same partial-`LeadAnalysis` JSON** the mock returns, so
nothing upstream changes. On any error it **falls back to mock** — a flaky model never breaks
the demo. Full GB10 setup: `../docs/setup-remote-nvidia.md`.

## Quick local check (no server)
Uses the backend deps, so run it with the backend venv's Python:
```bash
# from repo root, after backend setup (scripts/linux/setup.sh)
./backend/.venv/bin/python inference/local/mock_inference.py shared/sample_payloads/veneers_wedding.json
```
