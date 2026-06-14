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
The real path routes reasoning through **Hermes** (`:8642`), which delegates to its local
default model **Qwen3-30B** on the box's Ollama. We run no model server of our own. Edit `.env`
(`HERMES_API_KEY` = `API_SERVER_KEY` from the box's `~/.hermes/.env`):
```
INFERENCE_BACKEND=hermes
CHAT_BACKEND=hermes
HERMES_BASE_URL=http://127.0.0.1:8642
HERMES_API_KEY=<API_SERVER_KEY from ~/.hermes/.env>
HERMES_INFERENCE_MODEL=        # blank = Hermes default (local Qwen3-30B)
```
Hermes binds localhost on the box, so from Windows you must tunnel:
`ssh -L 8642:localhost:8642 user@<gb10-host>`, then use `http://127.0.0.1:8642`.
For the live demo we instead run the **backend on the GB10** (`:8090`) — see
`docs/setup-remote-nvidia.md` and `docs/hermes-integration.md`. (Fallback: `INFERENCE_BACKEND=qwen`
talks directly to Ollama at `:11434` — tunnel `11434` too; see `docs/setup-remote-nvidia.md`.)

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
