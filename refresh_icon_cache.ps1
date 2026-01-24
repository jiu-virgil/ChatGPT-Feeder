# PowerShell script to refresh Windows icon cache
# This helps display custom executable icons in Windows Explorer

$ErrorActionPreference = "Continue"

Write-Host "Refreshing Windows icon cache..." -ForegroundColor Yellow
Write-Host ""

# Method 1: Restart Explorer (most common solution)
Write-Host "  Restarting Windows Explorer..." -ForegroundColor Cyan
try {
    Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Start-Process explorer
    Write-Host "  Explorer restarted successfully" -ForegroundColor Green
} catch {
    Write-Host "  Warning: Could not restart Explorer automatically" -ForegroundColor Yellow
    Write-Host "  Please restart Explorer manually or log out and back in" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Icon cache refresh initiated." -ForegroundColor Green
Write-Host "If icons still don't appear, try:" -ForegroundColor Cyan
Write-Host "  1. Log out and log back in" -ForegroundColor White
Write-Host "  2. Restart your computer" -ForegroundColor White
Write-Host "  3. Delete icon cache manually:" -ForegroundColor White
Write-Host "     - Close all Explorer windows" -ForegroundColor Gray
Write-Host "     - Delete: $env:LOCALAPPDATA\IconCache.db" -ForegroundColor Gray
Write-Host "     - Restart Explorer" -ForegroundColor Gray
