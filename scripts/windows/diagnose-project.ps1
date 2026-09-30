$ErrorActionPreference = "Continue"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

Write-Host ""
Write-Host "=== ALCANTARA STUDIO — DIAGNÓSTICO ===" -ForegroundColor Cyan
Write-Host ""

function Test-CommandAvailable($name) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) {
        Write-Host "[OK] $name -> $($cmd.Source)" -ForegroundColor Green
        return $true
    }
    Write-Host "[--] $name não encontrado" -ForegroundColor Yellow
    return $false
}

Write-Host "1. Ferramentas locais"
$hasNode = Test-CommandAvailable "node"
$hasNpm = Test-CommandAvailable "npm"
$hasPython = Test-CommandAvailable "python"
$hasDocker = Test-CommandAvailable "docker"

Write-Host ""
Write-Host "2. Versões"
if ($hasNode) { node --version }
if ($hasNpm) { npm --version }
if ($hasPython) { python --version }
if ($hasDocker) { docker --version }

Write-Host ""
Write-Host "3. NVIDIA"
$nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidia) {
    Write-Host "[OK] nvidia-smi encontrado" -ForegroundColor Green
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
} else {
    Write-Host "[--] nvidia-smi não encontrado. Este PC pode não ter uma GPU NVIDIA." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "4. Docker GPU"
if ($hasDocker) {
    docker run --rm --gpus all nvidia/cuda:11.8.0-runtime-ubuntu22.04 nvidia-smi 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Docker conseguiu acessar a GPU NVIDIA." -ForegroundColor Green
    } else {
        Write-Host "[--] Docker não conseguiu executar o teste NVIDIA." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "5. Worker local"
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 5
    Write-Host "[OK] Worker respondeu." -ForegroundColor Green
    Write-Host ("Versão: " + $health.version)
    Write-Host ("GPU pronta: " + $health.ok)
    Write-Host ("GPU: " + $health.readiness.gpu.name)
    Write-Host ("Jobs: " + $health.jobs)
} catch {
    Write-Host "[--] Worker não está respondendo em http://127.0.0.1:8000" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "6. Arquivos principais"
$required = @(
    "app\page.tsx",
    "gpu-worker\main.py",
    "gpu-worker\musetalk_runner.py",
    "gpu-worker\Dockerfile",
    "docker-compose.gpu.yml",
    "scripts\windows\start-gpu-worker.ps1",
    "scripts\windows\start-web.ps1"
)

foreach ($file in $required) {
    if (Test-Path $file) {
        Write-Host "[OK] $file" -ForegroundColor Green
    } else {
        Write-Host "[--] $file ausente" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Diagnóstico concluído. Este script não altera o projeto nem inicia jobs."
