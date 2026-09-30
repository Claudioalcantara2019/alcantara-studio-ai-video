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
Write-Host "=== SISTEMA PRONTO ===" -ForegroundColor Green
Write-Host ""
Write-Host "GPU Worker: http://127.0.0.1:8000/health"
Write-Host "Interface:   http://localhost:3000"
Write-Host ""
Write-Host "Abrindo a interface..." -ForegroundColor Cyan
Start-Process "http://localhost:3000"
Write-Host ""
Write-Host "Iniciando Next.js. Feche esta janela para parar a interface." -ForegroundColor Yellow
Write-Host ""

npm run dev
