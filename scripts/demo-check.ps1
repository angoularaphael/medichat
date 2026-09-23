$ErrorActionPreference = "Stop"
$base = "http://localhost:8000"

Write-Host "Verification pre-soutenance EIR"
try {
    $health = Invoke-RestMethod "$base/api/health"
    if ($health.status -ne "ok") { throw "API non prete" }
    Write-Host "API: OK"
} catch {
    Write-Host "API: ECHEC. Lance docker compose up --build"
    exit 1
}

$login = Invoke-RestMethod "$base/api/auth/login" -Method Post -ContentType "application/json" -Body '{"username":"raphael","password":"qwerty123"}'
$headers = @{ Authorization = "Bearer $($login.access_token)" }
$status = Invoke-RestMethod "$base/api/system/status" -Headers $headers
Write-Host "Base: $($status.database) | MQTT: $($status.mqtt) | Ollama: $($status.ollama) | Mode: $($status.decision_mode)"
Write-Host "Lien vaisseau: $($status.linked_project.name) / $($status.linked_project.pillar)"

if (-not $status.database) {
    Write-Host "Base indisponible: demonstration bloquee"
    exit 1
}
if (-not $status.ollama) {
    Write-Host "Ollama hors ligne: la demo reste valide en mode regles locales"
}
Write-Host "Pret pour la demonstration"
