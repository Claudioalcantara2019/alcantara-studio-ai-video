$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

Write-Host ""
Write-Host "=== Alcantara Studio - validação local ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/4] Python worker..."
python -m py_compile gpu-worker/main.py gpu-worker/musetalk_runner.py
if ($LASTEXITCODE -ne 0) { throw "Falha na compilação Python." }
Write-Host "[OK] Python"

Write-Host "[2/4] Docker Compose..."
docker compose -f docker-compose.gpu.yml config | Out-Null
if ($LASTEXITCODE -ne 0) { throw "docker-compose.gpu.yml inválido." }
Write-Host "[OK] Docker Compose"

Write-Host "[3/4] Node..."
if (-not (Test-Path "node_modules")) {
    Write-Host "node_modules não existe; instalando dependências..."
    npm install
}
npm run build
if ($LASTEXITCODE -ne 0) { throw "Falha no build Next.js." }
Write-Host "[OK] Next.js"

Write-Host "[4/5] Arquivos essenciais..."
$required = @(
    "app/page.tsx",
    "app/api/health/route.ts",
    "app/api/jobs/route.ts",
    "gpu-worker/main.py",
    "gpu-worker/musetalk_runner.py",
    "gpu-worker/Dockerfile",
    "gpu-worker/download_models.sh",
    "docker-compose.gpu.yml"
)

foreach ($file in $required) {
    if (-not (Test-Path $file)) {
        throw "Arquivo essencial ausente: $file"
    }
}

Write-Host "[OK] Arquivos essenciais"

Write-Host "[5/5] Sintaxe PowerShell..."
$scripts = @(
    "scripts/windows/check-gpu.ps1",
    "scripts/windows/start-gpu-worker.ps1",
    "scripts/windows/start-web.ps1",
    "scripts/windows/show-job.ps1",
    "scripts/windows/validate-project.ps1",
    "scripts/windows/go-nvidia.ps1",
    "scripts/windows/start-all.ps1",
    "scripts/windows/status.ps1",
    "scripts/windows/stop-all.ps1"
)
foreach ($script in $scripts) {
    if (-not (Test-Path $script)) {
        throw "Script ausente: $script"
    }
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        (Resolve-Path $script),
        [ref]$null,
        [ref]$errors
    ) | Out-Null
    if ($errors.Count -gt 0) {
        throw "Erro de sintaxe PowerShell em $script"
    }
}
Write-Host "[OK] PowerShell"

Write-Host ""
Write-Host "VALIDAÇÃO CONCLUÍDA." -ForegroundColor Green
Write-Host "Observação: esta validação não executa MuseTalk; para isso é necessária uma GPU NVIDIA."
