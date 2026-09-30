$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

Write-Host ""
Write-Host "=== ALCANTARA STUDIO - GO NVIDIA ===" -ForegroundColor Cyan
Write-Host ""

function Fail($message) {
    Write-Host "[ERRO] $message" -ForegroundColor Red
    Write-Host ""
    Write-Host "O teste MuseTalk não deve ser iniciado enquanto este pré-requisito falhar." -ForegroundColor Yellow
    exit 1
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail "Docker não encontrado."
}

if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    Fail "nvidia-smi não encontrado. Esta máquina não apresenta uma GPU NVIDIA utilizável pelo fluxo atual."
}

Write-Host "[OK] nvidia-smi encontrado." -ForegroundColor Green
$nvidiaOutput = nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
if ($LASTEXITCODE -ne 0) {
    Fail "nvidia-smi não conseguiu consultar a GPU."
}
$nvidiaOutput

Write-Host ""
Write-Host "Testando GPU dentro do Docker..." -ForegroundColor Yellow
docker run --rm --gpus all nvidia/cuda:11.8.0-runtime-ubuntu22.04 nvidia-smi
if ($LASTEXITCODE -ne 0) {
    Fail "Docker não conseguiu acessar a GPU NVIDIA."
}

Write-Host ""
Write-Host "[OK] Windows + NVIDIA + Docker estão prontos para a próxima etapa." -ForegroundColor Green
Write-Host ""
Write-Host "Agora execute:" -ForegroundColor Cyan
Write-Host "  .\scripts\windows\start-gpu-worker.ps1"
Write-Host ""
Write-Host "Depois que o worker ficar pronto, execute:" -ForegroundColor Cyan
Write-Host "  .\scripts\windows\start-web.ps1"
Write-Host ""
Write-Host "O primeiro job curto vem antes do teste de 4:17."
