$ErrorActionPreference = "Continue"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

Write-Host ""
Write-Host "=== ALCANTARA STUDIO - PARAR TUDO ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Parando interface Next.js..." -ForegroundColor Yellow
if (Test-Path ".alcantara-web.pid") {
    $webPid = Get-Content ".alcantara-web.pid" | Select-Object -First 1
    if ($webPid -match "^\d+$") {
        try {
            Stop-Process -Id ([int]$webPid) -Force -ErrorAction Stop
            Write-Host "[OK] Next.js parado." -ForegroundColor Green
        } catch {
            Write-Host "[INFO] Processo Next.js já não estava ativo." -ForegroundColor Yellow
        }
    }
    Remove-Item ".alcantara-web.pid" -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "[INFO] Nenhum PID da interface registrado." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Parando GPU Worker..." -ForegroundColor Yellow
docker compose -f docker-compose.gpu.yml down

Write-Host ""
Write-Host "GPU Worker parado." -ForegroundColor Green
