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
    [string]$ReportDir = "",
    [int]$PollSeconds = 5,
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

function Get-Job($jobId) {
    return Invoke-RestMethod -Uri "http://127.0.0.1:8000/jobs/$jobId" -Method Get -TimeoutSec 10
}

function Run-Test($label, $video, $audio) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " $label" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

    $output = @(& "$PSScriptRoot\test-pipeline.ps1" -VideoPath $video -AudioPath $audio -Format $Format -Scene $Scene -PollSeconds $PollSeconds -TimeoutMinutes $TimeoutMinutes 2>&1 | Tee-Object -Variable liveOutput)

    if ($LASTEXITCODE -ne 0) {
        Fail "$label falhou. O benchmark foi interrompido."
    }

    $jobLine = $output | Where-Object { $_.ToString() -match '^Job:\s+(.+)$' } | Select-Object -Last 1
    if (-not $jobLine) {
        Fail "Não foi possível identificar o jobId de $label."
    }

    $jobId = [regex]::Match($jobLine.ToString(), '^Job:\s+(.+)$').Groups[1].Value.Trim()
    $job = Get-Job $jobId

    if ($job.status -ne "completed") {
        Fail "$label terminou sem status completed."
    }

    return [PSCustomObject]@{
        label = $label
        jobId = $jobId
        status = $job.status
        performance = $job.performance
        stageTiming = $job.stageTiming
        gpu = $job.gpu
        media = $job.media
        resultUrl = $job.resultUrl
    }
}

if ([string]::IsNullOrWhiteSpace($ReportDir)) {
    $ReportDir = Join-Path $root "reports"
}
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null

foreach ($path in @($ShortVideoPath, $ShortAudioPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        Fail "Arquivo do teste curto não encontrado: $path"
    }
}

if (-not [string]::IsNullOrWhiteSpace($LongVideoPath)) {
    foreach ($path in @($LongVideoPath, $LongAudioPath)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            Fail "Arquivo do teste longo não encontrado: $path"
        }
    }
}

$health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 10
if ($health.ok -ne $true) {
    $health | ConvertTo-Json -Depth 10
    Fail "GPU Worker não está READY."
}

if ([string]::IsNullOrWhiteSpace($LongVideoPath) -xor [string]::IsNullOrWhiteSpace($LongAudioPath)) {
    Fail "Informe LongVideoPath e LongAudioPath juntos, ou deixe os dois vazios."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$results = @()

Write-Host ""
Write-Host "=== ALCANTARA STUDIO - BENCHMARK ===" -ForegroundColor Cyan
Write-Host "GPU: $($health.readiness.gpu.name)"
Write-Host "Formato: $Format"
Write-Host "Cena: $Scene"
Write-Host "Relatórios: $ReportDir"
Write-Host ""
Write-Host "Regra: teste curto primeiro; 4:17 somente depois." -ForegroundColor Yellow

$short = Run-Test "TESTE CURTO" $ShortVideoPath $ShortAudioPath
$results += $short

$shortReport = Join-Path $ReportDir "benchmark-short-$stamp.json"
$short | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 $shortReport

Write-Host ""
Write-Host "[OK] Teste curto concluído." -ForegroundColor Green
Write-Host "Relatório: $shortReport"

if (-not [string]::IsNullOrWhiteSpace($LongVideoPath)) {
    Write-Host ""
    Write-Host "Teste curto aprovado. Iniciando teste longo / 4:17." -ForegroundColor Yellow

    $long = Run-Test "TESTE LONGO / 4:17" $LongVideoPath $LongAudioPath
    $results += $long

    $longReport = Join-Path $ReportDir "benchmark-long-$stamp.json"
    $long | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 $longReport
    Write-Host ""
    Write-Host "[OK] Teste longo concluído." -ForegroundColor Green
    Write-Host "Relatório: $longReport"
}

$summary = [PSCustomObject]@{
    createdAt = (Get-Date).ToString("o")
    gpu = $health.readiness.gpu
    format = $Format
    scene = $Scene
    tests = $results
}

$summaryPath = Join-Path $ReportDir "benchmark-$stamp.json"
$summary | ConvertTo-Json -Depth 30 | Set-Content -Encoding UTF8 $summaryPath

Write-Host ""
Write-Host "=== BENCHMARK FINALIZADO ===" -ForegroundColor Green
Write-Host ""
Write-Host "Relatório consolidado:"
Write-Host "  $summaryPath"
Write-Host ""
Write-Host "Os JSONs ficam em reports/ e não precisam ser versionados."
Write-Host ""
