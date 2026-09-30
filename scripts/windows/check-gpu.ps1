$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "=== Alcantara Studio AI Video - diagnóstico GPU ===" -ForegroundColor Cyan
Write-Host ""

$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) {
    Write-Host "[OK] Docker encontrado: $($docker.Source)"
} else {
    Write-Host "[ERRO] Docker não encontrado."
    exit 1
}

$nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidia) {
    Write-Host "[OK] nvidia-smi encontrado."
    & nvidia-smi
} else {
    Write-Host "[AVISO] nvidia-smi não está disponível no PATH."
    Write-Host "        Isso normalmente significa que não há uma GPU NVIDIA/driver NVIDIA utilizável."
}

Write-Host ""
Write-Host "Testando acesso do Docker à GPU..."

& docker run --rm --gpus all nvidia/cuda:11.8.0-runtime-ubuntu22.04 nvidia-smi

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[OK] Docker conseguiu acessar uma GPU NVIDIA." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[ERRO] Docker não conseguiu acessar a GPU NVIDIA." -ForegroundColor Red
}

Write-Host ""
Write-Host "Testando worker local em http://127.0.0.1:8000/health ..."

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 5
    $health | ConvertTo-Json -Depth 8
} catch {
    Write-Host "[INFO] Worker não está respondendo. Isso é normal se o container ainda não foi iniciado."
}

Write-Host ""
