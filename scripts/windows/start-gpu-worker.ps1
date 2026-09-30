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
Write-Host "Container iniciado." -ForegroundColor Green
Write-Host "A primeira execução pode baixar os modelos MuseTalk e demorar vários minutos." -ForegroundColor Yellow
Write-Host ""

$timeoutSeconds = 30 * 60
$intervalSeconds = 10
$elapsed = 0
$ready = $false

while ($elapsed -lt $timeoutSeconds) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 5

        if ($health.ok -eq $true) {
            $ready = $true
            Write-Host "[OK] GPU Worker pronto." -ForegroundColor Green
            Write-Host ""
            $health | ConvertTo-Json -Depth 10
            break
        }

        $modelState = "incompletos"
        if ($health.readiness -and $health.readiness.models) {
            $allModels = $true
            foreach ($value in $health.readiness.models.PSObject.Properties.Value) {
                if (-not $value) { $allModels = $false }
            }
            if ($allModels) { $modelState = "completos" }
        }

        Write-Host ("[AGUARDANDO] {0}s - GPU/modelos ainda não prontos (modelos: {1})" -f $elapsed, $modelState) -ForegroundColor Yellow
    } catch {
        Write-Host ("[AGUARDANDO] {0}s - worker ainda iniciando..." -f $elapsed) -ForegroundColor Yellow
    }

    Start-Sleep -Seconds $intervalSeconds
    $elapsed += $intervalSeconds
}

if (-not $ready) {
    Write-Host ""
    Write-Host "[ERRO] O worker não ficou pronto dentro de 30 minutos." -ForegroundColor Red
    Write-Host ""
    Write-Host "Últimos logs do container:" -ForegroundColor Yellow
    docker compose -f docker-compose.gpu.yml logs --tail 120 alcantara-gpu-worker
    throw "GPU Worker não ficou pronto. Veja os logs acima."
}

Write-Host ""
Write-Host "Próximo passo:" -ForegroundColor Cyan
Write-Host "  .\scripts\windows\start-web.ps1"
Write-Host ""
