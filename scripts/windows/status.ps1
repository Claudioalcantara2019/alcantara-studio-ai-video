$ErrorActionPreference = "Continue"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

Write-Host ""
Write-Host "=== ALCANTARA STUDIO - STATUS ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "[WINDOWS / NVIDIA]" -ForegroundColor Yellow
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $gpu = nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] NVIDIA:"
        $gpu
    } else {
        Write-Host "[ERRO] nvidia-smi não conseguiu consultar a GPU."
    }
} else {
    Write-Host "[ERRO] nvidia-smi não encontrado."
}

Write-Host ""
Write-Host "[DOCKER]" -ForegroundColor Yellow
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker version --format "Client: {{.Client.Version}} / Server: {{.Server.Version}}"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERRO] Docker não está respondendo."
    }
} else {
    Write-Host "[ERRO] Docker não encontrado."
}

Write-Host ""
Write-Host "[GPU WORKER]" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 5
    if ($health.ok) {
        Write-Host "[OK] Worker pronto." -ForegroundColor Green
    } else {
        Write-Host "[AGUARDANDO] Worker respondeu, mas ainda não está pronto." -ForegroundColor Yellow
    }
    $health | ConvertTo-Json -Depth 10
} catch {
    Write-Host "[OFFLINE] GPU Worker não está respondendo." -ForegroundColor Red
}

Write-Host ""
Write-Host "[DOCKER CONTAINER]" -ForegroundColor Yellow
docker compose -f docker-compose.gpu.yml ps

Write-Host ""
Write-Host "[WEB]" -ForegroundColor Yellow
try {
    $web = Invoke-WebRequest -Uri "http://localhost:3000" -Method Head -TimeoutSec 5
    Write-Host ("[OK] Next.js respondeu com HTTP {0}." -f $web.StatusCode) -ForegroundColor Green
} catch {
    Write-Host "[OFFLINE] Next.js não está respondendo." -ForegroundColor Red
}

Write-Host ""
