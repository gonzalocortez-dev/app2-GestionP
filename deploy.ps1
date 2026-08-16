# Deploy a Reflex Cloud — https://build.reflex.dev/
# Requisitos: .env con DATABASE_URL de producción (PostgreSQL en la nube, no localhost).

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$reflex = Join-Path $PSScriptRoot ".venv\Scripts\reflex.exe"
if (-not (Test-Path $reflex)) {
    Write-Error "No se encontró el entorno virtual. Ejecutá: py -3.13 -m venv .venv && pip install -r requirements.txt"
}

if (-not (Test-Path (Join-Path $PSScriptRoot ".env"))) {
    Write-Host ""
    Write-Host "Falta el archivo .env con variables de producción." -ForegroundColor Yellow
    Write-Host "Copiá .env.production.example a .env y completá DATABASE_URL (PostgreSQL en la nube)."
    Write-Host ""
    exit 1
}

$db = Select-String -Path ".env" -Pattern "^DATABASE_URL=(.+)$" | ForEach-Object { $_.Matches[0].Groups[1].Value.Trim() }
if ($db -match "localhost|127\.0\.0\.1") {
    Write-Host ""
    Write-Host "DATABASE_URL apunta a localhost. Reflex Cloud no puede usar tu PostgreSQL local." -ForegroundColor Red
    Write-Host "Usá Neon (https://neon.tech), Supabase u otro Postgres con URL pública."
    Write-Host ""
    exit 1
}

Write-Host "Compilando..." -ForegroundColor Cyan
& $reflex compile --dry
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "1) Si no iniciaste sesión: reflex login (se abre el navegador en build.reflex.dev)" -ForegroundColor Cyan
Write-Host "2) Creá un proyecto en https://build.reflex.dev/ y pegá el project id en cloud.yml" -ForegroundColor Cyan
Write-Host "3) Desplegando..." -ForegroundColor Cyan
Write-Host ""

& $reflex deploy --config cloud.yml --no-interactive
exit $LASTEXITCODE
