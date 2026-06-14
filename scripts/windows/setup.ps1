# Windows one-time setup: env file + backend venv + frontend deps.
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "Created .env (all-mock defaults)" -ForegroundColor Green }
Set-Location "$repo\backend"; python -m venv .venv; . .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
Set-Location "$repo\frontend"; npm install
Write-Host "Setup done. Run scripts\windows\run_backend.ps1 and run_frontend.ps1" -ForegroundColor Green
