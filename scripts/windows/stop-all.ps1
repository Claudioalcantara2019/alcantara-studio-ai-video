$ErrorActionPreference = "Continue"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

Write-Host ""
Write-Host "=== ALCANTARA STUDIO - PARAR TUDO ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Parando GPU Worker..." -ForegroundColor Yellow
docker compose -f docker-compose.gpu.yml down

Write-Host ""
Write-Host "O Next.js é executado em primeiro plano pelo start-all.ps1." -ForegroundColor Yellow
Write-Host "Se ele estiver aberto em outra janela, pressione Ctrl+C nessa janela."
Write-Host ""
Write-Host "GPU Worker parado." -ForegroundColor Green
