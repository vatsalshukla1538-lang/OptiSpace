# init-demo.ps1 - Explicitly seeds authentic MITS Gwalior IT campus data and users
$ErrorActionPreference = 'Stop'
$backendDir = Join-Path $PSScriptRoot 'backend'

Write-Host "== Initializing Authentic MITS IT Timetable Data ==" -ForegroundColor Yellow
Set-Location $backendDir

python manage.py migrate
python seed.py

Write-Host "Timetable and users loaded successfully!" -ForegroundColor Green
Write-Host "Admin user:  admin  / admin123" -ForegroundColor Cyan
Write-Host "Viewer user: viewer / viewer123" -ForegroundColor Cyan
