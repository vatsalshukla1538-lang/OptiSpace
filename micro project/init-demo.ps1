# init-demo.ps1 - Explicitly seeds authentic MITS Gwalior IT campus data and users
[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$DatabaseUrl = $env:DATABASE_URL
)

$ErrorActionPreference = 'Stop'
$backendDir = Join-Path $PSScriptRoot 'backend'

if ($DatabaseUrl) {
    $env:DATABASE_URL = $DatabaseUrl
    Write-Host "Target Database: $DatabaseUrl" -ForegroundColor Cyan
} else {
    Write-Host "Target Database: Local default (SQLite or active environment)" -ForegroundColor Cyan
}

Write-Host "== Initializing Authentic MITS IT Timetable Data ==" -ForegroundColor Yellow
Set-Location $backendDir

python manage.py migrate
python manage.py seed_db

Write-Host "Timetable and users loaded successfully!" -ForegroundColor Green
Write-Host "Admin user:  admin  / admin123" -ForegroundColor Cyan
Write-Host "Viewer user: viewer / viewer123" -ForegroundColor Cyan
