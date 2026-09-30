$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

Write-Host ""
Write-Host "=== ALCANTARA STUDIO - INICIAR TUDO ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] Verificando NVIDIA + Docker..." -ForegroundColor Yellow
& "$PSScriptRoot\go-nvidia.ps1"
if ($LASTEXITCODE -ne 0) {
    throw "Pré-voo NVIDIA falhou."
}

Write-Host ""
Write-Host "[2/3] Iniciando GPU Worker..." -ForegroundColor Yellow
& "$PSScriptRoot\start-gpu-worker.ps1"
if ($LASTEXITCODE -ne 0) {
    throw "GPU Worker não ficou pronto."
}

Write-Host ""
Write-Host "[3/3] Preparando interface web..." -ForegroundColor Yellow
if (-not (Test-Path "node_modules")) {
    npm install
    if ($LASTEXITCODE -ne 0) {
        throw "npm install falhou."
    }
}

if (-not (Test-Path ".env.local")) {
    @"
GPU_API_URL=http://127.0.0.1:8000
"@ | Set-Content -Encoding UTF8 ".env.local"
}

Write-Host ""
Write-Host "Iniciando Next.js em uma janela separada..." -ForegroundColor Yellow

$webProcess = Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", "Set-Location '$root'; npm run dev" -PassThru
$webProcess.Id | Set-Content -Encoding ASCII ".alcantara-web.pid"

$webTimeout = 120
$webElapsed = 0
$webReady = $false

while ($webElapsed -lt $webTimeout) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000" -Method Head -TimeoutSec 3
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
            $webReady = $true
            break
        }
    } catch {
    }

    Start-Sleep -Seconds 2
    $webElapsed += 2
}

if (-not $webReady) {
    Write-Host "[ERRO] Next.js não respondeu em 120 segundos." -ForegroundColor Red
    Remove-Item ".alcantara-web.pid" -Force -ErrorAction SilentlyContinue
    try { Stop-Process -Id $webProcess.Id -Force -ErrorAction SilentlyContinue } catch {}
    throw "Interface web não ficou pronta."
}

Write-Host ""
Write-Host "=== SISTEMA PRONTO ===" -ForegroundColor Green
Write-Host ""
Write-Host "GPU Worker: http://127.0.0.1:8000/health"
Write-Host "Interface:   http://localhost:3000"
Write-Host ""
Write-Host "Abrindo a interface..." -ForegroundColor Cyan
Start-Process "http://localhost:3000"
Write-Host ""
Write-Host "PID da janela Next.js: $($webProcess.Id)"
Write-Host "Use .\scripts\windows\status.ps1 para consultar o sistema."
Write-Host "Use .\scripts\windows\stop-all.ps1 para parar tudo."
Write-Host ""
