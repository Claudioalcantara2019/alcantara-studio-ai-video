[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$VideoPath,

    [Parameter(Mandatory = $true)]
    [string]$AudioPath,

    [ValidateSet("16:9", "9:16")]
    [string]$Format = "16:9",

    [ValidateSet("original", "studio", "stage", "cinematic")]
    [string]$Scene = "original",

    [string]$OutputPath = "",

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

function Invoke-JsonGet($url) {
    return Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 10
}

function Add-FilePart($multipart, $name, $path) {
    $stream = [System.IO.File]::OpenRead($path)
    $content = New-Object System.Net.Http.StreamContent($stream)
    $content.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("application/octet-stream")
    $multipart.Add($content, $name, [System.IO.Path]::GetFileName($path))
    return $stream
}

if (-not (Test-Path -LiteralPath $VideoPath -PathType Leaf)) {
    Fail "Vídeo não encontrado: $VideoPath"
}
if (-not (Test-Path -LiteralPath $AudioPath -PathType Leaf)) {
    Fail "Áudio não encontrado: $AudioPath"
}

$videoFull = (Resolve-Path -LiteralPath $VideoPath).Path
$audioFull = (Resolve-Path -LiteralPath $AudioPath).Path

if ([System.IO.Path]::GetExtension($videoFull).ToLowerInvariant() -ne ".mp4") {
    Fail "O vídeo-base precisa ser MP4."
}

$allowedAudio = @(".mp3", ".wav", ".m4a", ".aac", ".flac")
if ($allowedAudio -notcontains [System.IO.Path]::GetExtension($audioFull).ToLowerInvariant()) {
    Fail "O áudio precisa ser MP3, WAV, M4A, AAC ou FLAC."
}

$worker = "http://127.0.0.1:8000"

Write-Host ""
Write-Host "=== ALCANTARA STUDIO - TESTE DE PIPELINE ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Vídeo : $videoFull"
Write-Host "Áudio : $audioFull"
Write-Host "Formato: $Format"
Write-Host "Cena  : $Scene"
Write-Host ""

try {
    $health = Invoke-JsonGet "$worker/health"
} catch {
    Fail "GPU Worker não respondeu em $worker."
}

if ($health.ok -ne $true) {
    Write-Host "[ERRO] Worker respondeu, mas não está READY." -ForegroundColor Red
    $health | ConvertTo-Json -Depth 10
    Fail "Corrija NVIDIA/CUDA/modelos antes do teste."
}

Write-Host "[OK] GPU Worker READY." -ForegroundColor Green
if ($health.readiness.gpu.name) {
    Write-Host ("GPU: {0}" -f $health.readiness.gpu.name)
}

$client = New-Object System.Net.Http.HttpClient
$client.Timeout = [TimeSpan]::FromMinutes(10)
$multipart = New-Object System.Net.Http.MultipartFormDataContent
$streams = @()

try {
    $streams += Add-FilePart $multipart "video" $videoFull
    $streams += Add-FilePart $multipart "audio" $audioFull

    $formatContent = New-Object System.Net.Http.StringContent($Format)
    $sceneContent = New-Object System.Net.Http.StringContent($Scene)
    $multipart.Add($formatContent, "format")
    $multipart.Add($sceneContent, "scene")

    Write-Host ""
    Write-Host "[1/4] Enviando arquivos..." -ForegroundColor Yellow

    $response = $client.PostAsync("$worker/generate", $multipart).GetAwaiter().GetResult()
    $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()

    if (-not $response.IsSuccessStatusCode) {
        Write-Host $body
        Fail ("Worker recusou o job: HTTP {0}" -f [int]$response.StatusCode)
    }

    $job = $body | ConvertFrom-Json
    $jobId = $job.jobId

    if (-not $jobId) {
        Fail "O Worker não devolveu um jobId."
    }

    Write-Host "[OK] Job criado: $jobId" -ForegroundColor Green
}
catch {
    Fail $_.Exception.Message
}
finally {
    foreach ($stream in $streams) {
        if ($stream) { $stream.Dispose() }
    }
    $multipart.Dispose()
    $client.Dispose()
}

Write-Host ""
Write-Host "[2/4] Acompanhando processamento..." -ForegroundColor Yellow

$started = Get-Date
$deadline = $started.AddMinutes($TimeoutMinutes)
$lastStage = ""
$lastProgress = -1

while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds $PollSeconds

    try {
        $job = Invoke-JsonGet "$worker/jobs/$jobId"
    } catch {
        Write-Host "[AVISO] Falha temporária ao consultar o job. Tentando novamente..." -ForegroundColor Yellow
        continue
    }

    $stage = [string]$job.stage
    $progress = [int]$job.progress

    if ($stage -ne $lastStage -or $progress -ne $lastProgress) {
        Write-Host ("[{0}] {1}% - {2}" -f $job.status, $progress, $stage)
        if ($job.message) {
            Write-Host ("       {0}" -f $job.message)
        }
        $lastStage = $stage
        $lastProgress = $progress
    }

    if ($job.status -eq "completed") {
        break
    }

    if ($job.status -eq "failed") {
        Write-Host ""
        $job | ConvertTo-Json -Depth 12
        Fail "O Worker marcou o job como FAILED."
    }
}

if ($job.status -ne "completed") {
    Fail "Tempo limite de $TimeoutMinutes minutos atingido. O job pode continuar no Worker."
}

Write-Host ""
Write-Host "[OK] Processamento concluído." -ForegroundColor Green

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputPath = Join-Path $root "alcantara-output-$stamp.mp4"
} else {
    $parent = Split-Path -Parent $OutputPath
    if ($parent -and -not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
}

Write-Host ""
Write-Host "[3/4] Baixando MP4 final..." -ForegroundColor Yellow

try {
    Invoke-WebRequest -Uri "$worker/jobs/$jobId/result" -OutFile $OutputPath -TimeoutSec 600
} catch {
    Fail "Não foi possível baixar o resultado: $($_.Exception.Message)"
}

if (-not (Test-Path -LiteralPath $OutputPath)) {
    Fail "O download terminou sem criar o arquivo."
}

$resultFile = Get-Item -LiteralPath $OutputPath
if ($resultFile.Length -le 0) {
    Fail "O MP4 baixado está vazio."
}

Write-Host "[OK] MP4 salvo em:" -ForegroundColor Green
Write-Host "     $($resultFile.FullName)"
Write-Host ("     {0:N2} MB" -f ($resultFile.Length / 1MB))

Write-Host ""
Write-Host "[4/4] Métricas do job..." -ForegroundColor Yellow
$finalJob = Invoke-JsonGet "$worker/jobs/$jobId"

if ($finalJob.performance) {
    $finalJob.performance | ConvertTo-Json -Depth 10
} else {
    Write-Host "[INFO] O job não possui métricas de performance."
}

Write-Host ""
Write-Host "=== TESTE DE PIPELINE CONCLUÍDO ===" -ForegroundColor Green
Write-Host ""
Write-Host "Job:       $jobId"
Write-Host "Resultado: $($resultFile.FullName)"
Write-Host ""
Write-Host "Critérios para considerar o teste aprovado:"
Write-Host "  [ ] MP4 abre normalmente"
Write-Host "  [ ] boca acompanha a nova música"
Write-Host "  [ ] áudio final é a música enviada"
Write-Host "  [ ] duração acompanha a música"
Write-Host "  [ ] formato corresponde ao escolhido"
Write-Host "  [ ] resultado pode ser usado fora do projeto"
Write-Host ""
