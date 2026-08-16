# Levanta la app (corrige bugs npm/postcss en Windows + OneDrive).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Stop-ProjectFrontend {
    # Procesos node/vite del proyecto.
    Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*$PSScriptRoot*" } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }

    # Puertos típicos de Reflex (frontend + backend).
    foreach ($port in @(3000, 3001, 8000, 8001)) {
        Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
            ForEach-Object {
                Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
            }
    }

    Start-Sleep -Milliseconds 1000
}

Stop-ProjectFrontend

& .\.venv\Scripts\python.exe .\scripts\patch_reflex_postcss.py
& .\.venv\Scripts\python.exe .\scripts\patch_reflex_npm_ebusy.py
& .\.venv\Scripts\python.exe .\scripts\fix_web_package.py

& .\.venv\Scripts\reflex.exe run @args
