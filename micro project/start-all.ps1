# start-all.ps1 - Normal startup for Automated Classroom Scheduling System
param(
  [switch]$SeedDemo
)

$ErrorActionPreference = 'Stop'
$backendDir = Join-Path $PSScriptRoot 'backend'
$frontendDir = Join-Path $PSScriptRoot 'frontend'

Write-Host '== Classroom Scheduling System Startup ==' -ForegroundColor Magenta
Set-Location $backendDir
python -m pip install -q -r requirements.txt
python manage.py migrate

if ($SeedDemo) {
  Write-Host "Seeding MITS campus data as requested (-SeedDemo)..." -ForegroundColor Yellow
  python seed.py
}

if (-not (Test-Path (Join-Path $frontendDir 'node_modules'))) {
  Push-Location $frontendDir
  try { npm.cmd install } finally { Pop-Location }
}

Start-Process -FilePath 'npm.cmd' `
  -ArgumentList @('run', 'dev', '--', '--host', '127.0.0.1', '--port', '5173') `
  -WorkingDirectory $frontendDir `
  -WindowStyle Hidden

Start-Sleep -Seconds 2
Write-Host 'Frontend: http://localhost:5173/' -ForegroundColor Cyan
Write-Host 'Backend:  http://127.0.0.1:8000/api/' -ForegroundColor Cyan
Write-Host 'Default credentials: admin / admin123 (or viewer / viewer123)' -ForegroundColor Gray
Write-Host 'Press Ctrl+C to stop the backend server.' -ForegroundColor DarkGray
python manage.py runserver 127.0.0.1:8000
