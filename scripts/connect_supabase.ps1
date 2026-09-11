# Conecta Supabase a la app desplegada en Reflex Cloud.
# Uso: .\scripts\connect_supabase.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

Write-Host ""
Write-Host "=== Conectar Supabase + Reflex Cloud ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Proyecto detectado: bzhhjezqmwstgtfvrzxx.supabase.co"
Write-Host "Host pooler IPv4: aws-0-us-east-2.pooler.supabase.com:5432"
Write-Host ""
Write-Host "Supabase -> Connect -> Session pooler (NO Direct connection)."
Write-Host "Pegá la URI y reemplazá [YOUR-PASSWORD] por la contraseña del proyecto."
Write-Host ""

$rawUrl = Read-Host "Pegá la URI de Supabase (postgresql://...)"
$rawUrl = $rawUrl.Trim().Trim('"').Trim("'")

$dbUrl = $rawUrl
if ($dbUrl -match "^postgresql://") {
    $dbUrl = $dbUrl -replace "^postgresql://", "postgresql+psycopg://"
}
# Codificar @ y otros caracteres especiales en user:password@
if ($dbUrl -match "^postgresql\+psycopg://([^:@/]+):([^@/]+)@") {
    $user = $Matches[1]
    $pass = $Matches[2]
    $encodedPass = [uri]::EscapeDataString([uri]::UnescapeDataString($pass))
    $dbUrl = $dbUrl -replace "^postgresql\+psycopg://[^@]+@", "postgresql+psycopg://${user}:${encodedPass}@"
}
if ($dbUrl -notmatch "sslmode=") {
    if ($dbUrl -match "\?") { $dbUrl = "$dbUrl&sslmode=require" }
    else { $dbUrl = "$dbUrl?sslmode=require" }
}

$appUrl = Read-Host "URL pública de tu app en Reflex Cloud (ej. https://polleria-gestion.reflex.run)"
$appUrl = $appUrl.Trim().TrimEnd("/")
if (-not $appUrl.StartsWith("http")) {
    $appUrl = "https://$appUrl"
}

$appId = Read-Host "App ID de Reflex Cloud (Settings de la app, opcional Enter para omitir secrets CLI)"
$appId = $appId.Trim()

$supabaseEnv = @"
DATABASE_URL=$dbUrl
SEED_DEMO=false
APP_ENV=production
APP_BASE_URL=$appUrl
MAIL_FROM_NAME=La Fábrica del Pollo
"@

$supabaseEnvPath = Join-Path $root ".env.supabase"
Set-Content -Path $supabaseEnvPath -Value $supabaseEnv -Encoding UTF8
Write-Host "OK: guardado en .env.supabase" -ForegroundColor Green

# Probar conexión e inicializar tablas
Write-Host ""
Write-Host "Probando Supabase..." -ForegroundColor Cyan
$env:DATABASE_URL = $dbUrl
& (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "scripts\test_db.py")
if ($LASTEXITCODE -ne 0) {
    Write-Host "Revisá usuario, contraseña y que el proyecto Supabase esté activo." -ForegroundColor Red
    exit 1
}

Write-Host "Creando tablas en Supabase..." -ForegroundColor Cyan
& (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "scripts\init_production_db.py")
if ($LASTEXITCODE -ne 0) { exit 1 }

$createAdmin = Read-Host "¿Crear usuario admin en Supabase? (S/n)"
if ($createAdmin -ne "n" -and $createAdmin -ne "N") {
    $adminEmail = Read-Host "Email admin (Enter = admin.lafabrica@gmail.com)"
    if ([string]::IsNullOrWhiteSpace($adminEmail)) { $adminEmail = "admin.lafabrica@gmail.com" }
    $adminPass = Read-Host "Contraseña admin (Enter = Polleria123!)"
    if ([string]::IsNullOrWhiteSpace($adminPass)) { $adminPass = "Polleria123!" }
    $env:ADMIN_EMAIL = $adminEmail
    $env:ADMIN_PASSWORD = $adminPass
    & (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "scripts\create_admin.py")
}

if ($appId) {
    Write-Host ""
    Write-Host "Subiendo secretos a Reflex Cloud y reiniciando..." -ForegroundColor Cyan
    Write-Host "Completá login en el navegador si lo pide, luego Enter." -ForegroundColor Yellow
    & (Join-Path $root ".venv\Scripts\reflex.exe") cloud secrets update $appId --envfile $supabaseEnvPath --reboot
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Listo. Abrí: $appUrl" -ForegroundColor Green
    }
} else {
    Write-Host ""
    Write-Host "Configurá manualmente en Reflex Cloud -> Settings -> Secrets:" -ForegroundColor Yellow
    Write-Host "  DATABASE_URL = Session pooler postgresql+psycopg://postgres.bzhhjezqmwstgtfvrzxx:...@aws-0-us-east-2.pooler.supabase.com:5432/postgres?sslmode=require"
    Write-Host "  SEED_DEMO = false"
    Write-Host "  APP_ENV = production"
    Write-Host "  APP_BASE_URL = $appUrl"
    Write-Host ""
    Write-Host "Luego reiniciá la app desde el panel."
    Write-Host ""
    Write-Host "O ejecutá:"
    Write-Host "  reflex cloud secrets update TU_APP_ID --envfile .env.supabase --reboot"
}

Write-Host ""
