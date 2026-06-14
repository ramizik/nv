# inference/

Everything about the reasoning layer and how to swap mock ↔ real local inference.

## Layout
- `local/mock_inference.py` — CLI to run the mock analysis on a transcript fixture (no server).
- `local/sample_inputs/`, `local/sample_outputs/` — fixtures (golden veneers output lives here).
- `remote/` — scripts for the **DIRECT-OLLAMA fallback** path on the **GB10 NVIDIA box**
  (the real demo path needs no model server — see "Mock vs real" below):
  - `start_qwen.sh` — ensure/​warm the **Qwen3-30B** model on **Ollama** (`:11434/v1`,
    OpenAI-compatible) for the direct fallback. vLLM `:8000` documented as an alternative.
  - `run_model_server.sh` — stable entry point delegating to the above.
  - `start_personaplex.sh` — voice service placeholder (stretch).
  - `healthcheck.sh` — verify GPU + `/v1/models` + a tiny completion (direct path).

> ⚠️ **~120 GB unified memory ⇒ only ONE large model resident at a time.** Qwen3-30B
> (~18 GB, ~3B active) is fast, stays resident, and coexists with the NIM voice stack.
> Nemotron-120B (~82 GB) is an optional heavier alternative that monopolizes the box.

## Mock vs real
The backend picks the adapter from `.env` (adapters live in `backend/app/adapters/inference.py`):
- `INFERENCE_BACKEND=mock` (default) → rule-based mock (zero deps).
- `INFERENCE_BACKEND=hermes` (**the real demo path**) → `HermesInferenceAdapter` → calls
  Hermes (`HERMES_BASE_URL`, default `http://127.0.0.1:8642`), which delegates to its local
  default model **Qwen3-30B** on the GB10. Inference stays on-box; **we run no model server**.
- `INFERENCE_BACKEND=qwen` (optional fallback; legacy alias `nemotron`) → `QwenInferenceAdapter`
  → talks **directly** to Ollama (`QWEN_BASE_URL`, default `http://127.0.0.1:11434/v1`).

Both adapters ask for the **same partial-`LeadAnalysis` JSON** the mock returns, so nothing
upstream changes. On any error they **fall back to mock** — a flaky model never breaks the
demo. Connectivity test: `backend/test_hermes_inference.py`. Full GB10 setup:
`../docs/setup-remote-nvidia.md`.

## Quick local check (no server)
Uses the backend deps, so run it with the backend venv's Python:
```bash
# from repo root, after backend setup (scripts/linux/setup.sh)
./backend/.venv/bin/python inference/local/mock_inference.py shared/sample_payloads/veneers_wedding.json
```
