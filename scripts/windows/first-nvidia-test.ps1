[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ShortVideoPath,

    [Parameter(Mandatory = $true)]
    [string]$ShortAudioPath,

    [string]$LongVideoPath = "",
    [string]$LongAudioPath = "",

    [ValidateSet("16:9", "9:16")]
    [string]$Format = "16:9",

    [ValidateSet("original", "studio", "stage", "cinematic")]
    [string]$Scene = "original",

    [int]$TimeoutMinutes = 60
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

function Fail($message) {
    Write-Host ""
    Write-Host "[ERRO] $message" -ForegroundColor Red
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ALCANTARA STUDIO - PRIMEIRO TESTE NVIDIA" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] Pré-voo NVIDIA + Docker" -ForegroundColor Yellow
& "$PSScriptRoot\go-nvidia.ps1"
if ($LASTEXITCODE -ne 0) {
    Fail "Pré-voo NVIDIA falhou."
}

Write-Host ""
Write-Host "[2/3] Iniciando/verificando GPU Worker" -ForegroundColor Yellow
& "$PSScriptRoot\start-gpu-worker.ps1"
if ($LASTEXITCODE -ne 0) {
    Fail "GPU Worker não ficou pronto."
}

Write-Host ""
Write-Host "[3/3] Executando benchmark" -ForegroundColor Yellow

$arguments = @(
    "-ShortVideoPath", $ShortVideoPath,
    "-ShortAudioPath", $ShortAudioPath,
    "-Format", $Format,
    "-Scene", $Scene,
    "-TimeoutMinutes", $TimeoutMinutes
)

if (-not [string]::IsNullOrWhiteSpace($LongVideoPath)) {
    $arguments += @("-LongVideoPath", $LongVideoPath)
    $arguments += @("-LongAudioPath", $LongAudioPath)
}

& "$PSScriptRoot\benchmark-pipeline.ps1" @arguments
if ($LASTEXITCODE -ne 0) {
    Fail "Benchmark falhou."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " PRIMEIRO TESTE NVIDIA CONCLUÍDO" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Os relatórios estão em:"
Write-Host "  $root\reports"
Write-Host ""
Write-Host "Próximo passo: analisar tempo, VRAM e qualidade do MP4 antes de alterar o batch."
Write-Host ""
