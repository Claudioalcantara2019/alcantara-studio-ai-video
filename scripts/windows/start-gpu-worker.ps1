$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

Write-Host ""
Write-Host "=== Alcantara Studio - iniciando GPU Worker ===" -ForegroundColor Cyan
Write-Host "Projeto: $root"
Write-Host ""

docker compose -f docker-compose.gpu.yml up --build -d

if ($LASTEXITCODE -ne 0) {
    throw "Falha ao iniciar o GPU Worker."
}

Write-Host ""
Write-Host "Worker iniciado. Verificando status..." -ForegroundColor Green
docker compose -f docker-compose.gpu.yml ps

Write-Host ""
Write-Host "Health:"
try {
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 10 | ConvertTo-Json -Depth 8
} catch {
    Write-Host "O worker ainda pode estar inicializando os modelos."
    Write-Host "Consulte os logs com:"
    Write-Host "docker compose -f docker-compose.gpu.yml logs -f alcantara-gpu-worker"
}
