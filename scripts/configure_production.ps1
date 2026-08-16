# Configura .env y cloud.yml para Supabase + Reflex Cloud.
# Ejecutar desde la raíz del proyecto: .\scripts\configure_production.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

Write-Host ""
Write-Host "=== Configuración producción: Supabase + Reflex Cloud ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "En Supabase: Project Settings -> Database -> Connection string -> URI (Direct connection)"
Write-Host "Ejemplo: postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres"
Write-Host ""

$dbUrl = Read-Host "Pegá la DATABASE_URL completa (postgresql://...)"
$dbUrl = $dbUrl.Trim().Trim('"').Trim("'")

if ($dbUrl -match "^postgresql://") {
    $dbUrl = $dbUrl -replace "^postgresql://", "postgresql+psycopg://"
}
if ($dbUrl -notmatch "\?") {
    $dbUrl = "$dbUrl?sslmode=require"
} elseif ($dbUrl -notmatch "sslmode=") {
    $dbUrl = "$dbUrl&sslmode=require"
}

$reflexProject = Read-Host "Pegá el Project ID de Reflex Cloud (build.reflex.dev -> Project -> Settings)"
$reflexProject = $reflexProject.Trim()

$appUrl = Read-Host "URL pública de la app (Enter para dejar placeholder y actualizar después del deploy)"
if ([string]::IsNullOrWhiteSpace($appUrl)) {
    $appUrl = "https://polleria-gestion.reflex.run"
}

$envContent = @"
DATABASE_URL=$dbUrl
SEED_DEMO=false
APP_BASE_URL=$appUrl
MAIL_FROM_NAME=La Fábrica del Pollo
"@

Set-Content -Path (Join-Path $root ".env") -Value $envContent -Encoding UTF8
Write-Host "OK: .env actualizado" -ForegroundColor Green

$cloudYml = @"
# Reflex Cloud — https://build.reflex.dev/
project: $reflexProject
name: polleria-gestion
description: La Fábrica del Pollo — gestión integral (POS, inventario, finanzas)
envfile: .env
vmtype: c1m1
regions:
  - sjc
"@

Set-Content -Path (Join-Path $root "cloud.yml") -Value $cloudYml -Encoding UTF8
Write-Host "OK: cloud.yml actualizado" -ForegroundColor Green

Write-Host ""
Write-Host "Probando conexión a Supabase..." -ForegroundColor Cyan
& (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "scripts\test_db.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Siguiente:" -ForegroundColor Yellow
Write-Host "  1. reflex login          (completá login en el navegador y Enter)"
Write-Host "  2. .\deploy.ps1"
Write-Host ""
