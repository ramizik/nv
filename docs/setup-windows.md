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
Edit `.env`:
```
INFERENCE_BACKEND=nemotron
NEMOTRON_BASE_URL=http://<gb10-host-or-ip>:8000/v1
```
The GB10 server is started on the Linux box — see `docs/setup-remote-nvidia.md`.
Make sure the GB10 port is reachable from Windows (same LAN / SSH tunnel:
`ssh -L 8000:localhost:8000 user@gb10-host`, then use `http://localhost:8000/v1`).

## Discord alert (optional)
```
CHAT_BACKEND=discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/....
```

## Troubleshooting
- `Activate.ps1` blocked → `Set-ExecutionPolicy -Scope Process RemoteSigned`.
- CORS error in browser → confirm `CORS_ORIGINS` includes `http://localhost:5173`.
- Frontend can't reach API → check `VITE_API_BASE` and that backend is on 8080.
