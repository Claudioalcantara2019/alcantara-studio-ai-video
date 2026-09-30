param(
    [Parameter(Mandatory = $true)]
    [string]$JobId
)

$ErrorActionPreference = "Stop"

$url = "http://127.0.0.1:8000/jobs/$JobId"

Write-Host ""
Write-Host "=== Alcantara Studio - job ===" -ForegroundColor Cyan
Write-Host "Job: $JobId"
Write-Host ""

$data = Invoke-RestMethod -Uri $url -TimeoutSec 10
$data | ConvertTo-Json -Depth 12

if ($data.performance) {
    Write-Host ""
    Write-Host "=== Métricas ===" -ForegroundColor Yellow
    Write-Host ("Tempo de processamento: {0}s" -f $data.performance.processingSeconds)
    Write-Host ("Duração final:          {0}s" -f $data.performance.generatedDurationSeconds)
    Write-Host ("Tamanho do MP4:         {0} bytes" -f $data.performance.resultBytes)
    Write-Host ("Batch MuseTalk:         {0}" -f $data.performance.batchSize)
}

if ($data.stageTiming) {
    Write-Host ""
    Write-Host "=== Etapas ===" -ForegroundColor Yellow
    foreach ($entry in $data.stageTiming.PSObject.Properties) {
        Write-Host ("{0}: {1}s" -f $entry.Name, $entry.Value)
    }
}

if ($data.gpu) {
    Write-Host ""
    Write-Host "=== GPU / VRAM ===" -ForegroundColor Yellow
    $data.gpu | ConvertTo-Json -Depth 5
}
