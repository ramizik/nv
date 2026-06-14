# Setup — Remote NVIDIA (GB10) Linux box

Serves the **local reasoning model (Nemotron)** behind an OpenAI-compatible endpoint so
the backend can call it with `INFERENCE_BACKEND=nemotron`. All inference stays on-prem.

## Prereqs
- NVIDIA drivers + CUDA (`nvidia-smi` works)
- Python 3.12 / Docker (depending on serving choice)
- The repo pulled here too (`shared/` is the cross-machine source of truth)

## 1. Serve the model (OpenAI-compatible)
The backend expects an `/v1/chat/completions` endpoint that honors
`response_format: {type: json_object}`. Any of these work — pick what's installed:

- **vLLM** (common): `inference/remote/start_nemotron.sh` wraps
  `vllm serve <model> --port 8000`.
- **NVIDIA NIM**: run the Nemotron NIM container exposing port 8000.
- **TGI / llama.cpp server**: any OpenAI-compatible shim on port 8000.

```bash
cd inference/remote
./start_nemotron.sh            # starts the model server on :8000
./healthcheck.sh               # curls /v1/models and a tiny completion
```
Edit `start_nemotron.sh` to set the exact model id you have pulled (Nemotron family;
Llama/Qwen also work as drop-ins — update `NEMOTRON_MODEL` in `.env` to match).

## 2. (Optional) PersonaPlex voice
`./start_personaplex.sh` is a placeholder for the voice service. For the hackathon demo we
use a transcript fixture; wire live voice only after the dashboard + chat are solid.

## 3. Point the backend at this box
On whichever machine runs the backend, set in `.env`:
```
INFERENCE_BACKEND=nemotron
NEMOTRON_BASE_URL=http://<this-box-ip>:8000/v1
NEMOTRON_MODEL=<the-model-id-you-served>
```
If backend runs on Windows and can't reach the box directly, tunnel:
`ssh -L 8000:localhost:8000 user@<this-box>` then use `http://localhost:8000/v1`.

## 4. Verify the full path
```bash
curl -s http://localhost:8000/v1/models           # model server up
# from the backend host:
curl -s -X POST http://localhost:8080/api/simulate | python -m json.tool | grep -A2 system_status
# Nemotron status should read "online" with a GB10 latency.
```

## Notes
- The Nemotron adapter **falls back to mock** on any error — a flaky model never breaks
  the demo, it just shows `status: mock`.
- Run the backend ON the GB10 box for the most "fully local" story, with the frontend on
  Windows pointing `VITE_API_BASE` at the box.
