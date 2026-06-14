# Windows: start the FastAPI backend. Run from repo root or anywhere.
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location "$repo\backend"
if (-not (Test-Path ".venv")) { python -m venv .venv }
. .\.venv\Scripts\Activate.ps1
pip install -q -r requirements.txt
Write-Host "Backend on http://localhost:8080  (health: /api/health)" -ForegroundColor Green
uvicorn app.main:app --port 8080
