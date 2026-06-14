# Setup — Windows dev machine

Runs the **frontend** and (for the all-mock demo) the **backend**. PowerShell.

## Prereqs
- Python 3.12+  (`python --version`)
- Node 18+      (`node --version`)
- Git

## One-time
```powershell
git clone <repo-url> nv; cd nv
Copy-Item .env.example .env        # defaults = all-mock, single machine
```

## Backend (PowerShell)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --port 8080
# verify: http://localhost:8080/api/health
```
Or use the helper: `..\scripts\windows\run_backend.ps1`

## Frontend (separate terminal)
```powershell
cd frontend
npm install
npm run dev          # http://localhost:5173
```
Or: `.\scripts\windows\run_frontend.ps1`

## Pointing at the remote GB10 box (optional, for real inference)
Nemotron-120B is served on the box via **Ollama** at `:11434` (no key). Edit `.env`:
```
INFERENCE_BACKEND=nemotron
NEMOTRON_BASE_URL=http://127.0.0.1:11434/v1
NEMOTRON_MODEL=lifeos-nemotron-120b:latest
```
Ollama binds localhost on the box, so from Windows you must tunnel:
`ssh -L 11434:localhost:11434 user@<gb10-host>`, then use `http://127.0.0.1:11434/v1`.
For the live demo we instead run the **backend on the GB10** (`:8090`) — see
`docs/setup-remote-nvidia.md` and `docs/hermes-integration.md`.

## Discord alert (optional)
The real path hands off to the teammate's Hermes bot (`CHAT_BACKEND=hermes`); the raw webhook
below is a standalone fallback only. See `docs/hermes-integration.md`.
```
CHAT_BACKEND=discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/....
```

## Troubleshooting
- `Activate.ps1` blocked → `Set-ExecutionPolicy -Scope Process RemoteSigned`.
- CORS error in browser → confirm `CORS_ORIGINS` includes `http://localhost:5173`.
- Frontend can't reach API → check `VITE_API_BASE` and that backend is on 8080.
