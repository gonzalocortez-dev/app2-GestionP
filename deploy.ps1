# Deploy a Reflex Cloud — https://build.reflex.dev/
# Sube secretos desde .env.supabase (PostgreSQL en la nube). Nunca localhost ni SQLite.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$reflex = Join-Path $PSScriptRoot ".venv\Scripts\reflex.exe"
if (-not (Test-Path $reflex)) {
    Write-Error "No se encontró el entorno virtual. Ejecutá: py -3.13 -m venv .venv && pip install -r requirements.txt"
}

$envFile = Join-Path $PSScriptRoot ".env.supabase"
if (-not (Test-Path $envFile)) {
    Write-Host ""
    Write-Host "Falta .env.supabase con DATABASE_URL de Supabase (Session pooler)." -ForegroundColor Yellow
    Write-Host "Copiá .env.supabase.example a .env.supabase y pegá la URI de Connect → Session pooler."
    Write-Host ""
    exit 1
}

$db = Select-String -Path $envFile -Pattern "^DATABASE_URL=(.+)$" | ForEach-Object { $_.Matches[0].Groups[1].Value.Trim() }
if (-not $db) {
    Write-Host "DATABASE_URL no está en .env.supabase." -ForegroundColor Red
    exit 1
}
if ($db -match "localhost|127\.0\.0\.1|sqlite") {
    Write-Host ""
    Write-Host "DATABASE_URL no puede ser localhost ni SQLite. Los datos se perderían en Cloud." -ForegroundColor Red
    Write-Host "Usá Session pooler: aws-0-us-east-2.pooler.supabase.com"
    Write-Host ""
    exit 1
}
if ($db -notmatch "supabase") {
    Write-Host "DATABASE_URL no parece de Supabase. Abortando." -ForegroundColor Red
    exit 1
}

Write-Host "Compilando..." -ForegroundColor Cyan
& $reflex compile --dry
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "1) Si no iniciaste sesión: reflex login (se abre el navegador en build.reflex.dev)" -ForegroundColor Cyan
Write-Host "2) Creá un proyecto en https://build.reflex.dev/ y pegá el project id en cloud.yml" -ForegroundColor Cyan
Write-Host "3) Desplegando con secretos de .env.supabase..." -ForegroundColor Cyan
Write-Host ""

& $reflex deploy --config cloud.yml --no-interactive
exit $LASTEXITCODE
