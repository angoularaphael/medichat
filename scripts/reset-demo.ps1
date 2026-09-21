$ErrorActionPreference = "Stop"
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $base
Write-Host "Reset demo EIR via API..."
try {
  Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/demo/reset"
  Write-Host "OK"
} catch {
  Write-Host "API non disponible. Demarrez docker compose up."
  exit 1
}
