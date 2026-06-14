# Windows: start the Vite dashboard dev server.
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location "$repo\frontend"
if (-not (Test-Path "node_modules")) { npm install }
Write-Host "Dashboard on http://localhost:5173" -ForegroundColor Green
npm run dev
