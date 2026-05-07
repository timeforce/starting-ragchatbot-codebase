# Frontend quality checks: Prettier formatting + ESLint linting
param(
    [switch]$Fix
)

$ErrorActionPreference = 'Stop'
$FrontendDir = Join-Path $PSScriptRoot '..' 'frontend'

Push-Location $FrontendDir
try {
    if ($Fix) {
        Write-Host 'Formatting with Prettier...' -ForegroundColor Cyan
        npx prettier --write .
        Write-Host 'Done.' -ForegroundColor Green
    } else {
        Write-Host 'Checking formatting with Prettier...' -ForegroundColor Cyan
        npx prettier --check .
        Write-Host 'Prettier: OK' -ForegroundColor Green
    }

    Write-Host 'Linting with ESLint...' -ForegroundColor Cyan
    npx eslint script.js
    Write-Host 'ESLint: OK' -ForegroundColor Green

    Write-Host "`nAll checks passed." -ForegroundColor Green
} catch {
    Write-Host "`nQuality checks failed." -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}
