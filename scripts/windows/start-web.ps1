$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

if (-not (Test-Path "node_modules")) {
    Write-Host "Dependências Node não encontradas. Executando npm install..." -ForegroundColor Yellow
    npm install
}

if (-not (Test-Path ".env.local")) {
    @"
GPU_API_URL=http://127.0.0.1:8000
"@ | Set-Content -Encoding UTF8 ".env.local"

    Write-Host ".env.local criado com GPU_API_URL=http://127.0.0.1:8000" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Alcantara Studio - interface local ===" -ForegroundColor Cyan
Write-Host "Abrindo Next.js em http://localhost:3000"
Write-Host ""

npm run dev
